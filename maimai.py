import asyncio
import re
from pathlib import Path
from random import sample
from string import ascii_uppercase, digits
from textwrap import dedent
from typing import Tuple, Optional

from nonebot import on_command, on_regex, on_endswith, get_driver, get_bot, require, logger, on_message
from nonebot.adapters.onebot.v11 import Message, MessageEvent, GroupMessageEvent, MessageSegment, Bot, PrivateMessageEvent
from nonebot.matcher import Matcher
from nonebot.params import CommandArg, RegexGroup, Endswith
from nonebot.permission import SUPERUSER, GROUP_ADMIN

from . import BOTNAME, log, token
from .libraries.image import to_bytes_io
from .libraries.maimai_best_50 import diffs, generate, levelList, scoreRank, comboRank, syncRank
from .libraries.maimaidx_api_data import get_music_alias, post_music_alias
from .libraries.maimaidx_music import mai, guess, alias, update_local_alias
from .libraries.maimaidx_project import (
    SONGS_PER_PAGE,
    draw_music_info_to_message_segment,
    plate_to_version,
    music_play_data, query_chart_data, rise_score_data,
    player_plate_data, level_process_data, level_achievement_list_data, rating_ranking_data, music_global_data, music_play_data_dev
)
from .libraries.tool import render_forward_msg

driver = get_driver()
scheduler = require('nonebot_plugin_apscheduler').scheduler


def is_now_playing_guess_music(event: GroupMessageEvent) -> bool:
    return event.group_id in guess.Group


def is_group_admin(event: GroupMessageEvent) -> bool:
    return event.sender.role in ('owner', 'admin')


manual = on_command('帮助maimaiDX', aliases={'帮助maimaidx'}, priority=5)
repo = on_command('项目地址maimaiDX', aliases={'项目地址maimaidx'}, priority=5)
search_base = on_command('定数查歌', aliases={'search base'}, priority=5)
search_bpm = on_command('bpm查歌', aliases={'search bpm'}, priority=5)
search_artist = on_command('曲师查歌', aliases={'search artist'}, priority=5)
search_charter = on_command('谱师查歌', aliases={'search charter'}, priority=5)
random_song = on_regex(r'^[随来给]个((?:dx|sd|标准))?([绿黄红紫白]?)([0-9]+\+?)$', priority=5)
mai_what = on_regex(r'.*mai.*什么', priority=5)
search = on_command('查歌', aliases={'search'}, priority=5)  # 注意 on 响应器的注册顺序，search 应当优先于 search_* 之前注册
query_chart = on_regex(r'^([绿黄红紫白]?)\s?id\s?([0-9]+)$', priority=5)
mai_today = on_command('今日mai', aliases={'今日舞萌', '今日运势'}, priority=5)
what_song = on_endswith(('是什么歌', '是啥歌'), priority=5)
alias_song = on_endswith(('有什么别称', '有什么别名'), priority=5)
alias_local_apply = on_command('添加本地别名', aliases={'添加本地别称'}, priority=5)
alias_apply = on_command('添加别名', aliases={'增加别名', '增添别名', '添加别称'}, priority=5, permission=GROUP_ADMIN)
alias_agree = on_command('同意别名', aliases={'同意别称'}, priority=5)
alias_status = on_command('当前投票', aliases={'当前别名投票', '当前别称投票'}, priority=5)
alias_on = on_command('开启别名推送', aliases={'开启别称推送'}, priority=5, permission=GROUP_ADMIN)
alias_off = on_command('关闭别名推送', aliases={'关闭别称推送'}, priority=5, permission=GROUP_ADMIN)
alias_global_switch = on_command('aliasswitch', aliases={'全局关闭别称推送', '全局开启别称推送'}, priority=5, permission=SUPERUSER)
alias_update = on_command('aliasupdate', aliases={'更新别名库'}, priority=5, permission=SUPERUSER)
score = on_command('分数线', priority=5)
best50 = on_command('b50', aliases={'B50'}, priority=5)
minfo = on_command('minfo', aliases={'minfo', 'Minfo', 'MINFO'}, priority=5)
ginfo = on_command('ginfo', aliases={'ginfo', 'Ginfo', 'GINFO'}, priority=5)
rise_score = on_regex(r'^我要在?([0-9]+\+?)?上([0-9]+)分\s?(.+)?', priority=5)
plate_process = on_regex(r'^([真超檄橙暁晓桃櫻樱紫菫堇白雪輝辉熊華华爽舞霸星宙])([極极将舞神者]舞?)进度\s?(.+)?', priority=5)
level_process = on_regex(r'^([0-9]+\+?)\s?(.+)进度\s?(.+)?', priority=5)
level_achievement_list = on_regex(r'^([0-9]+\+?)分数列表\s?([0-9]+)?\s?(.+)?', priority=5)
rating_ranking = on_command('查看排名', aliases={'查看排行'}, priority=5)
guess_music_start = on_command('猜歌', priority=5)
guess_music_solve = on_message(rule=is_now_playing_guess_music, priority=5)
guess_music_enable = on_command('开启猜歌', aliases={'开启mai猜歌'}, priority=5, permission=GROUP_ADMIN | is_group_admin)
guess_music_disable = on_command('关闭猜歌', aliases={'关闭mai猜歌'}, priority=5, permission=GROUP_ADMIN | is_group_admin)

public_addr = 'https://vote.yuzuai.xyz/'


def song_level(ds1: float, ds2: float, stats1: str = None, stats2: str = None) -> list:
    result = []
    music_data = mai.total_list.filter(ds=(ds1, ds2))
    if stats1:
        if stats2:
            stats1 = stats1 + ' ' + stats2
            stats1 = stats1.title()
        for music in sorted(music_data, key=lambda i: int(i.id)):
            for i in music.diff:
                result.append((music.id, music.title, music.ds[i], diffs[i], music.level[i]))
    else:
        for music in sorted(music_data, key=lambda i: int(i.id)):
            for i in music.diff:
                result.append((music.id, music.title, music.ds[i], diffs[i], music.level[i]))
    return result


def get_at_qq(message: Message) -> Optional[int]:
    for item in message:
        if isinstance(item, MessageSegment) and item.type == 'at' and item.data['qq'] != 'all':
            return int(item.data['qq'])


@driver.on_bot_connect
async def get_music():
    """
    bot启动时开始获取所有数据
    """
    log.info('正在获取maimai所有曲目信息')
    await mai.get_music()
    log.info('正在获取maimai所有曲目别名信息')
    await mai.get_music_alias()
    log.info('获取完成')
    mai.guess()


@manual.handle()
async def _():
    await manual.finish(MessageSegment.image(Path(__file__).parent / 'static' / 'maimaidxhelp.png'), reply_message=True)


@repo.handle()
async def _():
    await manual.finish('项目地址：https://github.com/Yuri-YuzuChaN/maimaiDX\n求star，求宣传~', reply_message=True)


@search_base.handle()
async def _(args: Message = CommandArg()):
    args = args.extract_plain_text().strip().split()
    if len(args) > 4 or len(args) == 0:
        await search_base.finish('命令格式为\n定数查歌 <定数>\n定数查歌 <定数下限> <定数上限>', reply_message=True)
    if len(args) == 1:
        result = song_level(float(args[0]), float(args[0]))
    elif len(args) == 2:
        try:
            result = song_level(float(args[0]), float(args[1]))
        except:
            result = song_level(float(args[0]), float(args[0]), str(args[1]))
    elif len(args) == 3:
        try:
            result = song_level(float(args[0]), float(args[1]), str(args[2]))
        except:
            result = song_level(float(args[0]), float(args[0]), str(args[1]), str(args[2]))
    else:
        result = song_level(float(args[0]), float(args[1]), str(args[2]), str(args[3]))
    if not result:
        await search_base.finish('没有找到这样的乐曲。', reply_message=True)
    if len(result) >= 60:
        await search_base.finish(f'结果过多（{len(result)} 条），请缩小搜索范围', reply_message=True)
    msg = ''
    for i in result:
        msg += f'{i[0]}. {i[1]} {i[3]} {i[4]}({i[2]})\n'
    await search_base.finish(MessageSegment.image(to_bytes_io(msg)), reply_message=True)


@search_bpm.handle()
async def _(event: MessageEvent, args: Message = CommandArg()):
    if isinstance(event, GroupMessageEvent) and event.group_id in guess.Group:
        await search_bpm.finish('本群正在猜歌，不要作弊哦~', reply_message=True)
    args = args.extract_plain_text().strip().split()
    page = 1
    if len(args) == 1:
        music_data = mai.total_list.filter(bpm=int(args[0]))
    elif len(args) == 2:
        music_data = mai.total_list.filter(bpm=(int(args[0]), int(args[1])))
    elif len(args) == 3:
        music_data = mai.total_list.filter(bpm=(int(args[0]), int(args[1])))
        page = int(args[2])
    else:
        await search_bpm.finish('命令格式为：\nbpm查歌 <bpm>\nbpm查歌 <bpm下限> <bpm上限> (<页数>)', reply_message=True)
    if not music_data:
        await search_bpm.finish('没有找到这样的乐曲。', reply_message=True)
    msg = ''
    page = max(min(page, len(music_data) // SONGS_PER_PAGE + 1), 1)
    for i, m in enumerate(sorted(music_data, key=lambda i: int(i.basic_info.bpm))):
        if (page - 1) * SONGS_PER_PAGE <= i < page * SONGS_PER_PAGE:
            msg += f'No.{i + 1} {m.id}. {m.title} bpm {m.basic_info.bpm}\n'
    msg += f'第{page}页，共{len(music_data) // SONGS_PER_PAGE + 1}页'
    await search_bpm.finish(MessageSegment.image(to_bytes_io(msg)), reply_message=True)


@search_artist.handle()
async def _(event: MessageEvent, args: Message = CommandArg()):
    if isinstance(event, GroupMessageEvent) and event.group_id in guess.Group:
        await search_bpm.finish('本群正在猜歌，不要作弊哦~', reply_message=True)
    args = args.extract_plain_text().strip().split()
    page = 1
    if len(args) == 1:
        name: str = args[0]
    elif len(args) == 2:
        name: str = args[0]
        if args[1].isdigit():
            page = int(args[1])
        else:
            await search_artist.finish('命令格式为：\n曲师查歌 <曲师名称> (<页数>)', reply_message=True)
    else:
        name = ''
        await search_artist.finish('命令格式为：\n曲师查歌 <曲师名称> (<页数>)', reply_message=True)
    if not name:
        return
    music_data = mai.total_list.filter(artist_search=name)
    if not music_data:
        await search_artist.finish('没有找到这样的乐曲。', reply_message=True)
    msg = ''
    page = max(min(page, len(music_data) // SONGS_PER_PAGE + 1), 1)
    for i, m in enumerate(music_data):
        if (page - 1) * SONGS_PER_PAGE <= i < page * SONGS_PER_PAGE:
            msg += f'No.{i + 1} {m.id}. {m.title} {m.basic_info.artist}\n'
    msg += f'第{page}页，共{len(music_data) // SONGS_PER_PAGE + 1}页'
    await search_artist.finish(MessageSegment.image(to_bytes_io(msg)), reply_message=True)


@search_charter.handle()
async def _(event: MessageEvent, args: Message = CommandArg()):
    if isinstance(event, GroupMessageEvent) and event.group_id in guess.Group:
        await search_bpm.finish('本群正在猜歌，不要作弊哦~', reply_message=True)
    args = args.extract_plain_text().strip().split()
    page = 1
    if len(args) == 1:
        name: str = args[0]
    elif len(args) == 2:
        name: str = args[0]
        if args[1].isdigit():
            page = int(args[1])
        else:
            await search_charter.finish('命令格式为：\n谱师查歌 <谱师名称> (<页数>)', reply_message=True)
    else:
        name = ''
        await search_charter.finish('命令格式为：\n谱师查歌 <谱师名称> (<页数>)', reply_message=True)
    if not name:
        return
    music_data = mai.total_list.filter(charter_search=name)
    if not music_data:
        await search_charter.finish('没有找到这样的乐曲。', reply_message=True)
    msg = ''
    page = max(min(page, len(music_data) // SONGS_PER_PAGE + 1), 1)
    for i, m in enumerate(music_data):
        if (page - 1) * SONGS_PER_PAGE <= i < page * SONGS_PER_PAGE:
            diff_charter = zip([diffs[d] for d in m.diff], [m.charts[d].charter for d in m.diff])
            msg += f'No.{i + 1} {m.id}. {m.title} {" ".join([f"{d}/{c}" for d, c in diff_charter])}\n'
    msg += f'第{page}页，共{len(music_data) // SONGS_PER_PAGE + 1}页'
    await search_charter.finish(MessageSegment.image(to_bytes_io(msg)), reply_message=True)


@random_song.handle()
async def _(match: Tuple = RegexGroup()):
    # see https://github.com/nonebot/nonebot2/pull/1453
    try:
        diff = match[0]
        if diff == 'dx':
            tp = ['DX']
        elif diff == 'sd' or diff == '标准':
            tp = ['SD']
        else:
            tp = ['SD', 'DX']
        level = match[2]
        if match[1] == '':
            music_data = mai.total_list.filter(level=level, type=tp)
        else:
            music_data = mai.total_list.filter(level=level, diff=['绿黄红紫白'.index(match[1])], type=tp)
        if len(music_data) == 0:
            msg = '没有这样的乐曲哦。'
        else:
            msg = await draw_music_info_to_message_segment(music_data.random())
    except:
        msg = '随机命令错误，请检查语法'
    await random_song.finish(msg, reply_message=True)


@mai_what.handle()
async def _():
    await mai_what.finish(await draw_music_info_to_message_segment(mai.total_list.random()), reply_message=True)


@search.handle()
async def _(args: Message = CommandArg()):
    name = args.extract_plain_text().strip()
    if not name:
        return
    result = mai.total_list.filter(title_search=name)
    if len(result) == 0:
        await search.finish('没有找到这样的乐曲。', reply_message=True)
    elif len(result) == 1:
        msg = await draw_music_info_to_message_segment(result.random())
        await search.finish(msg, reply_message=True)
    elif len(result) < 50:
        search_result = ''
        for music in sorted(result, key=lambda i: int(i.id)):
            search_result += f'{music.id}. {music.title}\n'
        await search.finish(MessageSegment.image(to_bytes_io(search_result)), reply_message=True)
    else:
        await search.finish(f'结果过多（{len(result)} 条），请缩小查询范围。', reply_message=True)


@query_chart.handle()
async def _(match: Tuple = RegexGroup()):
    msg = await query_chart_data(match)
    await query_chart.finish(msg, reply_message=True)


@mai_today.handle()
async def _(event: MessageEvent):
    wm_list = ['拼机', '推分', '越级', '下埋', '夜勤', '练底力', '练手法', '打旧框', '干饭', '抓绝赞', '收歌']
    uid = event.user_id
    h = hash(uid)
    rp = h % 100
    wm_value = []
    for i in range(11):
        wm_value.append(h & 3)
        h >>= 2
    msg = f'\n今日人品值：{rp}\n'
    for i in range(11):
        if wm_value[i] == 3:
            msg += f'宜 {wm_list[i]}\n'
        elif wm_value[i] == 0:
            msg += f'忌 {wm_list[i]}\n'
    msg += f'{BOTNAME} Bot提醒您：打机时不要大力拍打或滑动哦\n今日推荐歌曲：'
    music = mai.total_list[h % len(mai.total_list)]
    msg += await draw_music_info_to_message_segment(music)
    await mai_today.finish(msg, reply_message=True)


@what_song.handle()
async def _(event: MessageEvent, end: str = Endswith()):
    name = event.get_plaintext().lower()[0:-len(end)].strip()  # before 3.9

    data = mai.total_alias_list.by_alias(name)
    if not data:
        await what_song.finish('未找到此歌曲\n可以使用 添加别名 指令给该乐曲添加别名', reply_message=True)
    if len(data) != 1:
        msg = f'找到{len(data)}个相同别名的曲目：\n'
        for songs in data:
            msg += f'{songs.ID}：{songs.Name}\n'
        await what_song.finish(msg.strip(), reply_message=True)

    music = mai.total_list.by_id(str(data[0].ID))
    await what_song.finish('您要找的是不是：' + await draw_music_info_to_message_segment(music), reply_message=True)


@alias_song.handle()
async def _(event: MessageEvent, end: str = Endswith()):
    name = event.get_plaintext().lower()[0:-len(end)].strip()  # before 3.9

    aliases = mai.total_alias_list.by_alias(name)
    if not aliases:
        if name.isdigit():
            alias_id = mai.total_alias_list.by_id(name)
            if not alias_id:
                await alias_song.finish('未找到此歌曲\n可以使用 添加别名 指令给该乐曲添加别名', reply_message=True)
            else:
                aliases = alias_id
        else:
            await alias_song.finish('未找到此歌曲\n可以使用 添加别名 指令给该乐曲添加别名', reply_message=True)
    if len(aliases) != 1:
        msg = []
        for songs in aliases:
            alias_list = '\n'.join(songs.Alias)
            msg.append(f'ID：{songs.ID}\n{alias_list}')
        await alias_song.finish(f'找到{len(aliases)}个相同别名的曲目：\n' + '\n======\n'.join(msg), reply_message=True)

    if len(aliases[0].Alias) == 1:
        await alias_song.finish('该曲目没有别名', reply_message=True)

    msg = f'该曲目有以下别名：\nID：{aliases[0].ID}\n'
    msg += '\n'.join(aliases[0].Alias)
    await alias_song.finish(msg, reply_message=True)


@alias_local_apply.handle()
async def _(event: MessageEvent, arg: Message = CommandArg()):
    args = arg.extract_plain_text().strip().split()
    if len(args) != 2:
        await alias_local_apply.finish('参数错误', reply_message=True)
    id_, alias_name = args
    if not mai.total_list.by_id(id_):
        await alias_local_apply.finish(f'未找到ID为 [{id_}] 的曲目', reply_message=True)
    server_exist = await get_music_alias('alias', {'id': id_})
    if alias_name in server_exist[id_]:
        await alias_local_apply.finish(f'该曲目的别名 <{alias_name}> 已存在别名服务器，不能重复添加别名，如果bot未生效，请联系BOT管理员使用指令 <更新别名库>')
    local_exist = mai.total_alias_list.by_alias(alias_name)
    if local_exist:
        await alias_local_apply.finish(f'本地别名库已存在该别名', reply_message=True)
    issave = await update_local_alias(id_, alias_name)
    if not issave:
        msg = '添加本地别名失败'
    else:
        msg = f'已成功为ID <{id_}> 添加别名 <{alias_name}> 到本地别名库'
    await alias_local_apply.send(msg, reply_message=True)

@alias_apply.handle()
async def _(event: MessageEvent, arg: Message = CommandArg()):
    args = arg.extract_plain_text().strip().split()
    if len(args) != 2:
        await alias_apply.finish('参数错误', reply_message=True)
    id_, alias_name = args
    if not mai.total_list.by_id(id_):
        await alias_apply.finish('未找到ID为 [{id_}] 的曲目', reply_message=True)
    isexist = await get_music_alias('alias', {'id': id_})
    if alias_name in isexist[id_]:
        await alias_apply.finish(f'该曲目的别名 <{alias_name}> 已存在，不能重复添加别名，如果bot未生效，请联系BOT管理员使用指令 <更新别名库>', reply_message=True)
    tag = ''.join(sample(ascii_uppercase + digits, 5))
    status = await post_music_alias('apply', {'id': id_, 'aliasname': alias_name, 'tag': tag, 'uid': event.user_id})
    if 'error' in status:
        await alias_apply.finish(status['error'], reply_message=True)
    elif isinstance(status, str):
        await alias_apply.finish(status, reply_message=True)
    await alias_apply.finish(dedent(f'''\
        您已提交以下别名申请
        ID：{id_}
        别名：{alias_name}
        现在可用使用唯一标签<{tag}>来进行投票，例如：同意别名 {tag}
        浏览{public_addr + "/vote"}查看详情
        ''') + await draw_music_info_to_message_segment(mai.total_list.by_id(id_)), reply_message=True)


@alias_agree.handle()
async def _(event: MessageEvent, arg: Message = CommandArg()):
    tag = arg.extract_plain_text().strip().upper()
    status = await post_music_alias('agree', {'tag': tag, 'uid': event.user_id})
    if 'content' in status:
        await alias_agree.finish(status['content'], reply_message=True)
    if 'error' in status:
        await alias_agree.finish(status['error'], reply_message=True)
    else:
        await alias_agree.finish(str(status), reply_message=True)


@alias_status.handle()
async def _(event: GroupMessageEvent):
    status = await get_music_alias('status')
    if not status:
        await alias_status.finish('未查询到正在进行的别名投票', reply_message=True)
    msg = [f'浏览{public_addr + "/vote"}查看详情']
    for tag in status:
        id_ = str(status[tag]['ID'])
        alias_name = status[tag]['ApplyAlias']
        usernum = status[tag]['Users']
        votes = status[tag]['Votes']
        msg.append(
            await draw_music_info_to_message_segment(mai.total_list.by_id(id_)) +
            f'\n{tag}：\n别名：{alias_name}\n票数：{usernum}/{votes}'
        )
    msg.append(f'浏览{public_addr}查看详情或查看以下合并消息')
    bot = get_bot()
    await bot.send_group_forward_msg(group_id=event.group_id, messages=render_forward_msg(msg, name=BOTNAME))


@alias_on.handle()
async def _(event: GroupMessageEvent):
    gid = event.group_id
    if gid in alias.config['enable']:
        msg = '该群已开启别名推送功能'
    else:
        alias.alias_change(gid, True)
        msg = '已开启该群别名推送功能'
    await alias_on.finish(msg, reply_message=True)


@alias_off.handle()
async def _(event: GroupMessageEvent):
    gid = event.group_id
    if gid in alias.config['disable']:
        msg = '该群已关闭别名推送功能'
    else:
        alias.alias_change(gid, False)
        msg = '已关闭该群别名推送功能'
    await alias_off.finish(msg, reply_message=True)


@alias_global_switch.handle()
async def _(event: PrivateMessageEvent):
    if event.raw_message == '全局关闭别称推送':
        alias.alias_global_change(False)
        await alias_global_switch.send('已全局关闭maimai别名推送')
    elif event.raw_message == '全局开启别名推送':
        alias.alias_global_change(True)
        await alias_global_switch.send('已全局开启maimai别名推送')
    else:
        return


@alias_update.handle()
async def _(event: PrivateMessageEvent):
    try:
        await mai.get_music_alias()
        log.error('手动更新别名库成功')
        await alias_update.send('手动更新别名库成功')
    except:
        log.error('手动更新别名库失败')
        await alias_update.send('手动更新别名库失败')


async def alias_apply_status():
    bot = get_bot()
    if status := await get_music_alias('status'):
        if 'error' in status:
            log.error(f'发生错误：{status["error"]}')
            raise ValueError
        if alias.config['global']:
            msg = ['检测到新的别名申请']
            for tag in status:
                if status[tag]['IsNew'] and (usernum := status[tag]['Users']) < (votes := status[tag]['Votes']):
                    id_ = str(status[tag]['ID'])
                    alias_name = status[tag]['ApplyAlias']
                    music = mai.total_list.by_id(id_)
                    msg.append(f'{tag}：\nID：{id_}\n标题：{music.title}\n别名：{alias_name}\n票数：{usernum}/{votes}')
            if len(msg) != 1:
                for group in await bot.get_group_list():
                    gid = group['group_id']
                    if gid in alias.config['disable'] or gid not in alias.config['enable']:
                        continue
                    try:
                        await bot.send_group_msg(group_id=gid, message='\n======\n'.join(msg))
                        await asyncio.sleep(5)
                    except:
                        continue
    await asyncio.sleep(5)
    if end := await get_music_alias('end'):
        if 'error' in end:
            log.error(f'发生错误：{status["error"]}')
            raise ValueError
        if alias.config['global']:
            msg2 = ['以下是已成功添加别名的曲目']
            for ta in end:
                id_ = str(end[ta]['ID'])
                alias_name = end[ta]['ApplyAlias']
                music = mai.total_list.by_id(id_)
                msg2.append(f'标题：{music.title}\nID：{id_}\n别名：{alias_name}')
            if len(msg2) != 1:
                for group in await bot.get_group_list():
                    gid = group['group_id']
                    if gid in alias.config['disable'] or gid not in alias.config['enable']:
                        continue
                    try:
                        await bot.send_group_msg(group_id=gid, message='\n======\n'.join(msg2))
                        await asyncio.sleep(5)
                    except:
                        continue
        await mai.get_music_alias()


@score.handle()
async def _(arg: Message = CommandArg()):
    arg = arg.extract_plain_text().strip()
    args = arg.split()
    if args and args[0] == '帮助':
        msg = dedent('''\
            此功能为查找某首歌分数线设计。
            命令格式：分数线 <难度+歌曲id> <分数线>
            例如：分数线 紫799 100
            命令将返回分数线允许的 TAP GREAT 容错以及 BREAK 50落等价的 TAP GREAT 数。
            以下为 TAP GREAT 的对应表：
            GREAT/GOOD/MISS
            TAP\t1/2.5/5
            HOLD\t2/5/10
            SLIDE\t3/7.5/15
            TOUCH\t1/2.5/5
            BREAK\t5/12.5/25(外加200落)''')
        await score.finish(MessageSegment.image(to_bytes_io(msg)), reply_message=True)
    else:
        try:
            result = re.search(r'([绿黄红紫白])\s?([0-9]+)', arg)
            level_labels = ['绿', '黄', '红', '紫', '白']
            level_labels2 = ['Basic', 'Advanced', 'Expert', 'Master', 'Re:MASTER']
            level_index = level_labels.index(result.group(1))
            chart_id = result.group(2)
            line = float(args[-1])
            music = mai.total_list.by_id(chart_id)
            chart = music.charts[level_index]
            tap = int(chart.notes.tap)
            slide = int(chart.notes.slide)
            hold = int(chart.notes.hold)
            touch = int(chart.notes.touch) if len(chart.notes) == 5 else 0
            brk = int(chart.notes.brk)
            total_score = tap * 500 + slide * 1500 + hold * 1000 + touch * 500 + brk * 2500
            break_bonus = 0.01 / brk
            break_50_reduce = total_score * break_bonus / 4
            reduce = 101 - line
            if reduce <= 0 or reduce >= 101:
                raise ValueError
            msg = dedent(f'''\
                {music.title} {level_labels2[level_index]}
                分数线 {line}% 允许的最多 TAP GREAT 数量为 {(total_score * reduce / 10000):.2f}(每个-{10000 / total_score:.4f}%),
                BREAK 50落(一共{brk}个)等价于 {(break_50_reduce / 100):.3f} 个 TAP GREAT(-{break_50_reduce / total_score * 100:.4f}%)''')
            await score.finish(MessageSegment.image(to_bytes_io(msg)), reply_message=True)
        except (AttributeError, ValueError) as e:
            logger.exception(e)
            await score.finish('格式错误，输入“分数线 帮助”以查看帮助信息', reply_message=True)


@best50.handle()
async def _(event: MessageEvent, matcher: Matcher, arg: Message = CommandArg()):
    specific_qq = get_at_qq(arg)

    if not arg:  # b40
        payload = {'qq': event.user_id}
    elif specific_qq is None:  # b40 name
        payload = {'username': arg.extract_plain_text().split()}
    else:  # b40 @xxxx
        payload = {'qq': specific_qq}

    payload['b50'] = True

    await matcher.finish(await generate(payload), reply_message=True)


@minfo.handle()
async def _(event: MessageEvent, arg: Message = CommandArg()):
    qqid = get_at_qq(arg) or event.user_id
    args = arg.extract_plain_text().strip()
    if not args:
        await minfo.finish('请输入曲目id或曲名', reply_message=True)
    payload = {
        'qq': qqid,
        'version': list(set(version for version in plate_to_version.values()))
    }
    if mai.total_list.by_id(args):
        id = args
    elif by_t := mai.total_list.by_title(args):
        id = by_t.id
    else:
        aliases = mai.total_alias_list.by_alias(args)
        if not aliases:
            await minfo.finish('未找到曲目', reply_message=True)
        elif len(aliases) != 1:
            msg = '找到相同别名的曲目，请使用以下ID查询：\n'
            for songs in aliases:
                msg += f'{songs.ID}：{songs.Name}\n'
            await minfo.finish(msg.strip(), reply_message=True)
        else:
            id = str(aliases[0].ID)

    if token:
        pic = await music_play_data_dev(payload, id)
    else:
        pic = await music_play_data(payload, id)

    await minfo.finish(pic, reply_message=True)


@ginfo.handle()
async def _(event: MessageEvent, arg: Message = CommandArg()):
    args = arg.extract_plain_text().strip()
    if not args:
        await ginfo.finish('请输入曲目id或曲名', reply_message=True)
    if args[0] not in '绿黄红紫白':
        level_index = 3
    else:
        level_index = '绿黄红紫白'.index(args[0])
        args = args[1:].strip()
        if not args:
            await ginfo.finish('请输入曲目id或曲名', reply_message=True)
    if mai.total_list.by_id(args):
        id = args
    elif by_t := mai.total_list.by_title(args):
        id = by_t.id
    else:
        alias = mai.total_alias_list.by_alias(args)
        if not alias:
            await ginfo.finish('未找到曲目', reply_message=True)
        elif len(alias) != 1:
            msg = '找到相同别名的曲目，请使用以下ID查询：\n'
            for songs in alias:
                msg += f'{songs.ID}：{songs.Name}\n'
            await ginfo.finish(msg.strip(), reply_message=True)
        else:
            id = str(alias[0].ID)
    music = mai.total_list.by_id(id)
    if not music.stats:
        await ginfo.finish('该乐曲还没有统计信息', reply_message=True)
    if level_index >= len(music.stats) or not music.stats[level_index]:
        await ginfo.finish('该乐曲没有这个等级', reply_message=True)
    stats = music.stats[level_index]
    await ginfo.finish(await music_global_data(music, level_index) + dedent(f'''\
        游玩次数：{round(stats.cnt)}
        拟合难度：{stats.fit_diff:.2f}
        平均达成率：{stats.avg:.2f}%
        平均 DX 分数：{stats.avg_dx:.1f}
        谱面成绩标准差：{stats.std_dev:.2f}
        '''), at_sender=True)


@rise_score.handle()  # 慎用，垃圾代码非常吃机器性能
async def _(bot: Bot, event: MessageEvent, match: Tuple = RegexGroup()):
    qqid = get_at_qq(event.get_message()) or event.user_id
    nickname = ''

    if match[0] and match[0] not in levelList:
        await rise_score.finish('无此等级', reply_message=True)
    elif match[2]:
        nickname = match[2]
        payload = {'username': match[2].strip()}
    else:
        payload = {'qq': qqid}

    if qqid != event.user_id:
        nickname = (await bot.get_stranger_info(user_id=qqid))['nickname']

    data = await rise_score_data(payload, match, nickname)
    await rise_score.finish(data, reply_message=True)


@plate_process.handle()
async def _(bot: Bot, event: MessageEvent, match: Tuple = RegexGroup()):
    qqid = get_at_qq(event.get_message()) or event.user_id
    nickname = ''

    if f'{match[0]}{match[1]}' == '真将':
        await plate_process.finish('真系没有真将哦', reply_message=True)
    elif match[2]:
        nickname = match[2]
        payload = {'username': match[2].strip()}
    else:
        payload = {'qq': qqid}

    if qqid != event.user_id:
        nickname = (await bot.get_stranger_info(user_id=qqid))['nickname']

    if match[0] in ['霸', '舞']:
        payload['version'] = list(set(version for version in list(plate_to_version.values())[:-9]))
    else:
        payload['version'] = [plate_to_version[match[0]]]

    data = await player_plate_data(payload, match, nickname)
    await plate_process.finish(data, reply_message=True)


@level_process.handle()
async def _(bot: Bot, event: MessageEvent, match: Tuple = RegexGroup()):
    qqid = get_at_qq(event.get_message()) or event.user_id
    nickname = ''

    if match[0] not in levelList:
        await level_process.finish('无此等级', reply_message=True)
    if match[1].lower() not in scoreRank + comboRank + syncRank:
        await level_process.finish('无此评价等级', reply_message=True)
    if levelList.index(match[0]) < 11 or (match[1].lower() in scoreRank and scoreRank.index(match[1].lower()) < 8):
        await level_process.finish('兄啊，有点志向好不好', reply_message=True)
    elif match[2]:
        nickname = match[2]
        payload = {'username': match[2].strip()}
    else:
        payload = {'qq': qqid}

    if qqid != event.user_id:
        nickname = (await bot.get_stranger_info(user_id=qqid))['nickname']

    payload['version'] = list(set(version for version in plate_to_version.values()))

    data = await level_process_data(payload, match, nickname)
    await level_process.finish(data, reply_message=True)


@level_achievement_list.handle()
async def _(bot: Bot, event: MessageEvent, match: Tuple = RegexGroup()):
    qqid = get_at_qq(event.get_message()) or event.user_id
    nickname = ''

    if match[0] not in levelList:
        await level_achievement_list.finish('无此等级', reply_message=True)
    elif match[2]:
        nickname = match[2]
        payload = {'username': match[2].strip()}
    else:
        payload = {'qq': qqid}

    if qqid != event.user_id:
        nickname = (await bot.get_stranger_info(user_id=qqid))['nickname']

    payload['version'] = list(set(version for version in plate_to_version.values()))

    data = await level_achievement_list_data(payload, match, nickname)
    await level_achievement_list.finish(data, reply_message=True)


@rating_ranking.handle()
async def _(arg: Message = CommandArg()):
    arg = arg.extract_plain_text().strip()
    page = 1
    name = ''
    if arg.isdigit():
        page = int(arg)
    else:
        name = arg.lower()

    data = await rating_ranking_data(name, page)
    await rating_ranking.finish(data, reply_message=True)


@guess_music_start.handle()
async def _(event: GroupMessageEvent):
    gid = event.group_id
    if gid not in guess.config['enable']:
        await guess_music_start.finish('该群已关闭猜歌功能，开启请输入 开启mai猜歌', reply_message=True)
    if gid in guess.Group:
        await guess_music_start.finish('该群已有正在进行的猜歌', reply_message=True)
    guess.add(gid)
    await mai.start()
    guess.start(gid, mai, 0)
    await guess_music_start.send(
        '我将从热门乐曲中选择一首歌，每隔8秒描述它的特征，'
        '请输入歌曲的 id 标题 或 别名（需bot支持，无需大小写） 进行猜歌（DX乐谱和标准乐谱视为两首歌）。'
        '猜歌时查歌等其他命令依然可用。'
    )
    await guess_music_loop(event)
    await guess_music_start.finish()


async def guess_music_loop(event: GroupMessageEvent):
    gid = event.group_id
    cycle = guess.Group[gid]['cycle']
    if cycle != 0:
        await asyncio.sleep(8)
    else:
        await asyncio.sleep(4)
    _guess = guess.Group[gid]['object']
    if gid not in guess.config['enable'] or _guess.is_end:
        return
    if cycle < 6:
        await guess_music_start.send(f'{cycle + 1}/7 这首歌{_guess.guess_options[cycle]}')
    else:
        await guess_music_start.send('7/7 这首歌封面的一部分是：\n' + MessageSegment.image(_guess.image) + '\n答案将在30秒后揭晓')
        await give_answer(event)
    guess.Group[gid]['cycle'] += 1
    await guess_music_loop(event)


async def give_answer(event: GroupMessageEvent):
    gid = event.group_id
    await asyncio.sleep(30)
    _guess = guess.Group[gid]['object']
    if gid not in guess.config['enable'] or _guess.is_end:
        return
    _guess.is_end = True
    guess.end(gid)
    await guess_music_solve.finish('答案是：' + await draw_music_info_to_message_segment(_guess.music), reply_message=True)


@guess_music_solve.handle()
async def _(event: GroupMessageEvent):
    gid = event.group_id
    ans = event.get_plaintext().strip()
    guess_ = guess.Group[gid]['object']
    if ans.lower() in guess_.answer:
        guess_.is_end = True
        guess.end(gid)
        await guess_music_solve.finish('猜对了，答案是：' + await draw_music_info_to_message_segment(guess_.music), reply_message=True)


@guess_music_enable.handle()
@guess_music_disable.handle()
async def _(matcher: Matcher, event: GroupMessageEvent):
    gid = event.group_id
    if type(matcher) is guess_music_enable:
        guess.guess_change(gid, True)
        msg = '已开启该群猜歌功能'
    elif type(matcher) is guess_music_disable:
        guess.guess_change(gid, False)
        if str(gid) in guess.Group:
            guess.end(str(gid))
        msg = '已关闭该群猜歌功能'
    else:
        raise ValueError('matcher type error')

    await guess_music_enable.finish(msg, reply_message=True)


async def Data_Update():
    await mai.get_music()
    mai.guess()
    logger.info('数据更新完毕')


scheduler.add_job(alias_apply_status, 'interval', minutes=5)
scheduler.add_job(Data_Update, 'cron', hour=4)
