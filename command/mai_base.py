import random
from re import Match

from nonebot import NoneBot
from PIL import Image

from hoshino.service import priv
from hoshino.typing import CQEvent, MessageSegment

from .. import BOTNAME, Root, log, sv
from ..libraries.image import image_to_base64, music_picture
from ..libraries.maimaidx_api_data import maiApi
from ..libraries.maimaidx_error import *
from ..libraries.maimaidx_music import mai
from ..libraries.maimaidx_music_info import draw_music_info
from ..libraries.maimaidx_player_score import rating_ranking_data
from ..libraries.tool import qqhash

update_data         = sv.on_fullmatch('更新maimai数据')
maimaidxhelp        = sv.on_fullmatch(['帮助maimaiDX', '帮助maimaidx'])
maimaidxrepo        = sv.on_fullmatch(['项目地址maimaiDX', '项目地址maimaidx'])
mai_today           = sv.on_prefix(['今日mai', '今日舞萌', '今日运势'])
mai_what            = sv.on_rex(r'.*mai.*什么(.+)?')
random_song         = sv.on_rex(r'^[来随给]个((?:dx|sd|标准))?([绿黄红紫白]?)([0-9]+\+?)$')
rating_ranking      = sv.on_prefix(['查看排名', '查看排行'])
my_rating_ranking   = sv.on_fullmatch('我的排名')
data_update_daily   = sv.scheduled_job('cron', hour='4')


@update_data
async def _(bot: NoneBot, ev: CQEvent):
    if not priv.check_priv(ev, priv.SUPERUSER):
        return
    await mai.get_music()
    await mai.get_music_alias()
    await bot.send(ev, 'maimai数据更新完成')


@maimaidxhelp
async def _(bot: NoneBot, ev: CQEvent):
    await bot.send(
        ev, 
        MessageSegment.image(
            image_to_base64(Image.open((Root / 'maimaidxhelp.png')))
        ), 
        at_sender=True
    )


@maimaidxrepo
async def _(bot: NoneBot, ev: CQEvent):
    await bot.send(
        ev, 
        f'项目地址：https://github.com/Yuri-YuzuChaN/maimaiDX\n求star，求宣传~', 
        at_sender=True
    )

    
@mai_today
async def _(bot: NoneBot, ev: CQEvent):
    wm_list = [
        '拼机', 
        '推分', 
        '越级', 
        '下埋', 
        '夜勤', 
        '练底力', 
        '练手法', 
        '打旧框', 
        '干饭', 
        '抓绝赞', 
        '收歌'
    ]
    uid = ev.user_id
    h = qqhash(uid)
    rp = h % 100
    wm_value = []
    for i in range(11):
        wm_value.append(h & 3)
        h >>= 2
    msg = f'\n今日人品值：{rp}\n'
    for i in range(11):
        if wm_value[i] == 3:
            msg += f'宜 {wm_list[i]}\n'
        elif wm_value[i] == 0:
            msg += f'忌 {wm_list[i]}\n'
    music = mai.total_list[h % len(mai.total_list)]
    ds = '/'.join([str(_) for _ in music.ds])
    msg += f'{BOTNAME} Bot提醒您：打机时不要大力拍打或滑动哦\n今日推荐歌曲：\n'
    msg += f'ID.{music.id} - {music.title}'
    msg += MessageSegment.image(image_to_base64(Image.open(music_picture(music.id))))
    msg += ds
    await bot.send(ev, msg, at_sender=True)


@mai_what
async def _(bot: NoneBot, ev: CQEvent):
    match: Match[str] = ev['match']
    music = mai.total_list.random()
    user = None
    if (point := match.group(1)) and ('推分' in point or '上分' in point or '加分' in point):
        try:
            user = await maiApi.query_user_b50(qqid=ev.user_id)
            r = random.randint(0, 1)
            _ra = 0
            ignore = []
            if r == 0:
                if sd := user.charts.sd:
                    ignore = [m.song_id for m in sd if m.achievements < 100.5]
                    _ra = sd[-1].ra
            else:
                if dx := user.charts.dx:
                    ignore = [m.song_id for m in dx if m.achievements < 100.5]
                    _ra = dx[-1].ra
            if _ra != 0:
                ds = round(_ra / 22.4, 1)
                musiclist = mai.total_list.filter(ds=(ds, ds + 1))
                for _m in musiclist:
                    if int(_m.id) in ignore:
                        musiclist.remove(_m)
                music = musiclist.random()
        except (UserNotFoundError, UserDisabledQueryError):
            pass
    await bot.send(ev, await draw_music_info(music, ev.user_id, user))


@random_song
async def _(bot: NoneBot, ev: CQEvent):
    try:
        match: Match[str] = ev['match']
        diff = match.group(1)
        if diff == 'dx':
            tp = ['DX']
        elif diff == 'sd' or diff == '标准':
            tp = ['SD']
        else:
            tp = ['SD', 'DX']
        level = match.group(3)
        if match.group(2) == '':
            music_data = mai.total_list.filter(level=level, type=tp)
        else:
            music_data = mai.total_list.filter(level=level, diff=['绿黄红紫白'.index(match.group(2))], type=tp)
        if len(music_data) == 0:
            msg = '没有这样的乐曲哦。'
        else:
            msg = await draw_music_info(music_data.random(), ev.user_id)
    except:
        msg = '随机命令错误，请检查语法'
    await bot.send(ev, msg, at_sender=True)
        
        
@rating_ranking
async def _(bot: NoneBot, ev: CQEvent):
    args: str = ev.message.extract_plain_text().strip()
    page = 1
    name = ''
    if args.isdigit():
        page = int(args)
    else:
        name = args.lower()
    
    pic = await rating_ranking_data(name, page)
    await bot.send(ev, pic, at_sender=True)


@my_rating_ranking
async def _(bot: NoneBot, ev: CQEvent):
    try:
        user = await maiApi.query_user_b50(qqid=ev.user_id)
        rank_data = await maiApi.rating_ranking()
        for num, rank in enumerate(rank_data):
            if rank.username == user.username:
                result = f'您的Rating为「{rank.ra}」，排名第「{num + 1}」名'
                await bot.finish(ev, result, at_sender=True)
    except (UserNotFoundError, UserNotExistsError, UserDisabledQueryError) as e:
        await bot.finish(ev, str(e), at_sender=True)



@data_update_daily
async def _():
    await mai.get_music()
    mai.guess()
    log.info('maimaiDX数据更新完毕')
