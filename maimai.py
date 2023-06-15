import asyncio
import re
from random import sample
from string import ascii_uppercase, digits

import aiofiles
from nonebot import NoneBot, on_websocket_connect

from hoshino import Service, priv
from hoshino.service import sucmd
from hoshino.typing import CommandSession, CQEvent, MessageSegment

from . import *
from .libraries.image import *
from .libraries.maimaidx_api_data import *
from .libraries.maimaidx_music import alias, guess, mai, update_local_alias
from .libraries.maimaidx_project import *
from .libraries.tool import *

public_addr = 'https://vote.yuzuai.xyz/'

sv_help = '''
可用命令如下：
帮助maimaiDX 查看指令帮助
项目地址maimaiDX 查看项目地址
今日mai,今日舞萌,今日运势 查看今天的舞萌运势
XXXmaimaiXXX什么 随机一首歌
随个[dx/标准][绿黄红紫白]<难度> 随机一首指定条件的乐曲
[查歌/search]<乐曲标题的一部分> 查询符合条件的乐曲
[绿黄红紫白]id <歌曲编号> 查询乐曲信息或谱面信息
<歌曲别名>是什么歌 查询乐曲别名对应的乐曲
<id/歌曲别称>有什么别称 查询乐曲对应的别称 识别id，歌名和别名
添加别称 <歌曲ID> <歌曲别名>   申请添加歌曲别名 
当前别名投票   查看正在进行的投票 
同意别名 <标签>    同意其中一个标签的别名申请，可通过指令 当前别名投票 查看
开启/关闭别名推送    开启或关闭新别名投票的推送
[定数查歌/search base] <定数>  查询定数对应的乐曲
[定数查歌/search base] <定数下限> <定数上限>
[bpm查歌/search bpm] <bpm>  查询bpm对应的乐曲
[bpm查歌/search bpm] <bpm下限> <bpm上限> (<页数>)
[曲师查歌/search artist] <曲师名字的一部分> (<页数>)  查询曲师对应的乐曲
[谱师查歌/search charter] <谱师名字的一部分> (<页数>)  查询名字对应的乐曲
分数线 <难度+歌曲id> <分数线> 详情请输入“分数线 帮助”查看
开启/关闭mai猜歌 开关猜歌功能
猜歌 顾名思义，识别id，歌名和别名
重置猜歌 猜歌卡住时使用
minfo<@> <id/别称/曲名> 查询单曲成绩
ginfo [绿黄红紫白] <id/别称/曲名> 查询乐曲游玩总览，不加难度默认为紫谱
b50 <名字> 或 @某人 查B50
我要(在<难度>)上<分数>分 <名字> 或 @某人 查看推荐的上分乐曲
<牌子名称>进度 <名字> 或 @某人 查看牌子完成进度
<等级><评价>进度 <名字> 或 @某人 查看等级评价完成进度
<等级>分数列表<页数> <名字> 或者 @某人 查看等级分数列表（从高至低）
查看排名,查看排行 <页数/名字> 查看某页或某玩家在水鱼网站的用户ra排行
添加机厅 <名称> <位置> <机台数量> <别称1> <别称2> ... 添加机厅信息
删除机厅 <名称> 删除机厅信息
修改机厅 <名称> [数量/别称] [<数量>/添加/删除] <别称1> <别称2> ... 修改机厅信息
订阅机厅 <名称> 订阅机厅，简化后续指令
查看订阅 查看群组订阅机厅的信息
取消订阅,取消订阅机厅 取消群组机厅订阅
查找机厅,查询机厅,机厅查找,机厅查询 <关键词> 查询对应机厅信息
<名称>人数设置,设定,=,增加,加,+,减少,减,-<人数> 操作排卡人数
<名称>有多少人,有几人,有几卡,几人,几卡 查看排卡人数

BOT管理员私聊指令：
全局关闭/开启别名推送 开关所有群的别名推送
'''.strip()

SV_HELP = '请使用 帮助maimaiDX 查看帮助'
sv = Service('maimaiDX', manage_priv=priv.ADMIN, enable_on_default=False, help_=SV_HELP)
sv_arcade = Service('maimaiDX排卡', manage_priv=priv.ADMIN, enable_on_default=False, help_=SV_HELP)

def song_level(ds1: float, ds2: float) -> list:
    result = []
    music_data = mai.total_list.filter(ds=(ds1, ds2))
    for music in sorted(music_data, key=lambda i: int(i.id)):
        for i in music.diff:
            result.append((music.id, music.title, music.ds[i], diffs[i], music.level[i]))
    return result


@on_websocket_connect
async def get_music(event: CQEvent):
    """
    bot启动时开始获取所有数据
    """
    log.info('正在获取maimai所有曲目信息')
    await mai.get_music()
    log.info('正在获取maimai所有曲目别名信息')
    await mai.get_music_alias()
    log.info('正在获取maimai所有机厅信息')
    await download_arcade_info()
    log.info('maimai数据获取完成')
    mai.guess()

@sv.on_fullmatch(['帮助maimaiDX', '帮助maimaidx'])
async def dx_help(bot: NoneBot, ev: CQEvent):
    await bot.send(ev, MessageSegment.image(image_to_base64(text_to_image(sv_help))), at_sender=True)

@sv.on_fullmatch(['项目地址maimaiDX', '项目地址maimaidx'])
async def dx_github(bot: NoneBot, ev: CQEvent):
    await bot.send(ev, f'项目地址：https://github.com/Yuri-YuzuChaN/maimaiDX\n求star，求宣传~', at_sender=True)

@sv.on_prefix(['定数查歌', 'search base'])
async def search_dx_song_level(bot: NoneBot, ev: CQEvent):
    args = ev.message.extract_plain_text().strip().split()
    if len(args) > 3 or len(args) == 0:
        await bot.finish(ev, '命令格式为\n定数查歌 <定数> [页数]\n定数查歌 <定数下限> <定数上限> [页数]', at_sender=True)
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
            music_data = mai.total_list.filter(level=level, type=tp)
        else:
            music_data = mai.total_list.filter(level=level, diff=['绿黄红紫白'.index(match.group(2))], type=tp)
        if len(music_data) == 0:
            msg = '没有这样的乐曲哦。'
        else:
            msg = await draw_music_info(music_data.random())
        await bot.send(ev, msg, at_sender=True)
    except:
        await bot.send(ev, '随机命令错误，请检查语法', at_sender=True)

@sv.on_rex(r'.*mai.*什么')
async def random_day_song(bot: NoneBot, ev: CQEvent):
    await bot.send(ev, await draw_music_info(mai.total_list.random()))

@sv.on_prefix(['查歌', 'search'])
async def search_song(bot: NoneBot, ev: CQEvent):
    name: str = ev.message.extract_plain_text().strip()
    if not name:
        return
    result = mai.total_list.filter(title_search=name)
    if len(result) == 0:
        await bot.send(ev, '没有找到这样的乐曲。', at_sender=True)
    elif len(result) == 1:
        msg = await draw_music_info(result.random())
        await bot.send(ev, msg)
    elif len(result) < 50:
        search_result = ''
        for music in sorted(result, key=lambda i: int(i.id)):
            search_result += f'{music.id}. {music.title}\n'
        await bot.send(ev, search_result.strip(), at_sender=True)
    else:
        await bot.send(ev, f'结果过多（{len(result)} 条），请缩小查询范围。', at_sender=True)

@sv.on_rex(r'^([绿黄红紫白]?)\s?id\s?([0-9]+)$')
async def query_chart(bot: NoneBot, ev: CQEvent):
    match: Match[str] = ev['match']
    msg = await query_chart_data(match)

    await bot.send(ev, msg)

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
    await bot.send(ev, '您要找的是不是：' + (await draw_music_info(music)), at_sender=True)

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
    server_exist = await get_music_alias('alias', {'id': id})
    if alias_name in server_exist[id]:
        await bot.finish(ev, f'该曲目的别名 <{alias_name}> 已存在别名服务器，不能重复添加别名，如果bot未生效，请联系BOT管理员使用指令 <更新别名库>')
    local_exist = mai.total_alias_list.by_alias(alias_name)
    if local_exist:
        await bot.finish(ev, f'本地别名库已存在该别名', at_sender=True)
    issave = await update_local_alias(id, alias_name)
    if not issave:
        msg = '添加本地别名失败'
    else:
        msg = f'已成功为ID <{id}> 添加别名 <{alias_name}> 到本地别名库'
    await bot.send(ev, msg, at_sender=True)

@sv.on_prefix(['添加别名', '增加别名', '增添别名', '添加别称'])
async def apply_alias(bot: NoneBot, ev: CQEvent):
    args: list[str] = ev.message.extract_plain_text().strip().split()
    if not priv.check_priv(ev, priv.ADMIN):
        await bot.finish(ev, '仅允许管理员修改歌曲别名')
    if len(args) != 2:
        await bot.finish(ev, '参数错误', at_sender=True)
    id, alias_name = args
    if not mai.total_list.by_id(id):
        await bot.finish(ev, f'未找到ID为 [{id}] 的曲目')
    isexist = await get_music_alias('alias', {'id': id})
    if alias_name in isexist[id]:
        await bot.finish(ev, f'该曲目的别名 <{alias_name}> 已存在，不能重复添加别名，如果bot未生效，请联系BOT管理员使用指令 <更新别名库>')
    tag = ''.join(sample(ascii_uppercase + digits, 5))
    status = await post_music_alias('apply', {'id': id, 'aliasname': alias_name, 'tag': tag, 'uid': ev.user_id})
    if 'error' in status:
        await bot.finish(ev, status['error'])
    elif isinstance(status, str):
        await bot.finish(ev, status)
    await bot.send(ev, f'''您已提交以下别名申请
ID：{id}
别名：{alias_name}
{await draw_music_info(mai.total_list.by_id(id))}
现在可用使用唯一标签<{tag}>来进行投票，例如：同意别名 {tag}
浏览{public_addr}查看详情''', at_sender=True)

@sv.on_prefix(['同意别名', '同意别称'])
async def agree_alias(bot: NoneBot, ev: CQEvent):
    tag: str = ev.message.extract_plain_text().strip().upper()
    status = await post_music_alias('agree', {'tag': tag, 'uid': ev.user_id})
    if 'content' in status:
        await bot.send(ev, status['content'], at_sender=True)
    elif 'error' in status:
        await bot.send(ev, status['error'], at_sender=True)
    else:
        await bot.send(ev, status, at_sender=True)

@sv.on_prefix(['当前投票', '当前别名投票', '当前别称投票'])
async def alias_status(bot: NoneBot, ev: CQEvent):
    status = await get_music_alias('status')
    if 'error' in status:
        await bot.finish(ev, status['error'])
    if not status:
        await bot.finish(ev, '未查询到正在进行的别名投票', at_sender=True)
    msg = []
    for tag in status:
        id = str(status[tag]['ID'])
        alias_name = status[tag]['ApplyAlias']
        usernum = status[tag]['Users']
        votes = status[tag]['Votes']
        msg.append(f'{tag}：\n{await draw_music_info(mai.total_list.by_id(id))}\n别名：{alias_name}\n票数：{usernum}/{votes}')
    await bot.send(ev, f'浏览{public_addr}查看详情或查看以下合并消息')
    await bot.send_group_forward_msg(group_id=ev.group_id, messages=render_forward_msg(msg, ev.self_id, BOTNAME))

@sv.on_fullmatch('开启别名推送')
async def alias_on(bot: NoneBot, ev: CQEvent):
    gid = ev.group_id
    if not priv.check_priv(ev, priv.ADMIN):
        msg = '仅允许管理员开启'
    elif gid in alias.config['enable']:
        msg = '该群已开启别名推送功能'
    else:
        alias.alias_change(gid, True)
        msg = '已开启该群别名推送功能'
    await bot.send(ev, msg, at_sender=True)

@sv.on_fullmatch('关闭别名推送')
async def alias_off(bot: NoneBot, ev: CQEvent):
    gid = ev.group_id
    if not priv.check_priv(ev, priv.ADMIN):
        msg = '仅允许管理员关闭'
    elif gid in alias.config['disable']:
        msg = '该群已关闭别名推送功能'
    else:
        alias.alias_change(gid, False)
        msg = '已关闭该群别名推送功能'
    await bot.send(ev, msg, at_sender=True)

@sucmd('aliasswitch', aliases=('全局关闭别名推送', '全局开启别名推送'))
async def _(session: CommandSession):
    if session.ctx.raw_message == '全局关闭别名推送':
        alias.alias_global_change(False)
        await session.send('已全局关闭maimai别名推送')
    elif session.ctx.raw_message == '全局开启别名推送':
        alias.alias_global_change(True)
        await session.send('已全局开启maimai别名推送')
    else:
        return
    
@sucmd('updatealias', aliases=('更新别名库'))
async def _(session: CommandSession):
    try:
        await mai.get_music_alias()
        log.error('手动更新别名库成功')
        await session.send('手动更新别名库成功')
    except:
        log.error('手动更新别名库失败')
        await session.send('手动更新别名库失败')

@sv.scheduled_job('interval', minutes=5)
async def alias_apply_status():
    group = await sv.get_enable_groups()
    if status := await get_music_alias('status'):
        if 'error' in status:
            log.error(f'发生错误：{status["error"]}')
            raise ValueError
        if alias.config['global']:
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
                        await sv.bot.send_group_msg(group_id=gid, message='\n======\n'.join(msg) + f'\n浏览{public_addr}查看详情')
                        await asyncio.sleep(5)
                    except: 
                        continue
    await asyncio.sleep(5)
    if end := await get_music_alias('end'):
        if 'error' in end:
            log.error(f'发生错误：{end["error"]}')
            raise ValueError
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
    args: str = ev.message.extract_plain_text().strip()
    for i in ev.message:
        if i.type == 'at' and i.data['qq'] != 'all':
            qqid = int(i.data['qq'])

    if args:
        payload = {'username': args}
    else:
        payload = {'qq': qqid}
    payload['b50'] = True
    await bot.send(ev, await generate(payload), at_sender=True)

@sv.on_prefix(['minfo', 'Minfo', 'MINFO'])
async def maiinfo(bot: NoneBot, ev: CQEvent):
    qqid = ev.user_id
    args: str = ev.message.extract_plain_text().strip()
    for i in ev.message:
        if i.type == 'at' and i.data['qq'] != 'all':
            qqid = int(i.data['qq'])
    if not args:
        await bot.finish(ev, '请输入曲目id或曲名', at_sender=True)
    payload = {'qq': qqid}
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
    if token:
        pic = await music_play_data_dev(payload, id)
    else:
        pic = await music_play_data(payload, id)

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
    if level_index >= len(music.stats) or not music.stats[level_index]:
        await bot.finish(ev, '该乐曲没有这个等级', at_sender=True)
    stats = music.stats[level_index]
    await bot.send(ev, await music_global_data(music, level_index) + f'''
游玩次数：{round(stats.cnt)}
拟合难度：{stats.fit_diff:.2f}
平均达成率：{stats.avg:.2f}%
平均 DX 分数：{stats.avg_dx:.1f}
谱面成绩标准差：{stats.std_dev:.2f}''', at_sender=True)

@sv.on_rex(r'^我要在?([0-9]+\+?)?上([0-9]+)分\s?(.+)?')  # 慎用，垃圾代码非常吃机器性能
async def rise_score(bot: NoneBot, ev: CQEvent):
    qqid = ev.user_id
    match: Match[str] = ev['match']
    nickname = ''
    for i in ev.message:
        if i.type == 'at' and i.data['qq'] != 'all':
            qqid = int(i.data['qq'])

    if match.group(1) and match.group(1) not in levelList:
        await bot.finish(ev, '无此等级', at_sender=True)
    elif match.group(3):
        nickname = match.group(3)
        payload = {'username': match.group(3).strip()}
    else:
        payload = {'qq': qqid}

    if qqid != ev.user_id:
        nickname = (await bot.get_stranger_info(user_id=qqid))['nickname']
        
    data = await rise_score_data(payload, match, nickname)
    await bot.send(ev, data, at_sender=True)

@sv.on_rex(r'^([真超檄橙暁晓桃櫻樱紫菫堇白雪輝辉熊華华爽舞霸宙星])([極极将舞神者]舞?)进度\s?(.+)?')
async def plate_process(bot: NoneBot, ev: CQEvent):
    qqid = ev.user_id
    match: Match[str] = ev['match']
    nickname = ''
    for i in ev.message:
        if i.type == 'at' and i.data['qq'] != 'all':
            qqid = int(i.data['qq'])

    if f'{match.group(1)}{match.group(2)}' == '真将':
        await bot.finish(ev, '真系没有真将哦', at_sender=True)
    elif match.group(3):
        nickname = match.group(3)
        payload = {'username': match.group(3).strip()}
    else:
        payload = {'qq': qqid}

    if qqid != ev.user_id:
        nickname = (await bot.get_stranger_info(user_id=qqid))['nickname']
    
    if match.group(1) in ['霸', '舞']:
        payload['version'] = list(set(version for version in list(plate_to_version.values())[:-9]))
    else:
        payload['version'] = [plate_to_version[match.group(1)]]

    data = await player_plate_data(payload, match, nickname)
    await bot.send(ev, data, at_sender=True)

@sv.on_rex(r'^([0-9]+\+?)\s?(.+)进度\s?(.+)?')
async def level_process(bot: NoneBot, ev: CQEvent):
    qqid = ev.user_id
    match: Match[str] = ev['match']
    nickname = ''
    for i in ev.message:
        if i.type == 'at' and i.data['qq'] != 'all':
            qqid = int(i.data['qq'])

    if match.group(1) not in levelList:
        await bot.finish(ev, '无此等级', at_sender=True)
    if match.group(2).lower() not in scoreRank + comboRank + syncRank:
        await bot.finish(ev, '无此评价等级', at_sender=True)
    if levelList.index(match.group(1)) < 11 or (match.group(2).lower() in scoreRank and scoreRank.index(match.group(2).lower()) < 8):
        await bot.finish(ev, '兄啊，有点志向好不好', at_sender=True)
    elif match.group(3):
        nickname = match.group(3)
        payload = {'username': match.group(3).strip()}
    else:
        payload = {'qq': qqid}

    if qqid != ev.user_id:
        nickname = (await bot.get_stranger_info(user_id=qqid))['nickname']

    payload['version'] = list(set(version for version in plate_to_version.values()))

    data = await level_process_data(payload, match, nickname)
    await bot.send(ev, data, at_sender=True)

@sv.on_rex(r'^([0-9]+\+?)分数列表\s?([0-9]+)?\s?(.+)?')
async def level_achievement_list(bot: NoneBot, ev: CQEvent):
    qqid = ev.user_id
    match: Match[str] = ev['match']
    nickname = ''
    for i in ev.message:
        if i.type == 'at' and i.data['qq'] != 'all':
            qqid = int(i.data['qq'])
        
    if match.group(1) not in levelList:
        await bot.finish(ev, '无此等级', at_sender=True)
    elif match.group(3):
        nickname = match.group(3)
        payload = {'username': match.group(3).strip()}
    else:
        payload = {'qq': qqid}

    if qqid != ev.user_id:
        nickname = (await bot.get_stranger_info(user_id=qqid))['nickname']

    payload['version'] = list(set(version for version in plate_to_version.values()))

    data = await level_achievement_list_data(payload, match, nickname)
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

async def guess_music_loop(bot: NoneBot, ev: CQEvent):
    gid = str(ev.group_id)
    cycle = guess.Group[gid]['cycle']
    if cycle != 0:
        await asyncio.sleep(8)
    else:
        await asyncio.sleep(4)
    _guess = guess.Group[gid]['object']
    if ev.group_id not in guess.config['enable'] or _guess.is_end:
        return
    if cycle < 6:
        await bot.send(ev, f'{cycle + 1}/7 这首歌{_guess.guess_options[cycle]}')
    else:
        await bot.send(ev,f'''7/7 这首歌封面的一部分是：
{MessageSegment.image(_guess.b64image)}
答案将在30秒后揭晓''')
        await give_answer(bot, ev)
    guess.Group[gid]['cycle'] += 1
    await guess_music_loop(bot, ev)

async def give_answer(bot: NoneBot, ev: CQEvent):
    gid = str(ev.group_id)
    await asyncio.sleep(30)
    _guess = guess.Group[gid]['object']
    if ev.group_id not in guess.config['enable'] or _guess.is_end:
        return
    _guess.is_end = True
    guess.end(gid)
    msg = f'''答案是：
{await draw_music_info(_guess.music)}'''
    await bot.finish(ev, msg)

@sv.on_fullmatch('猜歌')
async def guess_music(bot: NoneBot, ev: CQEvent):
    gid = str(ev.group_id)
    if ev.group_id not in guess.config['enable']:
        await bot.finish(ev, '该群已关闭猜歌功能，开启请输入 开启mai猜歌')
    if gid in guess.Group:
        await bot.finish(ev, '该群已有正在进行的猜歌')
    guess.add(gid)
    await mai.start()
    guess.start(gid, mai, 0)
    await bot.send(ev, '我将从热门乐曲中选择一首歌，每隔8秒描述它的特征，请输入歌曲的 id 标题 或 别名（需bot支持，无需大小写） 进行猜歌（DX乐谱和标准乐谱视为两首歌）。猜歌时查歌等其他命令依然可用。')
    await guess_music_loop(bot, ev)

@sv.on_message()
async def guess_music_solve(bot: NoneBot, ev: CQEvent):
    gid = str(ev.group_id)
    if gid not in guess.Group:
        return
    ans: str = ev.message.extract_plain_text().strip().lower()
    _guess = guess.Group[gid]['object']
    if ans.lower() in _guess.answer:
        _guess.is_end = True
        guess.end(gid)
        msg = f'''猜对了，答案是：
{await draw_music_info(_guess.music)}'''
        await bot.finish(ev, msg, at_sender=True)

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

@sv.on_fullmatch('开启mai猜歌')
async def guess_on(bot: NoneBot, ev: CQEvent):
    gid = ev.group_id
    if not priv.check_priv(ev, priv.ADMIN):
        msg = '仅允许管理员开启'
    elif gid in guess.config['enable']:
        msg = '该群已开启猜歌功能'
    else:
        guess.guess_change(gid, True)
        msg = '已开启该群猜歌功能'

    await bot.send(ev, msg, at_sender=True)

@sv.on_fullmatch('关闭mai猜歌')
async def guess_off(bot: NoneBot, ev: CQEvent):
    gid = ev.group_id
    if not priv.check_priv(ev, priv.ADMIN):
        msg = '仅允许管理员关闭'
    elif gid in guess.config['disable']:
        msg = '该群已关闭猜歌功能'
    else:
        guess.guess_change(gid, False)
        if str(gid) in guess.Group:
            guess.end(str(gid))
        msg = '已关闭该群猜歌功能'

    await bot.send(ev, msg, at_sender=True)

@sv_arcade.on_prefix('添加机厅', '新增机厅')
async def add_arcade(bot: NoneBot, ev: CQEvent):
    args: list[str] = ev.message.extract_plain_text().strip().lower().split()
    if not priv.check_priv(ev, priv.SUPERUSER):
        msg = '仅允许主人添加机厅\n请使用 来杯咖啡+内容 联系主人'
    elif len(args) == 1 and args[0] in ['帮助', 'help', '指令帮助']:
        msg = '添加机厅指令格式：添加机厅 <名称> <位置> <机台数量> <别称1> <别称2> ...'
    elif len(args) > 1:
        if len(args) > 3 and not args[2].isdigit():
            msg = '格式错误：添加机厅 <名称> <位置> <机台数量> <别称1> <别称2> ...'
        else:
            arcade_dict = {'name': args[0], 'location': args[1],
                           'num': int(args[2]) if len(args) > 2 else 1,
                           'alias': args[3:] if len(args) > 3 else [],
                           'group': [], 'person': 0,
                           'by': '', 'time': ''}
            msg = modify('add', None, arcade_dict)
    else:
        msg = '格式错误：添加机厅 <名称> <位置> <机台数量> <别称1> <别称2> ...'

    await bot.send(ev, msg, at_sender=True)

@sv_arcade.on_prefix('删除机厅', '移除机厅')
async def delele_arcade(bot: NoneBot, ev: CQEvent):
    args = ev.message.extract_plain_text().strip().lower()
    if not priv.check_priv(ev, priv.SUPERUSER):
        msg = '仅允许主人删除机厅\n请使用 来杯咖啡+内容 联系主人'
    elif not args:
        msg = '格式错误：删除机厅 <名称>'
    else:
        msg = modify('delete', None, {'name': args})
    await bot.send(ev, msg, at_sender=True)

@sv_arcade.on_prefix('修改机厅', '编辑机厅')
async def modify_arcade(bot: NoneBot, ev: CQEvent):
    args = ev.message.extract_plain_text().strip().lower().split()
    if not priv.check_priv(ev, priv.ADMIN):
        msg = '仅允许管理员修改机厅信息'
    elif len(args) == 1 and args[0] in ['帮助', 'help', '指令帮助']:
        msg = '修改机厅指令格式：修改机厅 <名称> [数量/别称] [<数量>/添加/删除] <别称1> <别称2> ...'
    elif args[1] == '数量':
        if len(args) == 3 and args[2].isdigit():
            msg = modify('modify', 'num', {'name': args[0], 'num': args[2]})
        else:
            msg = '格式错误：修改机厅 <名称> 数量 <数量>'
    elif args[1] == '别称':
        if args[2] in ['添加', '删除'] and len(args) > 3:
            msg = modify('modify', 'alias_delete' if args[2] == '删除' else 'alias_add',
                    {'name': args[0], 'alias': args[3] if args[2] == '删除' else args[3:]})
        else:
            msg = '格式错误：修改机厅 <名称> 别称 [添加/删除] <别称1> <别称2> ...'
    else:
        msg = '格式错误：修改机厅 <名称> [数量/别称] [<数量>/添加/删除] <别称1> <别称2> ...'
    
    await bot.send(ev, msg, at_sender=True)

@sv_arcade.on_prefix('订阅机厅')
async def subscribe_arcade(bot: NoneBot, ev: CQEvent):
    gid = ev.group_id
    args = ev.message.extract_plain_text().strip().lower()
    if not priv.check_priv(ev, priv.ADMIN):
        await bot.finish(ev, '仅允许管理员订阅')
    for a in arcades:
        if gid in a['group']:
            await bot.finish(ev, f'该群已订阅机厅：{a["name"]}', at_sender=True)
    if not args:
        msg = '格式错误：订阅机厅 <名称>'
    else:
        msg = modify('modify', 'subscribe', {'name': args, 'gid': gid})
        
    await bot.send(ev, msg, at_sender=True)

@sv_arcade.on_fullmatch('查看订阅', '查看订阅机厅')
async def check_subscribe(bot: NoneBot, ev: CQEvent):
    gid = ev.group_id
    result = None
    for a in arcades:
        if gid in a['group']:
            result = a
            break
    if result:
        msg = f'''群{gid}订阅机厅信息如下：
{result["name"]} {result["location"]} 机台数量 {result["num"]} {"别称：" if len(result["alias"]) > 0 else ""}{"/".join(result["alias"])}'''.strip()
    else:
        msg = '该群未订阅任何机厅'
    await bot.send(ev, msg, at_sender=True)

@sv_arcade.on_fullmatch(['取消订阅', '取消订阅机厅'])
async def unsubscribe_arcade(bot: NoneBot, ev: CQEvent):
    gid = ev.group_id
    if not priv.check_priv(ev, priv.ADMIN):
        await bot.finish(ev, '仅允许管理员订阅')
    result = None
    for a in arcades:
        if gid in a['group']:
            result = a
            break
    if result:
        msg = modify('modify', 'unsubscribe', {'name': result['name'], 'gid': gid})
    else:
        msg = '该群未订阅任何机厅，请使用 订阅机厅 <名称> 指令订阅机厅'
    
    await bot.send(ev, msg, at_sender=True)

@sv_arcade.on_prefix(['查找机厅', '查询机厅', '机厅查找', '查找机厅', '机厅查询', '查询机厅', '搜素机厅', '机厅搜素'])
async def search_arcade(bot: NoneBot, ev: CQEvent):
    args: str = ev.message.extract_plain_text().strip().lower()
    if not args:
        await bot.finish(ev, '格式错误：查找机厅 <关键词>', at_sender=True)

    result = []
    for a in arcades:
        match = False
        if args in a['name']:
            match = True
        if args in a['location']:
            match = True
        for alias in a['alias']:
            if args in alias:
                match = True
                break
        if match:
            result.append(a)
    if len(result) == 0:
        await bot.finish(ev, '没有这样的机厅哦', at_sender=True)
    msg = '为您找到以下机厅：\n'
    for r in result:
        msg += f'{r["name"]} {r["location"]} 机台数量 {r["num"]} {"别称：" if len(r["alias"]) > 0 else ""}{"/".join(r["alias"])}'.strip() + '\n'
    if len(result) < 5:
        await bot.send(ev, msg.strip(), at_sender=True)
    else:
        await bot.send(ev, MessageSegment.image(image_to_base64(text_to_image(msg.strip()))), at_sender=True)

@sv_arcade.on_rex(r'^(.+)?\s?(设置|设定|＝|=|增加|添加|加|＋|\+|减少|降低|减|－|-)\s?([0-9]+|＋|\+|－|-)(人|卡)?$')
async def arcade_person(bot: NoneBot, ev: CQEvent):
    try:
        match: Match[str] = ev['match']
        gid = ev.group_id
        nickname = ev.sender['nickname']
        if not match.group(3).isdigit() and match.group(3) not in ['＋', '+', '－', '-']:
            await bot.finish(ev, '请输入正确的数字', at_sender=True)

        msg = arcade_person_data(match, gid, nickname)

        await bot.send(ev, msg, at_sender=True)
    except: pass

@sv_arcade.on_suffix(['有多少人', '有几人', '有几卡', '多少人', '多少卡', '几人', 'jr', '几卡'])
async def arcade_query_person(bot: NoneBot, ev: CQEvent):
    gid = ev.group_id
    arg = ev.message.extract_plain_text().strip().lower()
    result = None
    if arg:
        for a in arcades:
            if arg == a['name']:
                result = a
                break
            if arg in a['alias']:
                result = a
                break
        if not result:
            await bot.finish(ev, '没有这样的机厅哦', at_sender=True)
    if not result:
        for a in arcades:
            if gid in a['group']:
                result = a
                break
    if result:
        msg = f'{arg}有{result["person"]}人\n'
        if result['num'] > 1:
            msg += f'机均{result["person"] / result["num"]:.2f}人\n'
        if result['by']:
            msg += f'由{result["by"]}更新于{result["time"]}'
        await bot.send(ev, msg.strip(), at_sender=True)
    else:
        await bot.send(ev, '该群未订阅任何机厅，请使用 订阅机厅 <名称> 指令订阅机厅', at_sender=True)

@sv.scheduled_job('cron', hour='4')
async def Data_Update():
    try:
        await download_arcade_info(False)
        for a in arcades:
            a['person'] = 0
            a['by'] = '自动清零'
            a['time'] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        async with aiofiles.open(arcades_json, 'w', encoding='utf-8') as f:
            await f.write(json.dumps(arcades, ensure_ascii=False, indent=4))
        await mai.get_music()
    except:
        return
    mai.guess()
    log.info('数据更新完毕')
