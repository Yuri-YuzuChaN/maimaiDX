import asyncio
import json
from textwrap import dedent

import httpx
from httpx_ws import WebSocketDisconnect, aconnect_ws
from nonebot import get_bot, NoneBot
from hoshino.typing import Message, MessageSegment

from ..config import log, maiconfig
from ..constants import UUID, VOTE_URL
from ..core.clients.yuzuchan.models import PushAliasStatus
from ..core.handler import draw_chart_info
from ..core.service import alias, mai


def forward_msg(info: list[Message], self_id: int) -> list:
    forward_msg_list = []
    for msg in info:
        data = {
            "type": "node",
            "data": {"name": "Bot", "uin": str(self_id), "content": msg},
        }
        forward_msg_list.append(data)
    return forward_msg_list


async def push_alias(push: PushAliasStatus):
    bot: NoneBot = get_bot()
    if push.type == "Approved":
        status = push.status[0]
        message = (
            MessageSegment.at(status.apply_uid)
            + "\n"
            + dedent(f"""\
            您申请的别名已通过审核
            =================
            {status.tag}：
            ID：{status.song_id}
            标题：{status.name}
            别名：{status.apply_alias}
            =================
            请使用指令「同意别名 {status.tag}」进行投票
        """).strip()
            + await draw_chart_info(mai.total_list.by_id(status.song_id))
        )
        await bot.send_group_msg(group_id=status.group_id, message=message)
        return
    if push.type == "Reject":
        status = push.status[0]
        message = (
            MessageSegment.at(status.apply_uid)
            + "\n"
            + dedent(f"""\
            您申请的别名被拒绝
            =================
            ID：{status.song_id}
            标题：{status.name}
            别名：{status.apply_alias}
        """).strip()
            + await draw_chart_info(mai.total_list.by_id(status.song_id))
        )
        await bot.send_group_msg(group_id=status.group_id, message=message)
        return

    if not maiconfig.maimaidx_alias_push:
        await mai.get_music_alias()
        return
    group_list = await bot.get_group_list()
    group_ids: set[int] = set(list({g["group_id"] for g in group_list}))
    message = []
    for _s in push.status:
        song_id = _s.song_id
        alias_name = _s.apply_alias
        song = mai.total_list.by_id(song_id)
        if song is None:
            continue
        if push.type == "Apply":
            message.append(
                dedent(f"""\
                检测到新的别名申请
                =================
                {_s.tag}：
                ID：{song_id}
                标题：{song.song_name}
                别名：{alias_name}
                浏览{VOTE_URL}查看详情
            """).strip()
                + await draw_chart_info(song)
            )
        if push.type == "End":
            message.append(
                dedent(f"""\
                检测到新增别名
                =================
                ID：{song_id}
                标题：{song.song_name}
                别名：{alias_name}
            """).strip()
                + await draw_chart_info(song)
            )
    forward = forward_msg(message, bot.self_id)
    for gid in group_ids:
        if gid in alias.push.disable:
            continue
        try:
            await bot.send_group_forward_msg(group_id=gid, message=forward)
            await asyncio.sleep(5)
        except Exception:
            continue


async def ws_alias_server():
    log.info("正在连接别名推送服务器")
    if maiconfig.maimaidx_alias_proxy:
        wsapi = "www.yuzuchan.cn/api/v2/aliases"
    else:
        wsapi = "www.yuzuchan.moe/api/v2/aliases"
    while True:
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(60)) as session:
                async with aconnect_ws(f"wss://{wsapi}/ws/{UUID}", session) as ws:
                    log.success("别名推送服务器连接成功")
                    while True:
                        data = await ws.receive_text()
                        if data == "Hello":
                            log.info("别名推送服务器正常运行")
                            continue
                        try:
                            newdata = json.loads(data)
                            status = PushAliasStatus.model_validate(newdata)
                            await push_alias(status)
                        except Exception as e:
                            log.error(f"处理别名推送失败: {e}")
                            continue
        except (WebSocketDisconnect, httpx.LocalProtocolError) as e:
            log.warning(f"连接断开或异常: {e}，将在 60 秒后重连")
            await asyncio.sleep(60)
            continue
        except Exception as e:
            log.error(f"别名推送服务器连接失败: {e}，将在 60 秒后重试")
            await asyncio.sleep(60)
            continue
