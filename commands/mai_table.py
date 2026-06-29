import re
from re import Match

from nonebot import NoneBot
from PIL import Image

from hoshino import priv
from hoshino.typing import CQEvent, MessageSegment

from ..config import sv
from ..constants import COMBO_PLUS, LEVEL_LIST, PLATE_CN, RANK_PLUS, SYNC_PLUS
from ..core.handler import (
    draw_level_progress,
    draw_level_score_list,
    draw_plate_progress,
    draw_plate_table,
    draw_rating_table,
    draw_rating_table_text,
)
from ..core.image.tools import image_to_base64
from ..core.image.update_table import UpdateTable
from ..core.merge.models import Category
from ..resources import pic_dir
from .depend import GetUserAndAuth

RATING_PATTERN = r"^([0-9]+\+?)((s+|ap|fc|fs|fdx)\+?)?\s?完成表$"
TABLE_PATTERN = (
    r"^([真超檄橙暁晓桃櫻樱紫菫堇白雪輝辉舞霸熊華华爽煌星宙祭祝双宴镜彩])"
    r"([極极将舞神者]舞?){}表?\s?([0-9]+)?$"
)
LEVEL_PATTERN = r"^([0-9]+\+?)\s?((?:a+|b+|c|d|s+|ap|fc|fs|fdx)\+?)\s?([\u4e00-\u9fa5]+)?\s?进度\s?([0-9]+)?$"
LEVEL_LIST_PATTERN = r"^([0-9]+(?:\.[0-9]+)?\+?)\s?分数列表\s?([0-9]+)?$"
CATEGORY_ALIAS = {
    "已完成": Category.COMPLETED,
    "未完成": Category.UNFINISHED,
    "未开始": Category.NOTPLAYED,
    "未游玩": Category.NOTPLAYED,
}

PLATE_TABLE_RE = re.compile(TABLE_PATTERN.format("完成表"), re.IGNORECASE)
PLATE_PROGRESS_RE = re.compile(TABLE_PATTERN.format("进度"), re.IGNORECASE)


update_table = sv.on_fullmatch("更新定数表")
update_plate = sv.on_fullmatch("更新完成表")
rating_table = sv.on_rex(r"([0-9]+\+?)定数表")
rating_table_pfm = sv.on_rex(re.compile(RATING_PATTERN, re.IGNORECASE))
plate_table_condition = sv.on_fullmatch("牌子条件")
plate_table_pfm = sv.on_rex(PLATE_TABLE_RE)
plate_progress = sv.on_rex(PLATE_PROGRESS_RE)
level_progress = sv.on_rex(re.compile(LEVEL_PATTERN, re.IGNORECASE))
level_score_list = sv.on_rex(LEVEL_LIST_PATTERN)


@update_table
async def _(bot: NoneBot, ev: CQEvent):
    if not priv.check_priv(ev, priv.SUPERUSER):
        return
    await bot.send(ev, "正在更新定数表...")
    update = UpdateTable()
    await update.update_rating_table()
    await update.update_level_15_rating_table()
    await bot.send(ev, "定数表更新完成。")


@update_plate
async def _(bot: NoneBot, ev: CQEvent):
    if not priv.check_priv(ev, priv.SUPERUSER):
        return
    update = UpdateTable()
    await update.update_plate_table()
    await update.update_wu_plate_table()
    await bot.send(ev, "完成表更新完成")


@rating_table
async def _(bot: NoneBot, ev: CQEvent):
    match: Match[str] = ev["match"]
    rating = match.group(1).strip()
    if rating in LEVEL_LIST[:6]:
        result = "只支持查询lv7-15的定数表。"
    elif rating in LEVEL_LIST[6:]:
        result = draw_rating_table_text(rating)
    else:
        result = "无法识别的定数。"
    await bot.send(ev, result, at_sender=True)


@rating_table_pfm
async def _(bot: NoneBot, ev: CQEvent):
    user = await GetUserAndAuth(bot, ev)
    match: Match[str] = ev["match"]
    ra = match.group(1)
    plan = match.group(2)
    if ra in LEVEL_LIST[:6]:
        await bot.finish(ev, "只支持查询lv7-15的完成表。", at_sender=True)
    elif ra in LEVEL_LIST[6:]:
        if plan and plan.lower() not in COMBO_PLUS:
            await bot.finish(
                ev,
                "完成表目前仅支持「fc」「ap」计划，例如「13fc完成表」「13ap完成表」。",
                at_sender=True,
            )
        pic = await draw_rating_table(
            user, ra, True if plan and plan.lower() in COMBO_PLUS else False
        )
        await bot.send(ev, pic, at_sender=True)
    else:
        await bot.send(ev, "无法识别的表格。", at_sender=True)


@plate_table_condition
async def _(bot: NoneBot, ev: CQEvent):
    await bot.send(
        ev,
        MessageSegment.image(
            image_to_base64(Image.open(pic_dir / "table_condition.jpg"))
        ),
    )


@plate_table_pfm
@plate_progress
async def _(bot: NoneBot, ev: CQEvent):
    user = await GetUserAndAuth(bot, ev)
    match: Match[str] = ev["match"]
    ver = match.group(1)
    plan = match.group(2)
    page = match.group(3) or 1
    if ver in PLATE_CN:
        ver = PLATE_CN[ver]
    if f"{ver}{plan}" == "真将":
        await bot.finish(ev, "真系没有真将哦。", at_sender=True)
    if match.re is PLATE_TABLE_RE:
        pic = await draw_plate_table(user, ver, plan, int(page))
    else:
        pic = await draw_plate_progress(user, ver, plan, int(page))
    await bot.send(ev, pic, at_sender=True)


@level_progress
async def _(bot: NoneBot, ev: CQEvent):
    user = await GetUserAndAuth(bot, ev)
    match: Match[str] = ev["match"]
    if not match:
        await bot.finish(ev, "输入错误，请重新输入难度等级。", at_sender=True)

    level = match.group(1)
    plan = match.group(2)
    category_ = match.group(3)
    page = match.group(4) or 1

    if level not in LEVEL_LIST:
        await bot.finish(ev, "无此等级", at_sender=True)
    if plan.lower() not in RANK_PLUS + COMBO_PLUS + SYNC_PLUS:
        await bot.finish(ev, "无此评价等级", at_sender=True)
    if LEVEL_LIST.index(level) < 11 or (
        plan.lower() in RANK_PLUS and RANK_PLUS.index(plan.lower()) < 8
    ):
        await bot.finish(ev, "兄啊，有点志向好不好", at_sender=True)
    if category_:
        target_category = CATEGORY_ALIAS.get(category_)
        if target_category:
            category = target_category
        else:
            await bot.finish(ev, f"无法指定查询「{category_}」", at_sender=True)
    else:
        category = Category.DEFAULT

    data = await draw_level_progress(user, level, plan, category, int(page))
    await bot.send(ev, data, at_sender=True)


@level_score_list
async def _(bot: NoneBot, ev: CQEvent):
    user = await GetUserAndAuth(bot, ev)
    match: Match[str] = ev["match"]
    if not match:
        await bot.finish(ev, "输入错误，请重新输入指定等级。", at_sender=True)

    rating = match.group(1)
    page = match.group(2) or 1
    if "." in rating:
        # 定数仅有一位小数，多位小数视为输入有误
        if not re.fullmatch(r"[0-9]+\.[0-9]", rating):
            await bot.finish(ev, "输入有误，定数仅有一位小数。", at_sender=True)
        rating = round(float(rating), 1)
    elif rating not in LEVEL_LIST:
        await bot.finish(ev, "无此等级", at_sender=True)

    result = await draw_level_score_list(user, rating, int(page))
    await bot.send(ev, result, at_sender=True)
