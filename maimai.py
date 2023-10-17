import asyncio
import re
from random import sample
from re import Match
from string import ascii_uppercase, digits

from nonebot import NoneBot, on_startup

from hoshino import Service, priv
from hoshino.service import sucmd
from hoshino.typing import CommandSession, CQEvent

from .libraries.maimaidx_music import alias, guess, update_local_alias
from .libraries.maimaidx_music_info import *
from .libraries.maimaidx_player_score import *
from .libraries.tool import *

public_addr = 'https://vote.yuzuai.xyz/'

SV_HELP = '请使用 帮助maimaiDX 查看帮助'
sv = Service('maimaiDX', manage_priv=priv.ADMIN, enable_on_default=False, help_=SV_HELP)


def song_level(ds1: float, ds2: float) -> list:
    result = []
    music_data = mai.total_list.filter(ds=(ds1, ds2))
    for music in sorted(music_data, key=lambda i: int(i.id)):
        for i in music.diff:
            result.append((music.id, music.title, music.ds[i], diffs[i], music.level[i]))
    return result


@on_startup
async def _():
    """
    bot启动时开始获取所有数据
    """
    log.info('正在获取maimai所有曲目信息')
    await mai.get_music()
    log.info('正在获取maimai所有曲目别名信息')
    await mai.get_music_alias()
    log.info('maimai数据获取完成')
    mai.guess()


@sucmd('updateData', aliases='更新maimai数据')
async def _(session: CommandSession):
    await mai.get_music()
    await mai.get_music_alias()
    await session.send('maimai数据更新完成')


@sv.on_fullmatch(['帮助maimaiDX', '帮助maimaidx'])
async def dx_help(bot: NoneBot, ev: CQEvent):
    await bot.send(ev, MessageSegment.image(f'file:///{Root / "maimaidxhelp.png"}'), at_sender=True)


@sv.on_fullmatch(['项目地址maimaiDX', '项目地址maimaidx'])
async def dx_github(bot: NoneBot, ev: CQEvent):
    await bot.send(ev, f'项目地址：https://github.com/Yuri-YuzuChaN/maimaiDX\n求star，求宣传~', at_sender=True)


@sv.on_prefix(['定数查歌', 'search base'])
async def search_dx_song_level(bot: NoneBot, ev: CQEvent):
    args = ev.message.extract_plain_text().strip().split()
    if len(args) > 3 or len(args) == 0:
        await bot.finish(ev, '命令格式为\n定数查歌 <定数> [页数]\n定数查歌 <定数下限> <定数上限> [页数]',
                         at_sender=True)
    page = 1
    if len(args) == 1:
        result = song_level(float(args[0]), float(args[0]))
    elif len(args) == 2:
        if float(args[1]) > float(args[0]):
            result = song_level(float(args[0]), float(args[1]))
        else:
            result = song_level(float(args[0]), float(args[0]))
            page = int(args[1])
    else:
        result = song_level(float(args[0]), float(args[1]))
        page = int(args[2])
    if not result:
        await bot.finish(ev, f'没有找到这样的乐曲。', at_sender=True)
    # if len(result) >= 60:
    #     await bot.finish(ev, f'结果过多（{len(result)} 条），请缩小搜索范围', at_sender=True)
    msg = ''
    page = max(min(page, len(result) // SONGS_PER_PAGE + 1), 1)
    for i, r in enumerate(result):
        if (page - 1) * SONGS_PER_PAGE <= i < page * SONGS_PER_PAGE:
            msg += f'{r[0]}. {r[1]} {r[3]} {r[4]}({r[2]})\n'
    msg += f'第{page}页，共{len(result) // SONGS_PER_PAGE + 1}页'
    await bot.send(ev, MessageSegment.image(image_to_base64(text_to_image(msg.strip()))), at_sender=True)


@sv.on_prefix(['bpm查歌', 'search bpm'])
async def search_dx_song_bpm(bot: NoneBot, ev: CQEvent):
    if str(ev.group_id) in guess.Group:
        await bot.finish(ev, '本群正在猜歌，不要作弊哦~', at_sender=True)
    args = ev.message.extract_plain_text().strip().split()
    page = 1
    if len(args) == 1:
        music_data = mai.total_list.filter(bpm=int(args[0]))
    elif len(args) == 2:
        music_data = mai.total_list.filter(bpm=(int(args[0]), int(args[1])))
    elif len(args) == 3:
        music_data = mai.total_list.filter(bpm=(int(args[0]), int(args[1])))
        page = int(args[2])
    else:
        await bot.finish(ev, '命令格式为：\nbpm查歌 <bpm>\nbpm查歌 <bpm下限> <bpm上限> (<页数>)', at_sender=True)
    if not music_data:
        await bot.finish(ev, f'没有找到这样的乐曲。', at_sender=True)
    msg = ''
    page = max(min(page, len(music_data) // SONGS_PER_PAGE + 1), 1)
    for i, m in enumerate(sorted(music_data, key=lambda i: int(i.basic_info.bpm))):
        if (page - 1) * SONGS_PER_PAGE <= i < page * SONGS_PER_PAGE:
            msg += f'No.{i + 1} {m.id}. {m.title} bpm {m.basic_info.bpm}\n'
    msg += f'第{page}页，共{len(music_data) // SONGS_PER_PAGE + 1}页'
    await bot.send(ev, MessageSegment.image(image_to_base64(text_to_image(msg.strip()))), at_sender=True)


@sv.on_prefix(['曲师查歌', 'search artist'])
async def search_dx_song_artist(bot: NoneBot, ev: CQEvent):
    if str(ev.group_id) in guess.Group:
        await bot.finish(ev, '本群正在猜歌，不要作弊哦~', at_sender=True)
    args: List[str] = ev.message.extract_plain_text().strip().split()
    page = 1
    if len(args) == 1:
        name: str = args[0]
    elif len(args) == 2:
        name: str = args[0]
        if args[1].isdigit():
            page = int(args[1])
        else:
            bot.finish(ev, '命令格式为：曲师查歌 <曲师名称> (<页数>)', at_sender=True)
    else:
        bot.finish(ev, '命令格式为：曲师查歌 <曲师名称> (<页数>)', at_sender=True)
    if not name:
        return
    music_data = mai.total_list.filter(artist_search=name)
    if not music_data:
        await bot.finish(ev, f'没有找到这样的乐曲。', at_sender=True)
    msg = ''
    page = max(min(page, len(music_data) // SONGS_PER_PAGE + 1), 1)
    for i, m in enumerate(music_data):
        if (page - 1) * SONGS_PER_PAGE <= i < page * SONGS_PER_PAGE:
            msg += f'No.{i + 1} {m.id}. {m.title} {m.basic_info.artist}\n'
    msg += f'第{page}页，共{len(music_data) // SONGS_PER_PAGE + 1}页'
    await bot.send(ev, MessageSegment.image(image_to_base64(text_to_image(msg.strip()))), at_sender=True)


@sv.on_prefix(['谱师查歌', 'search charter'])
async def search_dx_song_charter(bot: NoneBot, ev: CQEvent):
    if str(ev.group_id) in guess.Group:
        await bot.finish(ev, '本群正在猜歌，不要作弊哦~', at_sender=True)
    args: List[str] = ev.message.extract_plain_text().strip().split()
    page = 1
    if len(args) == 1:
        name: str = args[0]
    elif len(args) == 2:
        name: str = args[0]
        if args[1].isdigit():
            page = int(args[1])
        else:
            bot.finish(ev, '命令格式为：谱师查歌 <谱师名称> (<页数>)', at_sender=True)
    else:
        bot.finish(ev, '命令格式为：谱师查歌 <谱师名称> (<页数>)', at_sender=True)
    if not name:
        return
    music_data = mai.total_list.filter(charter_search=name)
    if not music_data:
        await bot.finish(ev, f'没有找到这样的乐曲。', at_sender=True)
    msg = ''
    page = max(min(page, len(music_data) // SONGS_PER_PAGE + 1), 1)
    for i, m in enumerate(music_data):
        if (page - 1) * SONGS_PER_PAGE <= i < page * SONGS_PER_PAGE:
            diff_charter = zip([diffs[d] for d in m.diff], [m.charts[d].charter for d in m.diff])
            msg += f'No.{i + 1} {m.id}. {m.title} {" ".join([f"{d}/{c}" for d, c in diff_charter])}\n'
    msg += f'第{page}页，共{len(music_data) // SONGS_PER_PAGE + 1}页'
    await bot.send(ev, MessageSegment.image(image_to_base64(text_to_image(msg.strip()))), at_sender=True)


@sv.on_rex(r'^[来随给]个((?:dx|sd|标准))?([绿黄红紫白]?)([0-9]+\+?)$')
async def random_song(bot: NoneBot, ev: CQEvent):
    try:
        match: Match[str] = ev['match']
        diff = match.group(1)
        if diff == 'dx':
            tp = ['DX']
        elif diff == 'sd' or diff == '标准':
            tp = ['SD']
        else:
            tp = ['SD', 'DX']
        level = match.group(3)
        if match.group(2) == '':
            music_data = mai.total_list.filter(level=level, music_type=tp)
        else:
            music_data = mai.total_list.filter(level=level, diff=['绿黄红紫白'.index(match.group(2))], music_type=tp)
        if len(music_data) == 0:
            msg = '没有这样的乐曲哦。'
        else:
            msg = await new_draw_music_info(music_data.random())
        await bot.send(ev, msg, at_sender=True)
    except:
        await bot.send(ev, '随机命令错误，请检查语法', at_sender=True)


@sv.on_rex(r'.*mai.*什么')
async def random_day_song(bot: NoneBot, ev: CQEvent):
    await bot.send(ev, await new_draw_music_info(mai.total_list.random()))


@sv.on_prefix(['查歌', 'search'])
async def search_song(bot: NoneBot, ev: CQEvent):
    name: str = ev.message.extract_plain_text().strip()
    if not name:
        return
    result = mai.total_list.filter(title_search=name)
    if len(result) == 0:
        await bot.send(ev, '没有找到这样的乐曲。', at_sender=True)
    elif len(result) == 1:
        msg = await new_draw_music_info(result.random())
        await bot.send(ev, msg)
    elif len(result) < 50:
        search_result = ''
        for music in sorted(result, key=lambda i: int(i.id)):
            search_result += f'{music.id}. {music.title}\n'
        await bot.send(ev, search_result.strip(), at_sender=True)
    else:
        await bot.send(ev, f'结果过多（{len(result)} 条），请缩小查询范围。', at_sender=True)


@sv.on_prefix(['id', 'Id', 'ID'])
async def query_chart(bot: NoneBot, ev: CQEvent):
    id: str = ev.message.extract_plain_text().strip()
    if not id:
        return
    if id.isdigit():
        music = mai.total_list.by_id(id)
        if not music:
            msg = f'未找到ID为[{id}]的乐曲'
        else:
            msg = await new_draw_music_info(music)
        await bot.send(ev, msg)
    else:
        await bot.finish(ev, '仅允许使用id查询', at_sender=True)


@sv.on_fullmatch(['今日mai', '今日舞萌', '今日运势'])
async def day_mai(bot: NoneBot, ev: CQEvent):
    wm_list = ['拼机', '推分', '越级', '下埋', '夜勤', '练底力', '练手法', '打旧框', '干饭', '抓绝赞', '收歌']
    uid = ev.user_id
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
    msg += await draw_music_info(music)
    await bot.send(ev, msg, at_sender=True)


@sv.on_suffix(['是什么歌', '是啥歌'])
async def what_song(bot: NoneBot, ev: CQEvent):
    name: str = ev.message.extract_plain_text().strip().lower()

    data = mai.total_alias_list.by_alias(name)
    if not data:
        await bot.finish(ev, '未找到此歌曲\n可以使用 添加别名 指令给该乐曲添加别名', at_sender=True)
    if len(data) != 1:
        msg = f'找到{len(data)}个相同别名的曲目：\n'
        for songs in data:
            msg += f'{songs.ID}：{songs.Name}\n'
        await bot.finish(ev, msg.strip(), at_sender=True)

    music = mai.total_list.by_id(str(data[0].ID))
    await bot.send(ev, '您要找的是不是：' + (await new_draw_music_info(music)), at_sender=True)


@sv.on_suffix(['有什么别称', '有什么别名'])
async def how_song(bot: NoneBot, ev: CQEvent):
    name: str = ev.message.extract_plain_text().strip().lower()

    alias = mai.total_alias_list.by_alias(name)
    if not alias:
        if name.isdigit():
            alias_id = mai.total_alias_list.by_id(name)
            if not alias_id:
                await bot.finish(ev, '未找到此歌曲\n可以使用 添加别名 指令给该乐曲添加别名', at_sender=True)
            else:
                alias = alias_id
        else:
            await bot.finish(ev, '未找到此歌曲\n可以使用 添加别名 指令给该乐曲添加别名', at_sender=True)
    if len(alias) != 1:
        msg = []
        for songs in alias:
            alias_list = '\n'.join(songs.Alias)
            msg.append(f'ID：{songs.ID}\n{alias_list}')
        await bot.finish(ev, f'找到{len(alias)}个相同别名的曲目：\n' + '\n======\n'.join(msg), at_sender=True)

    if len(alias[0].Alias) == 1:
        await bot.finish(ev, '该曲目没有别名', at_sender=True)

    msg = f'该曲目有以下别名：\nID：{alias[0].ID}\n'
    msg += '\n'.join(alias[0].Alias)
    await bot.send(ev, msg, at_sender=True)


@sv.on_prefix(['添加本地别名', '添加本地别称'])
async def apply_local_alias(bot: NoneBot, ev: CQEvent):
    args: list[str] = ev.message.extract_plain_text().strip().split()
    id, alias_name = args
    if not mai.total_list.by_id(id):
        await bot.finish(ev, f'未找到ID为 [{id}] 的曲目')
    server_exist = await maiApi.get_songs(id)
    if alias_name in server_exist[id]:
        await bot.finish(ev,
                         f'该曲目的别名 <{alias_name}> 已存在别名服务器，不能重复添加别名，如果bot未生效，请联系BOT管理员使用指令 <更新别名库>')
    local_exist = mai.total_alias_list.by_id(id)
    if local_exist and alias_name.lower() in local_exist[0].Alias:
        await bot.finish(ev, f'本地别名库已存在该别名', at_sender=True)
    issave = await update_local_alias(id, alias_name)
    if not issave:
        msg = '添加本地别名失败'
    else:
        msg = f'已成功为ID <{id}> 添加别名 <{alias_name}> 到本地别名库'
    await bot.send(ev, msg, at_sender=True)


@sv.on_prefix(['添加别名', '增加别名', '增添别名', '添加别称'])
async def apply_alias(bot: NoneBot, ev: CQEvent):
    try:
        args: list[str] = ev.message.extract_plain_text().strip().split()
        if not priv.check_priv(ev, priv.ADMIN):
            await bot.finish(ev, '仅允许管理员修改歌曲别名')
        if len(args) != 2:
            await bot.finish(ev, '参数错误', at_sender=True)
        id, alias_name = args
        if not mai.total_list.by_id(id):
            await bot.finish(ev, f'未找到ID为 [{id}] 的曲目')
        isexist = await maiApi.get_songs(id)
        if alias_name in isexist[id]:
            await bot.finish(ev,
                             f'该曲目的别名 <{alias_name}> 已存在，不能重复添加别名，如果bot未生效，请联系BOT管理员使用指令 <更新别名库>')
        tag = ''.join(sample(ascii_uppercase + digits, 5))
        status = await maiApi.post_alias(id, alias_name, tag, ev.user_id)
        if isinstance(status, str):
            await bot.finish(ev, status)
        msg = f'''您已提交以下别名申请
ID：{id}
别名：{alias_name}
{await draw_music_info(mai.total_list.by_id(id))}
现在可用使用唯一标签<{tag}>来进行投票，例如：同意别名 {tag}
浏览{public_addr}查看详情'''
    except ServerError as e:
        log.error(e)
        msg = str(e)
    except ValueError as e:
        msg = str(e)
    await bot.send(ev, msg, at_sender=True)


@sv.on_prefix(['同意别名', '同意别称'])
async def agree_alias(bot: NoneBot, ev: CQEvent):
    try:
        tag: str = ev.message.extract_plain_text().strip().upper()
        status = await maiApi.post_agree_user(tag, ev.user_id)
        if 'content' in status:
            await bot.send(ev, status['content'], at_sender=True)
        else:
            await bot.send(ev, status, at_sender=True)
    except ValueError as e:
        await bot.send(ev, str(e), at_sender=True)


@sv.on_prefix(['当前投票', '当前别名投票', '当前别称投票'])
async def alias_status(bot: NoneBot, ev: CQEvent):
    try:
        args: str = ev.message.extract_plain_text().strip()
        status = await maiApi.get_alias_status()
        if not status:
            await bot.finish(ev, '未查询到正在进行的别名投票', at_sender=True)
        page = max(min(int(args), len(status) // SONGS_PER_PAGE + 1), 1) if args else 1
        result = []
        for num, tag in enumerate(status):
            if (page - 1) * SONGS_PER_PAGE <= num < page * SONGS_PER_PAGE:
                result.append(f'''{tag}：
    - ID：{status[tag]['ID']}
    - 别名：{status[tag]['ApplyAlias']}
    - 票数：{status[tag]['Users']}/{status[tag]['Votes']}''')
        result.append(f'第{page}页，共{len(status) // SONGS_PER_PAGE + 1}页')
        msg = MessageSegment.image(image_to_base64(text_to_image('\n'.join(result))))
    except ServerError as e:
        log.error(str(e))
        msg = str(e)
    except ValueError as e:
        msg = str(e)
    await bot.send(ev, msg, at_sender=True)


@sv.on_suffix('别名推送')
async def alias_on(bot: NoneBot, ev: CQEvent):
    if not priv.check_priv(ev, priv.ADMIN):
        await bot.finish(ev, '仅允许管理员开启', at_sender=True)
    gid = ev.group_id
    args: str = ev.message.extract_plain_text().strip()
    if args == '开启':
        msg = await alias.on(gid)
    elif args == '关闭':
        msg = await alias.off(gid)
    else:
        msg = '指令错误'
    await bot.send(ev, msg, at_sender=True)


@sucmd('aliasswitch', aliases=('全局关闭别名推送', '全局开启别名推送'))
async def _(session: CommandSession):
    if session.ctx.raw_message == '全局关闭别名推送':
        await alias.alias_global_change(False)
        await session.send('已全局关闭maimai别名推送')
    elif session.ctx.raw_message == '全局开启别名推送':
        await alias.alias_global_change(True)
        await session.send('已全局开启maimai别名推送')
    else:
        return


@sucmd('updatealias', aliases='更新别名库')
async def _(session: CommandSession):
    try:
        await mai.get_music_alias()
        log.info('手动更新别名库成功')
        await session.send('手动更新别名库成功')
    except:
        log.error('手动更新别名库失败')
        await session.send('手动更新别名库失败')


@sv.scheduled_job('interval', minutes=5)
async def alias_apply_status():
    try:
        group = await sv.get_enable_groups()
        if (status := await maiApi.get_alias_status()) and alias.config['global']:
            msg = ['检测到新的别名申请']
            for tag in status:
                if status[tag]['IsNew'] and (usernum := status[tag]['Users']) < (votes := status[tag]['Votes']):
                    id = str(status[tag]['ID'])
                    alias_name = status[tag]['ApplyAlias']
                    music = mai.total_list.by_id(id)
                    msg.append(f'{tag}：\nID：{id}\n标题：{music.title}\n别名：{alias_name}\n票数：{usernum}/{votes}')
            if len(msg) != 1:
                for gid in group.keys():
                    if gid in alias.config['disable']:
                        continue
                    try:
                        await sv.bot.send_group_msg(group_id=gid,
                                                    message='\n======\n'.join(msg) + f'\n浏览{public_addr}查看详情')
                        await asyncio.sleep(5)
                    except:
                        continue
        await asyncio.sleep(5)
        if end := await maiApi.get_alias_end():
            if alias.config['global']:
                msg2 = ['以下是已成功添加别名的曲目']
                for ta in end:
                    id = str(end[ta]['ID'])
                    alias_name = end[ta]['ApplyAlias']
                    music = mai.total_list.by_id(id)
                    msg2.append(f'ID：{id}\n标题：{music.title}\n别名：{alias_name}')
                if len(msg2) != 1:
                    for gid in group.keys():
                        if gid in alias.config['disable']:
                            continue
                        try:
                            await sv.bot.send_group_msg(group_id=gid, message='\n======\n'.join(msg2))
                            await asyncio.sleep(5)
                        except:
                            continue
            await mai.get_music_alias()
    except ServerError as e:
        log.error(str(e))
    except ValueError as e:
        log.error(str(e))


@sv.on_prefix('分数线')
async def quert_score(bot: NoneBot, ev: CQEvent):
    args: str = ev.message.extract_plain_text().strip()
    pro = args.split()
    if len(pro) == 1 and pro[0] == '帮助':
        msg = '''此功能为查找某首歌分数线设计。
命令格式：分数线 <难度+歌曲id> <分数线>
例如：分数线 紫799 100
命令将返回分数线允许的 TAP GREAT 容错以及 BREAK 50落等价的 TAP GREAT 数。
以下为 TAP GREAT 的对应表：
GREAT/GOOD/MISS
TAP\t1/2.5/5
HOLD\t2/5/10
SLIDE\t3/7.5/15
TOUCH\t1/2.5/5
BREAK\t5/12.5/25(外加200落)'''
        await bot.send(ev, MessageSegment.image(image_to_base64(text_to_image(msg))), at_sender=True)
    else:
        try:
            result = re.search(r'([绿黄红紫白])\s?([0-9]+)', args)
            level_labels = ['绿', '黄', '红', '紫', '白']
            level_labels2 = ['Basic', 'Advanced', 'Expert', 'Master', 'Re:MASTER']
            level_index = level_labels.index(result.group(1))
            chart_id = result.group(2)
            line = float(pro[-1])
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
            msg = f'''{music.title} {level_labels2[level_index]}
分数线 {line}% 允许的最多 TAP GREAT 数量为 {(total_score * reduce / 10000):.2f}(每个-{10000 / total_score:.4f}%),
BREAK 50落(一共{brk}个)等价于 {(break_50_reduce / 100):.3f} 个 TAP GREAT(-{break_50_reduce / total_score * 100:.4f}%)'''
            await bot.send(ev, msg, at_sender=True)
        except:
            await bot.send(ev, '格式错误，输入“分数线 帮助”以查看帮助信息', at_sender=True)


@sv.on_prefix(['b50', 'B50'])
async def best_50(bot: NoneBot, ev: CQEvent):
    qqid = ev.user_id
    username: str = ev.message.extract_plain_text().strip()
    for i in ev.message:
        if i.type == 'at' and i.data['qq'] != 'all':
            qqid = int(i.data['qq'])

    await bot.send(ev, await generate(qqid, username), at_sender=True)


@sv.on_prefix(['minfo', 'Minfo', 'MINFO'])
async def maiinfo(bot: NoneBot, ev: CQEvent):
    qqid = ev.user_id
    args: str = ev.message.extract_plain_text().strip()
    for i in ev.message:
        if i.type == 'at' and i.data['qq'] != 'all':
            qqid = int(i.data['qq'])
    if not args:
        await bot.finish(ev, '请输入曲目id或曲名', at_sender=True)

    if mai.total_list.by_id(args):
        songs = args
    elif by_t := mai.total_list.by_title(args):
        songs = by_t.id
    else:
        alias = mai.total_alias_list.by_alias(args)
        if not alias:
            await bot.finish(ev, '未找到曲目', at_sender=True)
        elif len(alias) != 1:
            msg = f'找到相同别名的曲目，请使用以下ID查询：\n'
            for songs in alias:
                msg += f'{songs.ID}：{songs.Name}\n'
            await bot.finish(ev, msg.strip(), at_sender=True)
        else:
            songs = str(alias[0].ID)
    if maiApi.token:
        pic = await music_play_data_dev(qqid, songs)
    else:
        pic = await music_play_data(qqid, songs)

    await bot.send(ev, pic, at_sender=True)


@sv.on_prefix(['ginfo', 'Ginfo', 'GINFO'])
async def globinfo(bot: NoneBot, ev: CQEvent):
    args: str = ev.message.extract_plain_text().strip()
    if not args:
        await bot.finish(ev, '请输入曲目id或曲名', at_sender=True)
    if args[0] not in '绿黄红紫白':
        level_index = 3
    else:
        level_index = '绿黄红紫白'.index(args[0])
        args = args[1:].strip()
        if not args:
            await bot.finish(ev, '请输入曲目id或曲名', at_sender=True)
    if mai.total_list.by_id(args):
        id = args
    elif by_t := mai.total_list.by_title(args):
        id = by_t.id
    else:
        alias = mai.total_alias_list.by_alias(args)
        if not alias:
            await bot.finish(ev, '未找到曲目', at_sender=True)
        elif len(alias) != 1:
            msg = f'找到相同别名的曲目，请使用以下ID查询：\n'
            for songs in alias:
                msg += f'{songs.ID}：{songs.Name}\n'
            await bot.finish(ev, msg.strip(), at_sender=True)
        else:
            id = str(alias[0].ID)
    music = mai.total_list.by_id(id)
    if not music.stats:
        await bot.finish(ev, '该乐曲还没有统计信息', at_sender=True)
    if len(music.ds) == 4 and level_index == 4:
        await bot.finish(ev, '该乐曲没有这个等级', at_sender=True)
    if not music.stats[level_index]:
        await bot.finish(ev, '该等级没有统计信息', at_sender=True)
    stats = music.stats[level_index]
    await bot.send(ev, await music_global_data(music, level_index) + f'''
游玩次数：{round(stats.cnt)}
拟合难度：{stats.fit_diff:.2f}
平均达成率：{stats.avg:.2f}%
平均 DX 分数：{stats.avg_dx:.1f}
谱面成绩标准差：{stats.std_dev:.2f}''', at_sender=True)


@sucmd('updatetable', aliases='更新定数表')
async def _(session: CommandSession):
    msg = await update_rating_table()
    await session.send(msg)


@sv.on_suffix('定数表')
async def rating_table(bot: NoneBot, ev: CQEvent):
    args: str = ev.message.extract_plain_text().strip()
    if args in levelList[:5]:
        await bot.send(ev, '只支持查询lv6-15的定数表', at_sender=True)
    elif args in levelList[5:]:
        if args in levelList[-3:]:
            img = ratingdir / '14.png'
        else:
            img = ratingdir / f'{args}.png'
        await bot.send(ev, MessageSegment.image(f'''file:///{img}'''))
    else:
        await bot.send(ev, '无法识别的定数', at_sender=True)


@sv.on_suffix('完成表')
async def rating_table_pf(bot: NoneBot, ev: CQEvent):
    qqid = ev.user_id
    rating: str = ev.message.extract_plain_text().strip()
    if rating in levelList[:5]:
        await bot.send(ev, '只支持查询lv6-15的完成表', at_sender=True)
    elif rating in levelList[5:]:
        img = await rating_table_draw(qqid, rating)
        await bot.send(ev, img, at_sender=True)
    # else:
    #     await bot.send(ev, '无法识别的定数', at_sender=True)


@sv.on_rex(r'^我要在?([0-9]+\+?)?上([0-9]+)分\s?(.+)?')  # 慎用，垃圾代码非常吃机器性能
async def rise_score(bot: NoneBot, ev: CQEvent):
    qqid = ev.user_id
    match: Match[str] = ev['match']
    nickname = ''
    username = None
    for i in ev.message:
        if i.type == 'at' and i.data['qq'] != 'all':
            qqid = int(i.data['qq'])

    rating = match.group(1)
    score = match.group(2)

    if rating and rating not in levelList:
        await bot.finish(ev, '无此等级', at_sender=True)
    elif match.group(3):
        nickname = match.group(3)
        username = match.group(3).strip()

    if qqid != ev.user_id:
        nickname = (await bot.get_stranger_info(user_id=qqid))['nickname']

    data = await rise_score_data(qqid, username, rating, score, nickname)
    await bot.send(ev, data, at_sender=True)


@sv.on_rex(r'^([真超檄橙暁晓桃櫻樱紫菫堇白雪輝辉熊華华爽舞霸宙星祭祝])([極极将舞神者]舞?)进度\s?(.+)?')
async def plate_process(bot: NoneBot, ev: CQEvent):
    qqid = ev.user_id
    match: Match[str] = ev['match']
    nickname = ''
    username = None
    for i in ev.message:
        if i.type == 'at' and i.data['qq'] != 'all':
            qqid = int(i.data['qq'])

    ver = match.group(1)
    plan = match.group(2)
    if f'{ver}{plan}' == '真将':
        await bot.finish(ev, '真系没有真将哦', at_sender=True)
    elif match.group(3):
        nickname = match.group(3)
        username = match.group(3).strip()

    if qqid != ev.user_id:
        nickname = (await bot.get_stranger_info(user_id=qqid))['nickname']

    data = await player_plate_data(qqid, username, ver, plan, nickname)
    await bot.send(ev, data, at_sender=True)


@sv.on_rex(r'^([0-9]+\+?)\s?(.+)进度\s?(.+)?')
async def level_process(bot: NoneBot, ev: CQEvent):
    qqid = ev.user_id
    match: Match[str] = ev['match']
    nickname = ''
    username = None
    for i in ev.message:
        if i.type == 'at' and i.data['qq'] != 'all':
            qqid = int(i.data['qq'])

    rating = match.group(1)
    rank = match.group(2)

    if rating not in levelList:
        await bot.finish(ev, '无此等级', at_sender=True)
    if rank.lower() not in scoreRank + comboRank + syncRank:
        await bot.finish(ev, '无此评价等级', at_sender=True)
    if levelList.index(rating) < 11 or (rank.lower() in scoreRank and scoreRank.index(rank.lower()) < 8):
        await bot.finish(ev, '兄啊，有点志向好不好', at_sender=True)
    elif match.group(3):
        nickname = match.group(3)
        username = match.group(3).strip()

    if qqid != ev.user_id:
        nickname = (await bot.get_stranger_info(user_id=qqid))['nickname']

    data = await level_process_data(qqid, username, rating, rank, nickname)
    await bot.send(ev, data, at_sender=True)


@sv.on_rex(r'^([0-9]+\+?)分数列表\s?([0-9]+)?\s?(.+)?')
async def level_achievement_list(bot: NoneBot, ev: CQEvent):
    qqid = ev.user_id
    match: Match[str] = ev['match']
    nickname = ''
    username = None
    for i in ev.message:
        if i.type == 'at' and i.data['qq'] != 'all':
            qqid = int(i.data['qq'])

    rating = match.group(1)
    page = match.group(2)

    if rating not in levelList:
        await bot.finish(ev, '无此等级', at_sender=True)
    elif match.group(3):
        nickname = match.group(3)
        username = match.group(3).strip()

    if qqid != ev.user_id:
        nickname = (await bot.get_stranger_info(user_id=qqid))['nickname']

    data = await level_achievement_list_data(qqid, username, rating, page, nickname)
    await bot.send(ev, data, at_sender=True)


@sv.on_prefix(['查看排名', '查看排行'])
async def rating_ranking(bot: NoneBot, ev: CQEvent):
    args: str = ev.message.extract_plain_text().strip()
    page = 1
    name = ''
    if args.isdigit():
        page = int(args)
    else:
        name = args.lower()

    data = await rating_ranking_data(name, page)
    await bot.send(ev, data, at_sender=True)


@sv.on_fullmatch('猜歌')
async def guess_music(bot: NoneBot, ev: CQEvent):
    gid = str(ev.group_id)
    if ev.group_id not in guess.config['enable']:
        await bot.finish(ev, '该群已关闭猜歌功能，开启请输入 开启mai猜歌')
    if gid in guess.Group:
        await bot.finish(ev, '该群已有正在进行的猜歌')
    await guess.start(gid)
    await bot.send(ev,
                   '我将从热门乐曲中选择一首歌，每隔8秒描述它的特征，请输入歌曲的 id 标题 或 别名（需bot支持，无需大小写） 进行猜歌（DX乐谱和标准乐谱视为两首歌）。猜歌时查歌等其他命令依然可用。')
    await asyncio.sleep(4)
    for cycle in range(7):
        if ev.group_id not in guess.config['enable'] or gid not in guess.Group or guess.Group[gid].end:
            break
        if cycle < 6:
            await bot.send(ev, f'{cycle + 1}/7 这首歌{guess.Group[gid].options[cycle]}')
            await asyncio.sleep(8)
        else:
            await bot.send(ev,
                           f'''7/7 这首歌封面的一部分是：\n{MessageSegment.image(guess.Group[gid].img)}答案将在30秒后揭晓''')
            for _ in range(30):
                await asyncio.sleep(1)
                if gid in guess.Group:
                    if ev.group_id not in guess.config['enable'] or guess.Group[gid].end:
                        return
                else:
                    return
            guess.Group[gid].end = True
            answer = f'''答案是：\n{await new_draw_music_info(guess.Group[gid].music)}'''
            guess.end(gid)
            await bot.send(ev, answer)


@sv.on_message()
async def guess_music_solve(bot: NoneBot, ev: CQEvent):
    gid = str(ev.group_id)
    if gid not in guess.Group:
        return
    ans: str = ev.message.extract_plain_text().strip().lower()
    if ans.lower() in guess.Group[gid].answer:
        guess.Group[gid].end = True
        answer = f'''猜对了，答案是：\n{await new_draw_music_info(guess.Group[gid].music)}'''
        guess.end(gid)
        await bot.send(ev, answer, at_sender=True)


@sv.on_fullmatch('重置猜歌')
async def reset_guess(bot: NoneBot, ev: CQEvent):
    gid = str(ev.group_id)
    if not priv.check_priv(ev, priv.ADMIN):
        msg = '仅允许管理员开启'
    elif gid in guess.Group:
        msg = '已重置该群猜歌'
        guess.end(gid)
    else:
        msg = '该群未处在猜歌状态'
    await bot.send(ev, msg)


@sv.on_suffix('mai猜歌')
async def guess_on_off(bot: NoneBot, ev: CQEvent):
    if not priv.check_priv(ev, priv.ADMIN):
        msg = '仅允许管理员开启'
    gid = ev.group_id
    args: str = ev.message.extract_plain_text().strip()
    if args == '开启':
        msg = await guess.on(gid)
    elif args == '关闭':
        msg = await guess.off(gid)
    else:
        msg = '指令错误'

    await bot.send(ev, msg, at_sender=True)


@sv.scheduled_job('cron', hour='4')
async def _():
    try:
        await mai.get_music()
        mai.guess()
    except:
        return
    log.info('maimaiDX数据更新完毕')
