import re
import traceback
from re import Match
from textwrap import dedent

from nonebot import NoneBot

from hoshino.service import priv
from hoshino.typing import CQEvent, MessageSegment

from ..config import log, sv
from ..constants import SONGS_PER_PAGE
from ..core.clients.exceptions import ServerError
from ..core.clients.yuzuchan.client import YuzuChaNAPI
from ..core.clients.yuzuchan.models import Alias
from ..core.image.tools import image_to_base64, text_to_image
from ..core.service import alias, mai, update_local_alias

update_alias = sv.on_fullmatch("更新别名库")
alias_local_apply = sv.on_prefix(["添加本地别名", "添加本地别称"])
alias_apply = sv.on_prefix(["添加别名", "增加别名", "增添别名", "添加别称"])
alias_agree = sv.on_prefix(["同意别名", "同意别称"])
alias_status = sv.on_prefix(["当前投票", "当前别名投票", "当前别称投票"])
alias_switch = sv.on_suffix(["别名推送", "别称推送"])
alias_global_switch = sv.on_rex(r"^全局(开启|关闭)别名推送$")
alias_song = sv.on_rex(
    re.compile(r"^(id(?=[\s0-9]))?\s?(.+)\s?有什么别[名称]$", re.IGNORECASE)
)


@update_alias
async def _(bot: NoneBot, ev: CQEvent):
    if not priv.check_priv(ev, priv.SUPERUSER):
        return
    try:
        await mai.get_music_alias()
        log.info("手动更新别名库成功")
        await bot.send(ev, "手动更新别名库成功")
    except Exception:
        log.error("手动更新别名库失败")
        await bot.send(ev, "手动更新别名库失败")


@alias_global_switch
async def _(bot: NoneBot, ev: CQEvent):
    if not priv.check_priv(ev, priv.SUPERUSER):
        return
    match: Match[str] = ev["match"]
    group = await bot.get_group_list()
    group_id = [g["group_id"] for g in group]
    if match.group(1) == "开启":
        await alias.alias_global_change(True, group_id)
        await bot.send(ev, "已全局开启maimai别名推送")
    elif match.group(1) == "关闭":
        await alias.alias_global_change(False, group_id)
        await bot.send(ev, "已全局关闭maimai别名推送")
    else:
        return


@alias_local_apply
async def _(bot: NoneBot, ev: CQEvent):
    args: list[str] = ev.message.extract_plain_text().strip().split()
    if len(args) != 2:
        await bot.finish(ev, "参数错误", at_sender=True)
    song_id, alias_name = args
    if song_id.isdigit():
        song_id = int(song_id)
    else:
        await bot.finish(ev, "请输入正确的ID", at_sender=True)
    if not mai.total_list.by_id(song_id):
        await bot.finish(ev, f"未找到ID为「{song_id}」的曲目", at_sender=True)

    api = YuzuChaNAPI()
    server_exist = await api.get_aliases(song_id=song_id)
    if isinstance(server_exist, Alias) and alias_name.lower() in server_exist.alias:
        await bot.finish(
            ev, f"该曲目的别名「{alias_name}」已存在别名服务器", at_sender=True
        )

    local_exist = mai.total_alias_list.by_id(song_id)
    if local_exist and alias_name.lower() in local_exist[0].alias:
        await bot.finish(ev, "本地别名库已存在该别名", at_sender=True)

    issave = await update_local_alias(song_id, alias_name)
    if not issave:
        msg = "添加本地别名失败"
    else:
        msg = f"已成功为ID「{song_id}」添加别名「{alias_name}」到本地别名库"
    await bot.send(ev, msg, at_sender=True)


@alias_apply
async def _(bot: NoneBot, ev: CQEvent):
    try:
        args: list[str] = ev.message.extract_plain_text().strip().split()
        if len(args) < 2:
            await bot.finish(ev, "参数错误", at_sender=True)
        song_id = args[0]
        if not song_id.isdigit():
            await bot.finish(ev, "请输入正确的ID", at_sender=True)
        alias_name = " ".join(args[1:])
        if not mai.total_list.by_id(int(song_id)):
            await bot.finish(ev, f"未找到ID为「{song_id}」的曲目", at_sender=True)

        api = YuzuChaNAPI()
        isexist = await api.get_aliases(song_id=song_id)
        if isinstance(isexist, Alias) and alias_name.lower() in isexist.alias:
            await bot.finish(
                ev, f"该曲目的别名「{alias_name}」已存在别名服务器", at_sender=True
            )

        msg = (
            await api.post_alias(song_id, alias_name, ev.user_id, ev.group_id)
        ).message
    except Exception as e:
        log.error(traceback.format_exc())
        msg = str(e)
    await bot.send(ev, msg, at_sender=True)


@alias_agree
async def _(bot: NoneBot, ev: CQEvent):
    try:
        tag: str = ev.message.extract_plain_text().strip().upper()
        api = YuzuChaNAPI()
        status = await api.post_agree_user(tag, ev.user_id)
        msg = status.message
    except Exception as e:
        log.error(traceback.format_exc())
        msg = str(e)
    await bot.send(ev, msg, at_sender=True)


@alias_status
async def _(bot: NoneBot, ev: CQEvent):
    try:
        args: str = ev.message.extract_plain_text().strip()
        api = YuzuChaNAPI()
        status = await api.get_status()
        if not status:
            await bot.finish(ev, "未查询到正在进行的别名投票", at_sender=True)

        total_pages = (len(status) + SONGS_PER_PAGE - 1) // SONGS_PER_PAGE
        page = max(min(int(args), total_pages), 1) if args.isdigit() else 1
        result = []
        for num, _s in enumerate(status):
            if (page - 1) * SONGS_PER_PAGE <= num < page * SONGS_PER_PAGE:
                apply_alias = _s.apply_alias
                if len(_s.apply_alias) > 15:
                    apply_alias = _s.apply_alias[:15] + "..."
                result.append(
                    dedent(f"""\
                        - {_s.tag}：
                        - ID：{_s.song_id}
                        - 别名：{apply_alias}
                        - 票数：{_s.agree_votes}/{_s.votes}
                    """)
                )
        result.append(f"第「{page}」页，共「{total_pages}」页")
        msg = MessageSegment.image(image_to_base64(text_to_image("\n".join(result))))
    except (ServerError, ValueError) as e:
        log.error(traceback.format_exc())
        msg = str(e)
    await bot.send(ev, msg, at_sender=True)


@alias_song
async def _(bot: NoneBot, ev: CQEvent):
    match: Match[str] = ev["match"]
    findid = bool(match.group(1))
    name = match.group(2).lower()
    aliases = None
    if findid and name.isdigit():
        alias_id = mai.total_alias_list.by_id(int(name))
        if not alias_id:
            await bot.finish(
                ev,
                "未找到此歌曲\n可以使用「添加别名」指令给该乐曲添加别名",
                at_sender=True,
            )
        else:
            aliases = alias_id
    else:
        aliases = mai.total_alias_list.by_alias(name)
        if not aliases:
            if name.isdigit():
                alias_id = mai.total_alias_list.by_id(int(name))
                if not alias_id:
                    await bot.finish(
                        ev,
                        "未找到此歌曲\n可以使用「添加别名」指令给该乐曲添加别名",
                        at_sender=True,
                    )
                else:
                    aliases = alias_id
            else:
                await bot.finish(
                    ev,
                    "未找到此歌曲\n可以使用「添加别名」指令给该乐曲添加别名",
                    at_sender=True,
                )
    if len(aliases) != 1:
        msg = []
        for songs in aliases:
            alias_list = "\n".join(songs.alias)
            msg.append(f"ID：{songs.song_id}\n{alias_list}")
        await bot.finish(
            ev,
            f"找到{len(aliases)}个相同别名的曲目：\n" + "\n======\n".join(msg),
            at_sender=True,
        )

    real_aliases = [
        a for a in aliases[0].alias if a.lower() != aliases[0].song_name.lower()
    ]
    if not real_aliases:
        await bot.finish(ev, "该曲目没有别名", at_sender=True)

    msg = f"该曲目有以下别名：\nID：{aliases[0].song_id}\n"
    msg += "\n".join(real_aliases)
    await bot.send(ev, msg, at_sender=True)


@alias_switch
async def _(bot: NoneBot, ev: CQEvent):
    args = ev.message.extract_plain_text().strip().lower()
    if args == "开启":
        msg = await alias.on(ev.group_id)
    elif args == "关闭":
        msg = await alias.off(ev.group_id)
    else:
        return

    await bot.send(ev, msg, at_sender=True)
