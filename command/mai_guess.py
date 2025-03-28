import asyncio
from textwrap import dedent

from nonebot import NoneBot

from hoshino.service import priv
from hoshino.typing import CQEvent, MessageSegment

from .. import sv
from ..libraries.maimaidx_music import guess
from ..libraries.maimaidx_music_info import draw_music_info

guess_music_start   = sv.on_fullmatch('猜歌')
guess_music_pic     = sv.on_fullmatch('猜曲绘')
guess_music_reset   = sv.on_fullmatch('重置猜歌')
guess_music_switch  = sv.on_suffix('mai猜歌')


@guess_music_start
async def guess_music(bot: NoneBot, ev: CQEvent):
    gid = ev.group_id
    if ev.group_id not in guess.switch.enable:
        await bot.finish(ev, '该群已关闭猜歌功能，开启请输入 开启mai猜歌')
    if gid in guess.Group:
        await bot.finish(ev, '该群已有正在进行的猜歌或猜曲绘')
    guess.start(gid)
    await bot.send(ev, dedent(''' \
        我将从热门乐曲中选择一首歌，每隔8秒描述它的特征，
        请输入歌曲的 id 标题 或 别名（需bot支持，无需大小写） 进行猜歌（DX乐谱和标准乐谱视为两首歌）。
        猜歌时查歌等其他命令依然可用。
    '''))
    await asyncio.sleep(4)
    for cycle in range(7):
        if ev.group_id not in guess.switch.enable or gid not in guess.Group or guess.Group[gid].end:
            break
        if cycle < 6:
            await bot.send(ev, f'{cycle + 1}/7 这首歌{guess.Group[gid].options[cycle]}')
            await asyncio.sleep(8)
        else:
            await bot.send(ev, f'''7/7 这首歌封面的一部分是：\n{MessageSegment.image(guess.Group[gid].img)}答案将在30秒后揭晓''')
            for _ in range(30):
                await asyncio.sleep(1)
                if gid in guess.Group:
                    if ev.group_id not in guess.switch.enable or guess.Group[gid].end:
                        return
                else:
                    return
            guess.Group[gid].end = True
            answer = f'''答案是：\n{await draw_music_info(guess.Group[gid].music)}'''
            guess.end(gid)
            await bot.send(ev, answer)


@guess_music_pic
async def guess_pic(bot: NoneBot, ev: CQEvent):
    gid = ev.group_id
    if ev.group_id not in guess.switch.enable:
        await bot.finish(ev, '该群已关闭猜歌功能，开启请输入 开启mai猜歌')
    if gid in guess.Group:
        await bot.finish(ev, '该群已有正在进行的猜歌或猜曲绘')
    guess.startpic(gid)
    await bot.send(ev, f'以下裁切图片是哪首谱面的曲绘：\n{MessageSegment.image(guess.Group[gid].img)}请在30s内输入答案')
    for _ in range(30):
        await asyncio.sleep(1)
        if gid in guess.Group:
            if ev.group_id not in guess.switch.enable or guess.Group[gid].end:
                return
        else:
            return
    guess.Group[gid].end = True
    answer = f'''答案是：\n{await draw_music_info(guess.Group[gid].music)}'''
    guess.end(gid)
    await bot.send(ev, answer)


@sv.on_message()
async def guess_music_solve(bot: NoneBot, ev: CQEvent):
    gid = ev.group_id
    if gid not in guess.Group:
        return
    ans: str = ev.message.extract_plain_text().strip().lower()
    if ans.lower() in guess.Group[gid].answer:
        guess.Group[gid].end = True
        answer = f'''猜对了，答案是：\n{await draw_music_info(guess.Group[gid].music)}'''
        guess.end(gid)
        await bot.send(ev, answer, at_sender=True)


@guess_music_reset
async def reset_guess(bot: NoneBot, ev: CQEvent):
    gid = ev.group_id
    if not priv.check_priv(ev, priv.ADMIN):
        msg = '仅允许管理员重置'
    elif gid in guess.Group:
        msg = '已重置该群猜歌'
        guess.end(gid)
    else:
        msg = '该群未处在猜歌状态'
    await bot.send(ev, msg)


@guess_music_switch
async def guess_on_off(bot: NoneBot, ev: CQEvent):
    gid = ev.group_id
    args: str = ev.message.extract_plain_text().strip()
    if not priv.check_priv(ev, priv.ADMIN):
        msg = '仅允许管理员开关'
    elif args == '开启':
        msg = await guess.on(gid)
    elif args == '关闭':
        msg = await guess.off(gid)
    else:
        msg = '指令错误'
    await bot.send(ev, msg, at_sender=True)