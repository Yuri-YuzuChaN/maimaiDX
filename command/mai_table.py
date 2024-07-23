import re
from re import Match

from nonebot import NoneBot
from PIL import Image

from hoshino.service import sucmd
from hoshino.typing import CommandSession, CQEvent, MessageSegment

from .. import *
from ..libraries.image import image_to_base64
from ..libraries.maimaidx_music_info import draw_plate_table, draw_rating_table
from ..libraries.maimaidx_player_score import (
    level_achievement_list_data,
    level_process_data,
    player_plate_data,
    rise_score_data,
)
from ..libraries.maimaidx_update_table import update_plate_table, update_rating_table

update_table            = sucmd('updatetable', aliases=('更新定数表'))
update_plate            = sucmd('updateplate', aliases=('更新完成表'))
table_pfm               = sv.on_suffix('完成表')
rating_table            = sv.on_suffix('定数表')
rise_score              = sv.on_rex(r'^我要在?([0-9]+\+?)?上([0-9]+)分\s?(.+)?')
plate_process           = sv.on_rex(r'^([真超檄橙暁晓桃櫻樱紫菫堇白雪輝辉熊華华爽舞霸宙星祭祝双])([極极将舞神者]舞?)进度\s?(.+)?')
level_process           = sv.on_rex(r'^([0-9]+\+?)\s?([abcdsfxp\+]+)\s?([\u4e00-\u9fa5]+)?进度\s?([0-9]+)?\s?(.+)?')
level_achievement_list  = sv.on_rex(r'^([0-9]+\.?[0-9]?\+?)分数列表\s?([0-9]+)?\s?(.+)?')


@update_table
async def _(session: CommandSession):
    await session.send(await update_rating_table())


@update_plate
async def _(session: CommandSession):
    await session.send(await update_plate_table())
    

@table_pfm
async def _(bot: NoneBot, ev: CQEvent):
    qqid = ev.user_id
    args: str = ev.message.extract_plain_text().strip()
    rating = re.search(r'^([0-9]+\+?)(app|fcp|ap|fc)?', args, re.IGNORECASE)
    plate = re.search(r'^([真超檄橙暁晓桃櫻樱紫菫堇白雪輝辉熊華华爽煌舞霸宙星祭祝双])([極极将舞神者]舞?)$', args)
    if rating:
        ra = rating.group(1)
        plan = rating.group(2)
        if args in levelList[:5]:
            await bot.send(ev, '只支持查询lv6-15的完成表', at_sender=True)
        elif ra in levelList[5:]:
            pic = await draw_rating_table(qqid, ra, True if plan and plan.lower() in combo_rank else False)
            await bot.send(ev, pic, at_sender=True)
        else:
            await bot.send(ev, '无法识别的表格', at_sender=True)
    elif plate:
        ver = plate.group(1)
        plan = plate.group(2)
        if ver in platecn:
            ver = platecn[ver]
        if ver in ['舞', '霸']:
            await bot.finish(ev, '暂不支持查询「舞」系和「霸者」的牌子', at_sender=True)
        if f'{ver}{plan}' == '真将':
            await bot.finish(ev, '真系没有真将哦', at_sender=True)
        pic = await draw_plate_table(qqid, ver, plan)
        await bot.send(ev, pic, at_sender=True)
    else:
        await bot.send(ev, '无法识别的表格', at_sender=True)


@rating_table
async def _(bot: NoneBot, ev: CQEvent):
    args: str = ev.message.extract_plain_text().strip()
    if args in levelList[:5]:
        await bot.send(ev, '只支持查询lv6-15的定数表', at_sender=True)
    elif args in levelList[5:]:
        if args in levelList[-3:]:
            img = ratingdir / '14.png'
        else:
            img = ratingdir / f'{args}.png'
        await bot.send(ev, MessageSegment.image(image_to_base64(Image.open(img))))
    else:
        await bot.send(ev, '无法识别的定数', at_sender=True)


@rise_score
async def _(bot: NoneBot, ev: CQEvent):
    qqid = ev.user_id
    match: Match[str] = ev['match']
    username = None
    for i in ev.message:
        if i.type == 'at' and i.data['qq'] != 'all':
            qqid = int(i.data['qq'])

    rating = match.group(1)
    score = match.group(2)
    
    if rating and rating not in levelList:
        await bot.finish(ev, '无此等级', at_sender=True)
    elif match.group(3):
        username = match.group(3).strip()
    if username:
        qqid = None
        
    data = await rise_score_data(qqid, username, rating, score)
    await bot.send(ev, data, at_sender=True)
    

@plate_process
async def _(bot: NoneBot, ev: CQEvent):
    qqid = ev.user_id
    match: Match[str] = ev['match']
    username = None
    for i in ev.message:
        if i.type == 'at' and i.data['qq'] != 'all':
            qqid = int(i.data['qq'])

    ver = match.group(1)
    plan = match.group(2)
    if f'{ver}{plan}' == '真将':
        await bot.finish(ev, '真系没有真将哦', at_sender=True)
    elif match.group(3):
        username = match.group(3).strip()
    if username:
        qqid = None

    data = await player_plate_data(qqid, username, ver, plan)
    await bot.send(ev, data, at_sender=True)


@level_process
async def _(bot: NoneBot, ev: CQEvent):
    qqid = ev.user_id
    match: Match[str] = ev['match']
    username = ''
    for i in ev.message:
        if i.type == 'at' and i.data['qq'] != 'all':
            qqid = int(i.data['qq'])

    level = match.group(1)
    plan = match.group(2)
    category = match.group(3)
    page = match.group(4)
    username = match.group(5)
    if level not in levelList:
        await bot.finish(ev, '无此等级', at_sender=True)
    if plan.lower() not in scoreRank + comboRank + syncRank:
        await bot.finish(ev, '无此评价等级', at_sender=True)
    if levelList.index(level) < 11 or (plan.lower() in scoreRank and scoreRank.index(plan.lower()) < 8):
        await bot.finish(ev, '兄啊，有点志向好不好', at_sender=True)
    if category:
        if category in ['已完成', '未完成', '未开始']:
            _c = {
                '已完成': 'completed',
                '未完成': 'unfinished',
                '未开始': 'notstarted',
                '未游玩': 'notstarted'
            }
            category = _c[category]
        else:
            await bot.finish(ev, f'无法指定查询「{category}」', at_sender=True)
    else:
        category = 'default'

    data = await level_process_data(qqid, username, level, plan, category, int(page) if page else 1)
    await bot.send(ev, data, at_sender=True)
    
    
@level_achievement_list
async def _(bot: NoneBot, ev: CQEvent):
    qqid = ev.user_id
    match: Match[str] = ev['match']
    username = ''
    for i in ev.message:
        if i.type == 'at' and i.data['qq'] != 'all':
            qqid = int(i.data['qq'])
    
    rating = match.group(1)
    page = match.group(2)
    username = match.group(3)
    
    try:
        if '.' in rating:
            rating = round(float(rating), 1)
        elif rating not in levelList:
            await bot.finish(ev, '无此等级', at_sender=True)
    except ValueError:
        if rating not in levelList:
            await bot.finish(ev, '无此等级', at_sender=True)

    data = await level_achievement_list_data(qqid, username, rating, int(page) if page else 1)
    await bot.send(ev, data, at_sender=True)