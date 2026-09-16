import random
import re
from re import Match

from httpx import HTTPError as HTTPXError
from nonebot import NoneBot
from PIL import Image
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError

from hoshino.service import priv
from hoshino.typing import CQEvent, MessageSegment

from ..config import Root, dfconfig, log, lxnsconfig, maiconfig, sv
from ..constants import FORTUNE, LEVEL_LIST
from ..core.clients.divingfish.client import DivingFishAPI
from ..core.clients.divingfish.exceptions import (
    DivingFishBindingMismatchError,
    DivingFishConfirmationCodeError,
)
from ..core.clients.divingfish.oauth import REVOKE_URL, binding_label
from ..core.clients.exceptions import HTTPError, UnknownError
from ..core.database.qq import User, update_user
from ..core.divingfish_oauth import extract_confirmation_code
from ..core.handler import (
    bind_divingfish,
    bind_lxns,
    complete_divingfish_binding,
    draw_chart_info,
    draw_rating_ranking,
    draw_rise_score_list,
    get_mai_what,
)
from ..core.image.tools import image_to_base64, song_chart
from ..core.lxns_oauth import (
    extract_authorization_code,
)
from ..core.merge.models import ServiceName, Theme
from ..core.pending_binding import PendingBindingStore
from ..core.service import mai
from ..core.tool import qqhash
from .depend import (
    GetOrCreateSender,
    GetOrCreateUser,
    GetUserAndAuthOrNone,
)
from .oauth_message import (
    BINDING_TEMPORARY_FAILED_MSG,
    DIVINGFISH_AUTHORIZE_MSG,
    DIVINGFISH_BIND_FAILED_MSG,
    DIVINGFISH_BIND_SUCCESS_MSG,
    DIVINGFISH_CODE_FAILED_MSG,
    DIVINGFISH_CODE_TEMPORARY_FAILED_MSG,
    DIVINGFISH_INVALID_CODE_MSG,
    DIVINGFISH_MISMATCH_MSG,
    DIVINGFISH_NO_SESSION_MSG,
    DIVINGFISH_OAUTH_ERROR,
    DIVINGFISH_SESSION_TTL,
    INVALID_CODE_MSG,
    LXNS_AUTHORIZE_MSG,
    LXNS_ERROR,
    OAUTH_FAILED_MSG,
)

CODE_PATTERN = re.compile(r"^[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}$")


pending_bindings = PendingBindingStore()


async def is_pending_authorization_code(
    event: CQEvent,
) -> bool:
    return pending_bindings.is_active(
        event.self_id, event.user_id, ServiceName.LXNS
    ) and bool(extract_authorization_code(event.get_plaintext()))


async def is_pending_confirmation_code(
    event: CQEvent,
) -> bool:
    """这条消息是不是「发起水鱼绑定的那个人」发回来的确认码

    两个条件缺一不可：这个 QQ 此刻确实在等水鱼的码（会话按
    `(self_id, user_id)` 记，别人发的落不到这条记录上），且整条消息
    就是一串确认码。剩下那一半核对在
    `handler.complete_divingfish_binding` 里向水鱼求证。
    """
    return pending_bindings.is_active(
        event.self_id, event.user_id, ServiceName.DIVINGFISH
    ) and bool(extract_confirmation_code(event.get_plaintext()))


async def complete_lxns_binding(user: User, code: str) -> tuple[str, bool]:
    try:
        result = await bind_lxns(user, code)
    except HTTPError as error:
        log.warning(f"落雪 OAuth 绑定失败：{type(error).__name__}")
        return OAUTH_FAILED_MSG, False
    except (HTTPXError, UnknownError, ValidationError, SQLAlchemyError) as error:
        log.warning(f"落雪 OAuth 绑定暂时失败：{type(error).__name__}")
        return BINDING_TEMPORARY_FAILED_MSG, False
    return result, result == "授权完成。"


async def complete_divingfish(qqid: int, code: str) -> tuple[str, bool]:
    try:
        await complete_divingfish_binding(qqid, code)
    except DivingFishBindingMismatchError:
        # 码有效，但兑出来的授权不是这个 QQ 的。多半是把别人转发来的码
        # 当成自己的用了——照实说清楚，别让他以为是自己操作错了
        log.warning("水鱼确认码与发起绑定的用户不一致")
        return DIVINGFISH_MISMATCH_MSG, False
    except DivingFishConfirmationCodeError:
        return DIVINGFISH_CODE_FAILED_MSG, False
    except (HTTPError, HTTPXError, UnknownError, ValidationError) as error:
        log.warning(f"水鱼绑定暂时失败：{type(error).__name__}")
        return DIVINGFISH_CODE_TEMPORARY_FAILED_MSG, False
    return DIVINGFISH_BIND_SUCCESS_MSG, True


update_data = sv.on_fullmatch("更新maimai数据")
help = sv.on_fullmatch(["帮助maimaiDX", "帮助maimaidx"])
maimaidxrepo = sv.on_fullmatch(["项目地址maimaiDX", "项目地址maimaidx"])
bind = sv.on_fullmatch(["lxbind", "绑定落雪", "绑定lx"])
dfbind = sv.on_fullmatch(["dfbind", "绑定水鱼", "绑定df"])
authcode = sv.on_prefix(["落雪授权码", "lxcode"])
df_authcode = sv.on_prefix(["水鱼授权码", "dfcode"])
source = sv.on_prefix("数据源")
theme = sv.on_prefix(["主题", "theme"])
portune = sv.on_prefix(["今日mai", "今日舞萌", "今日运势"])
mai_what = sv.on_rex(r".*mai.*什么(.+)?")
random_song = sv.on_rex(r"^[来随给]个((?:dx|sd|标准))?([绿黄红紫白]?)([0-9]+\+?)$")
rise_score = sv.on_rex(r"^我要在?([0-9]+\+?)?[上加\+]([0-9]+)?分\s?(.+)?")
rating_ranking = sv.on_prefix(["查看排名", "查看排行"])
my_rating_ranking = sv.on_fullmatch("我的排名")


@update_data
async def _(bot: NoneBot, ev: CQEvent):
    if not priv.check_priv(ev, priv.SUPERUSER):
        return
    await mai.get_music()
    await mai.get_music_alias()
    await mai.get_plate_json()
    await bot.send(ev, "maimai数据更新完成")


@help
async def _(bot: NoneBot, ev: CQEvent):
    await bot.send(
        ev,
        MessageSegment.image(image_to_base64(Image.open((Root / "maimaidxhelp.png")))),
        at_sender=True,
    )


@maimaidxrepo
async def _(bot: NoneBot, ev: CQEvent):
    await bot.send(
        ev,
        "项目地址：https://github.com/Yuri-YuzuChaN/maimaiDX\n求star，求宣传~",
        at_sender=True,
    )


@bind
async def _(bot: NoneBot, ev: CQEvent):
    user = await GetOrCreateSender(bot, ev)
    if not all(
        (
            lxnsconfig.lx_client_id,
            lxnsconfig.lx_client_secret,
            lxnsconfig.redirect_uri,
        )
    ):
        await bot.finish(ev, LXNS_ERROR + "，无法进行绑定授权。", at_sender=True)
    text = ev.message.extract_plain_text().strip()
    if not text:
        pending_bindings.start(ev.self_id, ev.user_id, ServiceName.LXNS)
        await bot.send(ev, LXNS_AUTHORIZE_MSG, at_sender=True)

    code = extract_authorization_code(text)
    if code is None:
        await bot.finish(ev, INVALID_CODE_MSG, at_sender=True)

    result, succeeded = await complete_lxns_binding(user, code)
    if succeeded:
        pending_bindings.discard(ev.self_id, ev.user_id)
    else:
        pending_bindings.start(ev.self_id, ev.user_id, ServiceName.LXNS)
    await bot.finish(ev, result, at_sender=True)


@authcode
async def _(bot: NoneBot, ev: CQEvent):
    user = await GetOrCreateUser(bot, ev)
    args = ev.message.extract_plain_text().strip()
    code = extract_authorization_code(args)
    if code is None or not pending_bindings.is_active(
        ev.self_id, ev.user_id, ServiceName.LXNS
    ):
        return
    result, succeeded = await complete_lxns_binding(user, code)
    if succeeded:
        pending_bindings.consume(ev.self_id, ev.user_id)
    await bot.send(ev, result, at_sender=True)


@dfbind
async def _(bot: NoneBot, ev: CQEvent):
    user = await GetOrCreateSender(bot, ev)
    if not dfconfig.oauth_enabled:
        await bot.finish(ev, DIVINGFISH_OAUTH_ERROR, at_sender=True)

    text = ev.message.extract_plain_text().strip()
    if text:
        if not pending_bindings.is_active(
            ev.self_id, ev.user_id, ServiceName.DIVINGFISH
        ):
            await bot.finish(ev, DIVINGFISH_NO_SESSION_MSG, at_sender=True)
        code = extract_confirmation_code(text)
        if code is None:
            await bot.finish(ev, DIVINGFISH_INVALID_CODE_MSG, at_sender=True)
        result, succeeded = await complete_divingfish(user.qqid, code)
        if succeeded:
            pending_bindings.consume(ev.self_id, ev.user_id)
        await bot.finish(ev, result, at_sender=True)

    try:
        authorization = await bind_divingfish(user.qqid)
    except (HTTPError, HTTPXError, UnknownError, ValidationError) as error:
        log.warning(f"水鱼授权发起失败：{type(error).__name__}")
        await bot.finish(ev, DIVINGFISH_BIND_FAILED_MSG, at_sender=True)

    pending_bindings.start(
        ev.self_id,
        ev.user_id,
        ServiceName.DIVINGFISH,
        ttl=DIVINGFISH_SESSION_TTL,
    )
    await bot.finish(
        ev,
        DIVINGFISH_AUTHORIZE_MSG.format(
            bot_name=maiconfig.bot_name,
            url=authorization.verification_uri_complete,
            label=binding_label(user.qqid),
            minutes=max(authorization.expires_in // 60, 1),
            revoke=dfconfig.divingfish_auth_url.rstrip("/") + REVOKE_URL,
        ),
        at_sender=True,
    )


@df_authcode
async def _(bot: NoneBot, ev: CQEvent):
    user = await GetOrCreateUser(bot, ev)
    args = ev.message.extract_plain_text().strip()
    code = extract_confirmation_code(args)
    if code is None or not pending_bindings.is_active(
        ev.self_id, ev.user_id, ServiceName.LXNS
    ):
        return
    result, succeeded = await complete_divingfish(user.qqid, code)
    if succeeded:
        pending_bindings.consume(ev.self_id, ev.user_id)
    await bot.send(ev, result, at_sender=True)


@source
async def _(bot: NoneBot, ev: CQEvent):
    user = await GetOrCreateUser(bot, ev)
    args = ev.message.extract_plain_text().strip()
    source_ = ServiceName.get_by_index(args)
    if source_ is None:
        await bot.finish(
            ev,
            f"未找到该数据源，请输入指定数字切换：\n{ServiceName.get_help()}",
            at_sender=True,
        )
    if (
        source_ == ServiceName.LXNS
        and lxnsconfig.lxns_dev_token is None
        and (lxnsconfig.lx_client_id is None or lxnsconfig.redirect_uri is None)
    ):
        await update_user(user.qqid, service=ServiceName.DIVINGFISH)
        await bot.finish(
            ev,
            LXNS_ERROR + "。为防止无法查询成绩，已强制将数据源切换为水鱼查分器。",
            at_sender=True,
        )

    await update_user(user.qqid, service=source_)
    await bot.send(ev, f"已切换数据源为：「{source_.value}」", at_sender=True)


@theme
async def _(bot: NoneBot, ev: CQEvent):
    user = await GetOrCreateUser(bot, ev)
    args = ev.message.extract_plain_text().strip()
    theme_ = Theme.get_by_index(args)
    if theme_ is None:
        await bot.finish(
            ev,
            f"未找到该主题，请输入指定数字切换：\n{Theme.get_help()}",
            at_sender=True,
        )

    await update_user(user.qqid, theme=theme_)
    await bot.send(ev, f"已切换主题为：「{theme_.value}」", at_sender=True)


@portune
async def _(bot: NoneBot, ev: CQEvent):
    user = await GetOrCreateUser(bot, ev)
    fortune_hash = qqhash(user.qqid)
    daily_random = random.Random(fortune_hash)
    rp = fortune_hash % 100
    h = fortune_hash
    wm_value = []
    for i in range(11):
        wm_value.append(h & 3)
        h >>= 2
    msg = f"\n今日人品值：{rp}\n"
    for i in range(11):
        if wm_value[i] == 3:
            msg += f"宜 {FORTUNE[i]}\n"
        elif wm_value[i] == 0:
            msg += f"忌 {FORTUNE[i]}\n"
    song = daily_random.choice(mai.total_list.root)
    ds = "/".join([str(d.level_value) for d in song.difficulties])
    msg += (
        f"{maiconfig.bot_name} Bot提醒您：打机时不要大力拍打或滑动哦\n今日推荐歌曲："
        f"ID.{song.song_id} - {song.song_name}"
        f"{MessageSegment.image(image_to_base64(Image.open(song_chart(song.song_id))))}"
        f"{ds}"
    )
    await bot.send(ev, msg, at_sender=True)


@mai_what
async def _(bot: NoneBot, ev: CQEvent):
    user = await GetUserAndAuthOrNone(bot, ev)
    match: Match[str] = ev["match"]
    song = mai.total_list.random()
    if (point := match.group(1)) and (
        "推分" in point or "上分" in point or "加分" in point
    ):
        _song = await get_mai_what(user)
        if _song is not None:
            song = _song
    await bot.send(ev, await draw_chart_info(song, user), at_sender=True)


@random_song
async def _(bot: NoneBot, ev: CQEvent):
    user = await GetUserAndAuthOrNone(bot, ev)
    match: Match[str] = ev["match"]
    if not match:
        await bot.finish(ev, "参数错误，请重新发送随机谱面", at_sender=True)
    diff = match.group(1)
    if diff == "dx":
        type_ = ["DX"]
    elif diff == "sd" or diff == "标准":
        type_ = ["SD"]
    else:
        type_ = ["SD", "DX"]
    level = match.group(3)
    color = match.group(2)
    songs = mai.total_list.filter(level=level, type=type_)
    if color:
        ci = "绿黄红紫白".index(color)
        songs = [
            s
            for s in songs
            if len(s.difficulties) > ci and s.difficulties[ci].level == level
        ]
    if len(songs) == 0:
        result = "没有这样的乐曲哦。"
    else:
        result = await draw_chart_info(random.choice(songs), user)
    await bot.send(ev, result, at_sender=True)


@rise_score
async def _(bot: NoneBot, ev: CQEvent):
    user = await GetOrCreateUser(bot, ev)
    match: Match[str] = ev["match"]
    if not match:
        rating = None
        score = None
    else:
        rating = match.group(1)
        score = match.group(2)
    if score is not None:
        score = int(score)

    if rating and rating not in LEVEL_LIST:
        await bot.finish(ev, "无此等级", at_sender=True)

    data = await draw_rise_score_list(user, rating, score)
    await bot.send(ev, data, at_sender=True)


@rating_ranking
async def _(bot: NoneBot, ev: CQEvent):
    name = ""
    page = 1
    args: str = ev.message.extract_plain_text().strip()
    if args.isdigit():
        page = int(args)
    else:
        name = args.lower()
    pic = await draw_rating_ranking(name, page)
    await bot.send(ev, pic, at_sender=True)


@my_rating_ranking
async def _(bot: NoneBot, ev: CQEvent):
    user = await GetOrCreateUser(bot, ev)
    api = DivingFishAPI(qqid=user.qqid)
    info = await api.query_user_b50()
    rank_data = await api.rating_ranking()
    for num, rank in enumerate(rank_data):
        if rank.username == info.username:
            result = f"您的Rating为「{rank.ra}」，排名第「{num + 1}」名"
            await bot.finish(ev, result, at_sender=True)
    await bot.finish(ev, "未在查分器排行榜中找到您的记录。", at_sender=True)
