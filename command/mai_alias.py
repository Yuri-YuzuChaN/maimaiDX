import asyncio
import re
import traceback
from re import Match
from textwrap import dedent
from typing import List

from nonebot import NoneBot

from hoshino.service import priv
from hoshino.typing import CQEvent, MessageSegment

from .. import SONGS_PER_PAGE, log, public_addr, sv
from ..libraries.image import image_to_base64, text_to_image
from ..libraries.maimaidx_api_data import maiApi
from ..libraries.maimaidx_error import AliasesNotFoundError, ServerError
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
alias_apply_status  = sv.scheduled_job('interval', minutes=5)


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
    if ev.raw_message == '全局关闭别名推送':
        await alias.alias_global_change(False)
        await bot.send(ev, '已全局关闭maimai别名推送')
    elif ev.raw_message == '全局开启别名推送':
        await alias.alias_global_change(True)
        await bot.send(ev, '已全局开启maimai别名推送')


@alias_local_apply
async def _(bot: NoneBot, ev: CQEvent):
    args: List[str] = ev.message.extract_plain_text().strip().split()
    if len(args) != 2:
        await alias_local_apply.finish(ev, '参数错误', at_sender=True)
    song_id, alias_name = args
    if not mai.total_list.by_id(song_id):
        await bot.finish(ev, f'未找到ID为「{song_id}」的曲目', at_sender=True)
    try:
        server_exist = await maiApi.get_songs_alias(song_id)
        if alias_name.lower() in server_exist.Alias:
            await bot.send(ev, f'该曲目的别名「{alias_name}」已存在别名服务器，不能重复添加别名', at_sender=True)
            await mai.get_music_alias()
            await bot.finish(ev, f'别名库更新完成', at_sender=True)
    except AliasesNotFoundError:
        pass
    
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
        if len(args) != 2:
            await bot.finish(ev, '参数错误', at_sender=True)
        song_id, alias_name = args
        if not (music := mai.total_list.by_id(song_id)):
            await bot.finish(ev, f'未找到ID为「{song_id}」的曲目')
        try:
            isexist = await maiApi.get_songs_alias(song_id)
            if alias_name.lower() in isexist.Alias:
                await bot.send(
                    ev, 
                    f'该曲目的别名「{alias_name}」已存在别名服务器，不能重复添加别名，正在进行更新别名库', 
                    at_sender=True
                )
                await mai.get_music_alias()
                await bot.finish(ev, f'别名库更新完成', at_sender=True)
        except AliasesNotFoundError:
            pass
            
        status = await maiApi.post_alias(song_id, alias_name, ev.user_id)
        msg = dedent(f'''\
            您已提交以下别名申请
            ID：{song_id}
            别名：{alias_name}
            现在可用使用唯一标签「{status.Tag}」来进行投票，例如：同意别名 {status.Tag}
            浏览 {public_addr} 查看详情
            {await draw_music_info(music)}
        ''')
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
                r = f'{_s.Tag}：\n- ID：{_s.SongID}\n- 别名：{apply_alias}\n- 票数：{_s.AgreeVotes}/{_s.Votes}'
                result.append(r)
        result.append(f'第{page}页，共{len(status) // SONGS_PER_PAGE + 1}页')
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
            await bot.finish(ev, '未找到此歌曲\n可以使用「添加别名」指令给该乐曲添加别名', at_sender=True)
        else:
            aliases = alias_id
    else:
        aliases = mai.total_alias_list.by_alias(name)
        if not aliases:
            if name.isdigit():
                alias_id = mai.total_alias_list.by_id(name)
                if not alias_id:
                    await bot.finish(ev, '未找到此歌曲\n可以使用「添加别名」指令给该乐曲添加别名', at_sender=True)
                else:
                    aliases = alias_id
            else:
                await bot.finish(ev, '未找到此歌曲\n可以使用「添加别名」指令给该乐曲添加别名', at_sender=True)
    if len(aliases) != 1:
        msg = []
        for songs in aliases:
            alias_list = '\n'.join(songs.Alias)
            msg.append(f'ID：{songs.SongID}\n{alias_list}')
        await bot.finish(ev, f'找到{len(aliases)}个相同别名的曲目：\n' + '\n======\n'.join(msg), at_sender=True)
    
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
    
@alias_apply_status
async def _():
    try:
        group = await sv.get_enable_groups()
        status = await maiApi.get_alias_status()
        if not alias.push.global_switch:
            await mai.get_music_alias()
            return
        if status:
            msg = ['检测到新的别名申请']
            msg2 = ['以下是已成功添加别名的曲目']
            for _s in status:
                if _s.IsNew and (usernum := _s.AgreeVotes) < (votes := _s.Votes):
                    song_id = str(_s.SongID)
                    alias_name = _s.ApplyAlias
                    music = mai.total_list.by_id(song_id)
                    msg.append(f'{_s.Tag}：\nID：{song_id}\n标题：{music.title}\n别名：{alias_name}\n票数：{usernum}/{votes}')
                elif _s.IsEnd:
                    song_id = str(_s.SongID)
                    alias_name = _s.ApplyAlias
                    music = mai.total_list.by_id(song_id)
                    msg2.append(f'ID：{song_id}\n标题：{music.title}\n别名：{alias_name}')

            if len(msg) != 1 and len(msg2) != 1:
                for gid in group.keys():
                    if gid in alias.push.disable:
                        continue
                    try:
                        if len(msg) != 1: 
                            await sv.bot.send_group_msg(group_id=gid, message='\n======\n'.join(msg) + f'\n浏览{public_addr}查看详情')
                            await asyncio.sleep(5)
                        if len(msg2) != 1:
                            await sv.bot.send_group_msg(group_id=gid, message='\n======\n'.join(msg2))
                            await asyncio.sleep(5)
                    except: 
                        continue
        await mai.get_music_alias()
    except (ServerError, ValueError) as e:
        log.error(str(e))