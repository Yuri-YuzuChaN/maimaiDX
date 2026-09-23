import asyncio
import json
from collections.abc import AsyncIterator
from textwrap import dedent

import httpx
from nonebot import NoneBot, get_bot

from hoshino.typing import MessageSegment

from ..config import log, maiconfig
from ..constants import VOTE_URL
from ..core.clients.yuzuchan.models import (
    PushAliasStatus,
    SSEMessage,
)
from ..core.handler import draw_chart_info
from ..core.service import alias, mai

SSE_RECONNECT_DELAY = 3.0
SSE_RECONNECT_DELAY_MAX = 60.0


async def iter_sse(lines: AsyncIterator[str]) -> AsyncIterator[SSEMessage]:
    """把 HTTP 响应行解析为 SSE 消息。"""
    event = "message"
    data: list[str] = []
    event_id: str | None = None
    retry: int | None = None

    async for line in lines:
        if not line:
            if data:
                yield SSEMessage(
                    event=event,
                    data="\n".join(data),
                    id=event_id,
                    retry=retry,
                )
            event = "message"
            data = []
            event_id = None
            retry = None
            continue
        if line.startswith(":"):
            continue

        field, separator, value = line.partition(":")
        if separator and value.startswith(" "):
            value = value[1:]
        if field == "event":
            event = value
        elif field == "data":
            data.append(value)
        elif field == "id" and "\0" not in value:
            event_id = value
        elif field == "retry" and value.isdecimal():
            retry = int(value)

    if data:
        yield SSEMessage(
            event=event,
            data="\n".join(data),
            id=event_id,
            retry=retry,
        )


async def push_alias(push: PushAliasStatus):
    bot: NoneBot = get_bot()

    if not maiconfig.maimaidx_alias_push:
        await mai.get_music_alias()
        return
    group_list = await bot.get_group_list()
    group_ids: set[int] = set({g["group_id"] for g in group_list})
    message = []
    for num, item in enumerate(push.status):
        song_id = item.song_id
        alias_name = item.apply_alias
        song = mai.total_list.by_id(song_id)
        if num == 0 and push.type == "Apply":
            message.append(
                "检测到新的别名申请，可使用同意别名指令进行投票，点击下方链接查看详情："
                f"「{VOTE_URL}」\n如果不需要接收推送消息，请使用「关闭别名推送」指令关闭推送"
            )
        if push.type == "Apply":
            message.append(
                dedent(f"""\
                {item.tag}：
                ID：{song_id}
                标题：{song.song_name}
                别名：{alias_name}
            """).strip()
                + await draw_chart_info(song)
            )
    if not message:
        return
    forward = [MessageSegment.node_custom(bot.self_id, "Bot", msg) for msg in message]
    for gid in group_ids:
        if gid in alias.push.disable:
            continue
        try:
            await bot.send_group_forward_msg(group_id=gid, message=forward)
            await asyncio.sleep(5)
        except Exception:
            continue


async def sse_alias_server():
    log.info("正在连接别名推送服务器")
    if maiconfig.maimaidx_alias_proxy:
        api = "https://www.yuzuchan.cn/api/v2/events"
    else:
        api = "https://www.yuzuchan.moe/api/v2/events"

    reconnect_delay = SSE_RECONNECT_DELAY
    last_event_id: str | None = None
    timeout = httpx.Timeout(connect=30, read=None, write=30, pool=30)
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as session:
        while True:
            try:
                headers = {"Accept": "text/event-stream"}
                if last_event_id is not None:
                    headers["Last-Event-ID"] = last_event_id
                async with session.stream(
                    "GET",
                    api,
                    headers=headers,
                ) as response:
                    response.raise_for_status()
                    content_type: str = response.headers.get("content-type", "")
                    if (
                        content_type.partition(";")[0].strip().lower()
                        != "text/event-stream"
                    ):
                        raise httpx.RemoteProtocolError(
                            f"服务器返回了非 SSE 响应: {content_type or 'unknown'}"
                        )

                    log.success("别名推送服务器连接成功")
                    async for message in iter_sse(response.aiter_lines()):
                        if message.id is not None:
                            last_event_id = message.id or None
                        if message.retry is not None:
                            reconnect_delay = min(
                                max(message.retry / 1000, 0.1),
                                SSE_RECONNECT_DELAY_MAX,
                            )
                        if message.event != "alias":
                            continue
                        try:
                            payload = json.loads(message.data)
                            if payload.get("type") != "Apply":
                                continue
                            push = PushAliasStatus.model_validate(payload)
                            await push_alias(push)
                        except ValueError as e:
                            log.warning(f"收到无效的别名推送事件: {e}")
                        except Exception:
                            log.exception("处理别名推送事件失败")

                log.warning(f"别名推送服务器已断开，将在 {reconnect_delay:g} 秒后重连")
            except httpx.HTTPError as e:
                log.warning(
                    f"别名推送服务器连接异常: {e}，将在 {reconnect_delay:g} 秒后重连"
                )
            except Exception:
                log.exception(
                    f"别名推送服务器连接失败，将在 {reconnect_delay:g} 秒后重试"
                )

            await asyncio.sleep(reconnect_delay)
