import asyncio
import re
from re import Match
from textwrap import dedent
from typing import List

from nonebot import NoneBot
from PIL import Image

from hoshino.service import sucmd
from hoshino.typing import CommandSession, CQEvent, MessageSegment

from .. import SONGS_PER_PAGE, log, public_addr, sv
from ..libraries.image import image_to_base64, text_to_image
from ..libraries.maimaidx_api_data import maiApi
from ..libraries.maimaidx_error import ServerError
from ..libraries.maimaidx_music import alias, mai, update_local_alias
from ..libraries.maimaidx_music_info import draw_music_info

update_alias        = sucmd('updatealias', aliases=('更新别名库'))
alias_switch        = sucmd('aliasswitch', aliases=('全局关闭别名推送', '全局开启别名推送'))
alias_local_apply   = sv.on_prefix(['添加本地别名', '添加本地别称'])
alias_apply         = sv.on_prefix(['添加别名', '增加别名', '增添别名', '添加别称'])
alias_agree         = sv.on_prefix(['同意别名', '同意别称'])
alias_status        = sv.on_prefix(['当前投票', '当前别名投票', '当前别称投票'])
alias_song          = sv.on_rex(re.compile(r'^(id)?\s?(.+)\s?有什么别[名称]$', re.IGNORECASE))
alias_apply_status  = sv.scheduled_job('interval', minutes=5)


@update_alias
async def _(session: CommandSession):
    try:
        await mai.get_music_alias()
        log.info('手动更新别名库成功')
        await session.send('手动更新别名库成功')
    except:
        log.error('手动更新别名库失败')
        await session.send('手动更新别名库失败')
        

@alias_switch
async def _(session: CommandSession):
    if session.ctx.raw_message == '全局关闭别名推送':
        await alias.alias_global_change(False)
        await session.send('已全局关闭maimai别名推送')
    elif session.ctx.raw_message == '全局开启别名推送':
        await alias.alias_global_change(True)
        await session.send('已全局开启maimai别名推送')


@alias_local_apply
async def _(bot: NoneBot, ev: CQEvent):
    args: List[str] = ev.message.extract_plain_text().strip().split()
    id, alias_name = args
    if not mai.total_list.by_id(id):
        await bot.finish(ev, f'未找到ID为「{id}」的曲目')
    server_exist = await maiApi.get_songs_alias(id)
    if alias_name.lower() in server_exist['Alias']:
        await bot.finish(ev, f'该曲目的别名「{alias_name}」已存在别名服务器，不能重复添加别名，如果bot未生效，请联系BOT管理员使用指令「更新别名库」')
    local_exist = mai.total_alias_list.by_id(id)
    if local_exist and alias_name.lower() in local_exist[0].Alias:
        await bot.finish(ev, f'本地别名库已存在该别名', at_sender=True)
    issave = await update_local_alias(id, alias_name)
    if not issave:
        msg = '添加本地别名失败'
    else:
        msg = f'已成功为ID「{id}」添加别名「{alias_name}」到本地别名库'
    await bot.send(ev, msg, at_sender=True)


@alias_apply
async def _(bot: NoneBot, ev: CQEvent):
    try:
        args: List[str] = ev.message.extract_plain_text().strip().split()
        if len(args) != 2:
            await bot.finish(ev, '参数错误', at_sender=True)
        id, alias_name = args
        if not mai.total_list.by_id(id):
            await bot.finish(ev, f'未找到ID为 [{id}] 的曲目')
        isexist = await maiApi.get_songs_alias(id)
        if alias_name in isexist['Alias']:
            await bot.finish(ev, f'该曲目的别名 <{alias_name}> 已存在，不能重复添加别名，如果bot未生效，请联系BOT管理员使用指令 <更新别名库>')
        status = await maiApi.post_alias(id, alias_name, ev.user_id)
        if isinstance(status, str):
            await bot.finish(ev, status, at_sender=True)
        msg = dedent(f'''\
            您已提交以下别名申请
            ID：{id}
            别名：{alias_name}
            {await draw_music_info(mai.total_list.by_id(id))}
            现在可用使用唯一标签<{status['Tag']}>来进行投票，例如：同意别名 {status['Tag']}
            浏览{public_addr}查看详情
            ''') + MessageSegment.image(image_to_base64(Image.open(await maiApi.download_music_pictrue(id))))
    except ServerError as e:
        log.error(e)
        msg = str(e)
    except ValueError as e:
        msg = str(e)
    await bot.send(ev, msg, at_sender=True)


@alias_agree
async def _(bot: NoneBot, ev: CQEvent):
    try:
        tag: str = ev.message.extract_plain_text().strip().upper()
        status = await maiApi.post_agree_user(tag, ev.user_id)
        await bot.send(ev, status, at_sender=True)
    except ValueError as e:
        await bot.send(ev, str(e), at_sender=True)


@sv.on_prefix(['当前投票', '当前别名投票', '当前别称投票'])
async def _(bot: NoneBot, ev: CQEvent):
    try:
        args: str = ev.message.extract_plain_text().strip()
        status = await maiApi.get_alias_status()
        if not status:
            await bot.finish(ev, '未查询到正在进行的别名投票', at_sender=True)
        page = max(min(int(args), len(status) // SONGS_PER_PAGE + 1), 1) if args else 1
        result = []
        for num, _s in enumerate(status):
            if (page - 1) * SONGS_PER_PAGE <= num < page * SONGS_PER_PAGE:
                result.append(dedent(f'''{_s['Tag']}：
                - ID：{_s['SongID']}
                - 别名：{_s['ApplyAlias']}
                - 票数：{_s['AgreeVotes']}/{_s['Votes']}'''))
        result.append(f'第{page}页，共{len(status) // SONGS_PER_PAGE + 1}页')
        msg = MessageSegment.image(image_to_base64(text_to_image('\n'.join(result))))
    except ServerError as e:
        log.error(str(e))
        msg = str(e)
    except ValueError as e:
        msg = str(e)
    await bot.send(ev, msg, at_sender=True)


@alias_song
async def _(bot: NoneBot, ev: CQEvent):
    match: Match[str] = ev['match']
    findid = bool(match.group(1))
    name = match.group(2)
    alias = None
    if findid and name.isdigit():
        alias_id = mai.total_alias_list.by_id(name)
        if not alias_id:
            await bot.finish(ev, '未找到此歌曲\n可以使用「添加别名」指令给该乐曲添加别名', at_sender=True)
        else:
            alias = alias_id
    else:
        alias = mai.total_alias_list.by_alias(name)
        if not alias:
            if name.isdigit():
                alias_id = mai.total_alias_list.by_id(name)
                if not alias_id:
                    await bot.finish(ev, '未找到此歌曲\n可以使用「添加别名」指令给该乐曲添加别名', at_sender=True)
                else:
                    alias = alias_id
            else:
                await bot.finish(ev, '未找到此歌曲\n可以使用「添加别名」指令给该乐曲添加别名', at_sender=True)
    if len(alias) != 1:
        msg = []
        for songs in alias:
            alias_list = '\n'.join(songs.Alias)
            msg.append(f'ID：{songs.SongID}\n{alias_list}')
        await bot.finish(ev, f'找到{len(alias)}个相同别名的曲目：\n' + '\n======\n'.join(msg), at_sender=True)
    
    if len(alias[0].Alias) == 1:
        await bot.finish(ev, '该曲目没有别名', at_sender=True)

    msg = f'该曲目有以下别名：\nID：{alias[0].SongID}\n'
    msg += '\n'.join(alias[0].Alias)
    await bot.send(ev, msg, at_sender=True)
    
    
@alias_apply_status
async def _():
    try:
        group = await sv.get_enable_groups()
        if (status := await maiApi.get_alias_status()) and alias.config['global']:
            msg = ['检测到新的别名申请']
            for _s in status:
                if _s['IsNew'] and (usernum := _s['AgreeVotes']) < (votes := _s['Votes']):
                    song_id = str(_s['SongID'])
                    alias_name = _s['ApplyAlias']
                    music = mai.total_list.by_id(song_id)
                    msg.append(f'{_s["Tag"]}：\nID：{song_id}\n标题：{music.title}\n别名：{alias_name}\n票数：{usernum}/{votes}')
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
        if end := await maiApi.get_alias_end():
            if alias.config['global']:
                msg2 = ['以下是已成功添加别名的曲目']
                for _e in end:
                    song_id = str(_e['SongID'])
                    alias_name = _e['ApplyAlias']
                    music = mai.total_list.by_id(song_id)
                    msg2.append(f'ID：{song_id}\n标题：{music.title}\n别名：{alias_name}')
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