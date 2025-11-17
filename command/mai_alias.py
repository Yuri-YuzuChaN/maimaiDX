import asyncio
import json
import re
import traceback
from re import Match
from textwrap import dedent
from typing import List

import aiohttp
from nonebot import NoneBot, get_bot

from hoshino.service import priv
from hoshino.typing import CQEvent, MessageSegment

from .. import SONGS_PER_PAGE, UUID, log, public_addr, sv
from ..libraries.image import image_to_base64, text_to_image
from ..libraries.maimaidx_api_data import maiApi
from ..libraries.maimaidx_error import ServerError
from ..libraries.maimaidx_model import Alias, PushAliasStatus
from ..libraries.maimaidx_music import alias, mai, update_local_alias
from ..libraries.maimaidx_music_info import draw_music_info

update_alias        = sv.on_fullmatch('更新别名库')
alias_switch_on     = sv.on_fullmatch('全局开启别名推送')
alias_switch_off    = sv.on_fullmatch('全局关闭别名推送')
alias_local_apply   = sv.on_prefix(['添加本地别名', '添加本地别称'])
alias_apply         = sv.on_prefix(['添加别名', '增加别名', '增添别名', '添加别称'])
alias_agree         = sv.on_prefix(['同意别名', '同意别称'])
alias_status        = sv.on_prefix(['当前投票', '当前别名投票', '当前别称投票'])
alias_switch        = sv.on_suffix(['别名推送', '别称推送'])
alias_song          = sv.on_rex(re.compile(r'^(id)?\s?(.+)\s?有什么别[名称]$', re.IGNORECASE))


@update_alias
async def _(bot: NoneBot, ev: CQEvent):
    if not priv.check_priv(ev, priv.SUPERUSER):
        return
    try:
        await mai.get_music_alias()
        log.info('手动更新别名库成功')
        await bot.send(ev, '手动更新别名库成功')
    except:
        log.error('手动更新别名库失败')
        await bot.send(ev, '手动更新别名库失败')
        

@alias_switch_on
@alias_switch_off
async def _(bot: NoneBot, ev: CQEvent):
    if not priv.check_priv(ev, priv.SUPERUSER):
        return
    
    await bot.get_group_list()
    group = await bot.get_group_list()
    group_id = [g['group_id'] for g in group]
    if ev.raw_message == '全局关闭别名推送':
        await alias.alias_global_change(False, group_id)
        await bot.send(ev, '已全局关闭maimai别名推送')
    elif ev.raw_message == '全局开启别名推送':
        await alias.alias_global_change(True, group_id)
        await bot.send(ev, '已全局开启maimai别名推送')


@alias_local_apply
async def _(bot: NoneBot, ev: CQEvent):
    args: List[str] = ev.message.extract_plain_text().strip().split()
    if len(args) != 2:
        await alias_local_apply.finish(ev, '参数错误', at_sender=True)
    song_id, alias_name = args
    if not mai.total_list.by_id(song_id):
        await bot.finish(ev, f'未找到ID为「{song_id}」的曲目', at_sender=True)
    
    server_exist = await maiApi.get_songs_alias(song_id)
    if isinstance(server_exist, Alias) and alias_name.lower() in server_exist.Alias:
        await bot.finish(
            ev,
            f'该曲目的别名「{alias_name}」已存在别名服务器', 
            at_sender=True
        )
    
    local_exist = mai.total_alias_list.by_id(song_id)
    if local_exist and alias_name.lower() in local_exist[0].Alias:
        await bot.finish(ev, f'本地别名库已存在该别名', at_sender=True)
    
    issave = await update_local_alias(song_id, alias_name)
    if not issave:
        msg = '添加本地别名失败'
    else:
        msg = f'已成功为ID「{song_id}」添加别名「{alias_name}」到本地别名库'
    await bot.send(ev, msg, at_sender=True)


@alias_apply
async def _(bot: NoneBot, ev: CQEvent):
    try:
        args: List[str] = ev.message.extract_plain_text().strip().split()
        if len(args) < 2:
            await bot.finish(ev, '参数错误', at_sender=True)
        song_id = args[0]
        if not song_id.isdigit():
            await bot.finish(ev, f'请输入正确的ID', at_sender=True)
        alias_name = ' '.join(args[1:])
        if not mai.total_list.by_id(song_id):
            await bot.finish(ev, f'未找到ID为「{song_id}」的曲目', at_sender=True)
        
        isexist = await maiApi.get_songs_alias(song_id)
        if isinstance(isexist, Alias) and alias_name.lower() in isexist.Alias:
            await bot.finish(
                ev, 
                f'该曲目的别名「{alias_name}」已存在别名服务器', 
                at_sender=True
            )
            
        msg = await maiApi.post_alias(song_id, alias_name, ev.user_id, ev.group_id)
    except (ServerError, ValueError) as e:
        log.error(traceback.format_exc())
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


@alias_status
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
                apply_alias = _s.ApplyAlias
                if len(_s.ApplyAlias) > 15:
                    apply_alias = _s.ApplyAlias[:15] + '...'
                result.append(
                    dedent(f'''\
                        - {_s.Tag}：
                        - ID：{_s.SongID}
                        - 别名：{apply_alias}
                        - 票数：{_s.AgreeVotes}/{_s.Votes}
                    ''')
                )
        result.append(f'第「{page}」页，共「{len(status) // SONGS_PER_PAGE + 1}」页')
        msg = MessageSegment.image(image_to_base64(text_to_image('\n'.join(result))))
    except (ServerError, ValueError) as e:
        log.error(traceback.format_exc())
        msg = str(e)
    await bot.send(ev, msg, at_sender=True)


@alias_song
async def _(bot: NoneBot, ev: CQEvent):
    match: Match[str] = ev['match']
    findid = bool(match.group(1))
    name = match.group(2)
    aliases = None
    if findid and name.isdigit():
        alias_id = mai.total_alias_list.by_id(name)
        if not alias_id:
            await bot.finish(
                ev, 
                '未找到此歌曲\n可以使用「添加别名」指令给该乐曲添加别名', 
                at_sender=True
            )
        else:
            aliases = alias_id
    else:
        aliases = mai.total_alias_list.by_alias(name)
        if not aliases:
            if name.isdigit():
                alias_id = mai.total_alias_list.by_id(name)
                if not alias_id:
                    await bot.finish(
                        ev, 
                        '未找到此歌曲\n可以使用「添加别名」指令给该乐曲添加别名', 
                        at_sender=True
                    )
                else:
                    aliases = alias_id
            else:
                await bot.finish(
                    ev, 
                    '未找到此歌曲\n可以使用「添加别名」指令给该乐曲添加别名', 
                    at_sender=True
                )
    if len(aliases) != 1:
        msg = []
        for songs in aliases:
            alias_list = '\n'.join(songs.Alias)
            msg.append(f'ID：{songs.SongID}\n{alias_list}')
        await bot.finish(
            ev, 
            f'找到{len(aliases)}个相同别名的曲目：\n' + '\n======\n'.join(msg), 
            at_sender=True
        )
    
    if len(aliases[0].Alias) == 1:
        await bot.finish(ev, '该曲目没有别名', at_sender=True)

    msg = f'该曲目有以下别名：\nID：{aliases[0].SongID}\n'
    msg += '\n'.join(aliases[0].Alias)
    await bot.send(ev, msg, at_sender=True)


@alias_switch
async def _(bot: NoneBot, ev: CQEvent):
    args = ev.message.extract_plain_text().strip().lower()
    if args == '开启':
        msg = await alias.on(ev.group_id)
    elif args == '关闭':
        msg = await alias.off(ev.group_id)
    else:
        raise ValueError('matcher type error')
    
    await bot.send(ev, msg)


async def push_alias(push: PushAliasStatus):
    bot = get_bot()
    song_id = str(push.Status.SongID)
    alias_name = push.Status.ApplyAlias
    music = mai.total_list.by_id(song_id)
    
    if push.Type == 'Approved':
        message = MessageSegment.at(push.Status.ApplyUID) + '\n' + dedent(f'''\
            您申请的别名已通过审核
            =================
            {push.Status.Tag}：
            ID：{song_id}
            标题：{music.title}
            别名：{alias_name}
            =================
            请使用指令「同意别名 {push.Status.Tag}」进行投票
        ''').strip() + await draw_music_info(music)
        await bot.send_group_msg(group_id=push.Status.GroupID, message=message)
        return
    if push.Type == 'Reject':
        message = MessageSegment.at(push.Status.ApplyUID) + '\n' + dedent(f'''\
            您申请的别名被拒绝
            =================
            ID：{song_id}
            标题：{music.title}
            别名：{alias_name}
        ''').strip() + await draw_music_info(music)
        await bot.send_group_msg(group_id=push.Status.GroupID, message=message)
        return
    
    if not maiApi.config.maimaidxaliaspush:
        await mai.get_music_alias()
        return
    group_list = await bot.get_group_list()
    group_ids = list({g['group_id'] for g in group_list})
    message = ''
    if push.Type == 'Apply':
        message = dedent(f'''\
            检测到新的别名申请
            =================
            {push.Status.Tag}：
            ID：{song_id}
            标题：{music.title}
            别名：{alias_name}
            浏览{public_addr}查看详情
        ''').strip() + await draw_music_info(music)
    if push.Type == 'End':
        message = dedent(f'''\
            检测到新增别名
            =================
            ID：{song_id}
            标题：{music.title}
            别名：{alias_name}
        ''').strip() + await draw_music_info(music)
    
    
    for gid in group_ids:
        if gid in alias.push.disable:
            continue
        try:
            await bot.send_group_msg(group_id=gid, message=message)
            await asyncio.sleep(5)
        except:
            continue


async def ws_alias_server():
    log.info('正在连接别名推送服务器')
    if maiApi.config.maimaidxaliasproxy:
        wsapi = 'proxy.yuzuchan.site/maimaidxaliases'
    else:
        wsapi = 'www.yuzuchan.moe/api/maimaidx'
    while True:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.ws_connect(f'wss://{wsapi}/ws/{UUID}') as ws:
                    log.info('别名推送服务器连接成功')
                    while True:
                        data = await ws.receive_str()
                        if data == 'Hello':
                            log.info('别名推送服务器正常运行')
                        try:
                            newdata = json.loads(data)
                            status = PushAliasStatus.model_validate(newdata)
                            await push_alias(status)
                        except:
                            continue
        except (aiohttp.WSServerHandshakeError, aiohttp.WebSocketError) as e:
            log.warning(f'连接断开或异常: {e}，将在 60 秒后重连')
            await asyncio.sleep(60)
            continue
        except Exception as e:
            log.error(f'别名推送服务器连接失败: {e}，将在 60 秒后重试')
            await asyncio.sleep(60)
            continue