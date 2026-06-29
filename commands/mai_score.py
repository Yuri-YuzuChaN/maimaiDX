import re
from textwrap import dedent

from nonebot import NoneBot

from hoshino.typing import CQEvent, MessageSegment

from ..config import log, sv
from ..core.handler import draw_best50, draw_play_data, draw_song_galobal_data
from ..core.image.tools import image_to_base64, text_to_image
from ..core.merge.models import ServiceName
from ..core.service import mai
from .depend import GetUserAndAuth

b50 = ["b50", "B50"]
ap50 = ["ap50", "AP50"]

best50 = sv.on_prefix(b50 + ap50)
info = sv.on_prefix(["minfo", "Minfo", "MINFO", "info", "Info", "INFO"])
ginfo = sv.on_prefix(["ginfo", "Ginfo", "GINFO"])
score = sv.on_prefix(["分数线"])


@best50
async def _(bot: NoneBot, ev: CQEvent):
    user = await GetUserAndAuth(bot, ev)
    username: str = ev.message.extract_plain_text().strip()

    if (is_ap := ev.prefix.strip() in ap50) and user.service == ServiceName.DIVINGFISH:
        await bot.finish(ev, "仅落雪查分器支持AP50指令", at_sender=True)
    result = await draw_best50(user, username=username, all_perfect=is_ap)
    await bot.send(ev, result, at_sender=True)


@info
async def _(bot: NoneBot, ev: CQEvent):
    user = await GetUserAndAuth(bot, ev)
    data: str = ev.message.extract_plain_text().strip().lower()
    if not data:
        await bot.finish(ev, "请输入曲目id或曲名", at_sender=True)

    if data.isdigit() and (by_id := mai.total_list.by_id(int(data))):
        song = by_id
    elif by_t := mai.total_list.by_name(data):
        song = by_t
    else:
        aliases = mai.total_alias_list.by_alias(data)
        if not aliases:
            await bot.finish(ev, "未找到曲目", at_sender=True)
        elif len(aliases) != 1:
            msg = "找到相同别名的曲目，请使用以下ID查询：\n"
            for alias in aliases:
                msg += f"{alias.song_id}：{alias.alias[0]}\n"
            await bot.finish(ev, msg.strip(), at_sender=True)
        else:
            song_id = aliases[0].song_id
        song = mai.total_list.by_id(song_id)

    result = await draw_play_data(user, song)
    await bot.send(ev, result, at_sender=True)


@ginfo
async def _(bot: NoneBot, ev: CQEvent):
    args: str = ev.message.extract_plain_text().strip().lower()
    if not args:
        await bot.finish(ev, "请输入曲目id或曲名", at_sender=True)

    if args[0] not in "绿黄红紫白":
        level_index = 3
    else:
        level_index = "绿黄红紫白".index(args[0])
        args = args[1:].strip()
        if not args:
            await bot.finish(ev, "请输入曲目id或曲名", at_sender=True)
    if args.isdigit() and (by_id := mai.total_list.by_id(int(args))):
        song = by_id
    elif by_t := mai.total_list.by_name(args):
        song = by_t
    else:
        alias = mai.total_alias_list.by_alias(args)
        if not alias:
            await bot.finish(ev, "未找到曲目", at_sender=True)
        elif len(alias) != 1:
            msg = "找到相同别名的曲目，请使用以下ID查询：\n"
            for songs in alias:
                msg += f"{songs.song_id}：{songs.alias[0]}\n"
            await bot.finish(ev, msg.strip(), at_sender=True)
        else:
            song = mai.total_list.by_id(alias[0].song_id)
    if song is None:
        await bot.finish(ev, "未找到曲目", at_sender=True)
    if level_index >= len(song.difficulties):
        await bot.finish(ev, "该乐曲没有这个等级", at_sender=True)
    stats = song.difficulties[level_index].stats
    if not stats:
        await bot.finish(ev, "该乐曲还没有统计信息", at_sender=True)

    info = dedent(f"""\
        游玩次数：{round(stats.cnt)}
        拟合难度：{stats.fit_diff:.2f}
        平均达成率：{stats.avg:.2f}%
        平均 DX 分数：{stats.avg_dx:.1f}
        谱面成绩标准差：{stats.std_dev:.2f}""")
    await bot.send(
        ev, await draw_song_galobal_data(song, level_index) + info, at_sender=True
    )


@score
async def _(bot: NoneBot, ev: CQEvent):
    _args: str = ev.message.extract_plain_text().strip()
    args = _args.split()
    if len(args) == 1 and args[0] == "帮助":
        msg = dedent("""\
            此功能为查找某首歌分数线设计。
            命令格式：分数线「难度+歌曲id」「分数线」
            例如：分数线 紫799 100
            命令将返回分数线允许的「TAP」「GREAT」容错，
            以及「BREAK」50落等价的「TAP」「GREAT」数。
            以下为「TAP」「GREAT」的对应表：
                    GREAT / GOOD / MISS
            TAP         1 / 2.5  / 5
            HOLD        2 / 5    / 10
            SLIDE       3 / 7.5  / 15
            TOUCH       1 / 2.5  / 5
            BREAK       5 / 12.5 / 25 (外加200落)
        """).strip()
        await bot.send(
            ev,
            MessageSegment.image(image_to_base64(text_to_image(msg))),
            at_sender=True,
        )
    else:
        try:
            result = re.search(r"([绿黄红紫白])\s?([0-9]+)", _args)
            level_labels = ["绿", "黄", "红", "紫", "白"]
            level_labels2 = ["Basic", "Advanced", "Expert", "Master", "Re:MASTER"]
            level_index = level_labels.index(result.group(1))
            chart_id = int(result.group(2))
            line = float(args[-1])
            song = mai.total_list.by_id(chart_id)
            if song is None or level_index >= len(song.difficulties):
                raise ValueError
            chart = song.difficulties[level_index]
            tap = int(chart.notes.tap)
            slide = int(chart.notes.slide)
            hold = int(chart.notes.hold)
            touch = int(chart.notes.touch)
            brk = int(chart.notes.brk)
            total_score = (
                tap * 500 + slide * 1500 + hold * 1000 + touch * 500 + brk * 2500
            )
            break_bonus = 0.01 / brk
            break_50_reduce = total_score * break_bonus / 4
            reduce = 101 - line
            if reduce <= 0 or reduce >= 101:
                raise ValueError
            msg = (
                f"{song.song_name}「{level_labels2[level_index]}」\n"
                f"分数线「{line}%」\n允许的最多「TAP」「GREAT」数量为\n"
                f"「{(total_score * reduce / 10000):.2f}」(每个-{10000 / total_score:.4f}%),\n"
                f"「BREAK」50落(一共「{brk}」个)\n"
                f"等价于「{(break_50_reduce / 100):.3f}」个「TAP」"
                f"「GREAT」(-{break_50_reduce / total_score * 100:.4f}%)"
            )
            await bot.send(ev, msg, at_sender=True)
        except (AttributeError, ValueError) as e:
            log.exception(e)
            await bot.send(
                ev, "格式错误，输入“分数线 帮助”以查看帮助信息", at_sender=True
            )
