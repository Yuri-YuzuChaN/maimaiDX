import random
import re
from re import Match
from textwrap import dedent

from nonebot import NoneBot
from PIL import Image

from hoshino.service import priv
from hoshino.typing import CQEvent, MessageSegment

from ..config import Root, lxnsconfig, maiconfig, sv
from ..constants import FORTUNE, LEVEL_LIST
from ..core.clients.divingfish.client import DivingFishAPI
from ..core.database.qq import update_user
from ..core.handler import (
    bind_lxns,
    draw_chart_info,
    draw_rating_ranking,
    draw_rise_score_list,
    get_mai_what,
)
from ..core.image.tools import image_to_base64, song_chart
from ..core.merge.models import ServiceName, Theme
from ..core.service import mai
from ..core.tool import qqhash
from .depend import GetOrCreateUser, GetUserAndAuthOrNone

CODE_PATTERN = re.compile(r"^[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}$")
AUTHORIZE_URL = (
    "https://maimai.lxns.net/oauth/authorize"
    "?response_type=code"
    f"&client_id={lxnsconfig.lx_client_id}"
    f"&redirect_uri={lxnsconfig.redirect_uri}"
    "&scope=read_player+read_user_profile+write_player"
)
AUTHORIZE_MSG = dedent(f"""
    请点击以下链接进行授权
    允许「{maiconfig.bot_name} BOT」访问您的落雪查分器数据
    =======================
    {AUTHORIZE_URL}
    =======================
    点击授权后您应收到该格式的
    授权码：「XXXX-XXXX-XXXX」
    请复制该授权码，并使用「授权码」指令粘贴到该窗口完成授权
    =======================
    请注意！！您必须在落雪查分器的
    「账号设置 -> 常规设置」中的
    「隐私设置」开启允许读取成绩，否
    则BOT将无法查询您的成绩
""").strip()
LXNS_ERROR = "BOT管理员尚未配置落雪查分器相关信息"


update_data = sv.on_fullmatch("更新maimai数据")
help = sv.on_fullmatch(["帮助maimaiDX", "帮助maimaidx"])
maimaidxrepo = sv.on_fullmatch(["项目地址maimaiDX", "项目地址maimaidx"])
bind = sv.on_fullmatch(["lxbind", "绑定落雪", "绑定lx"])
authcode = sv.on_prefix(["授权码", "code"])
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
    if lxnsconfig.lxns_dev_token is None and (
        lxnsconfig.lx_client_id is None or lxnsconfig.redirect_uri is None
    ):
        await bot.finish(ev, LXNS_ERROR + "，无法进行绑定授权。", at_sender=True)
    await bot.send(ev, AUTHORIZE_MSG, at_sender=True)


@authcode
async def _(bot: NoneBot, ev: CQEvent):
    user = await GetOrCreateUser(bot, ev)
    code = ev.message.extract_plain_text().strip()
    if not CODE_PATTERN.fullmatch(code):
        await bot.finish(ev, "授权码格式错误，请重新发送。", at_sender=True)
    result = await bind_lxns(user, code)
    await bot.send(ev, result, at_sender=True)


@source
async def _(bot: NoneBot, ev: CQEvent):
    user = await GetOrCreateUser(bot, ev)
    args = ev.message.extract_plain_text().strip()
    source_ = ServiceName.get_by_index(args)
    if source_ is None:
        await bot.finish(
            ev, f"未找到该数据源：\n{ServiceName.get_help()}", at_sender=True
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
    await bot.send(ev, f"数据源已切换为：「{source_.value}」", at_sender=True)


@theme
async def _(bot: NoneBot, ev: CQEvent):
    user = await GetOrCreateUser(bot, ev)
    args = ev.message.extract_plain_text().strip()
    theme_ = Theme.get_by_index(args)
    if theme_ is None:
        await bot.finish(ev, f"未找到该主题：\n{Theme.get_help()}", at_sender=True)

    await update_user(user.qqid, theme=theme_)
    await bot.send(ev, f"主题已切换为：「{theme_.value}」", at_sender=True)


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
