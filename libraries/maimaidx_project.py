import io
import os
import time
import aiofiles
import traceback
from re import Match
from typing import Optional, Union

from PIL import Image, ImageDraw

from quart.utils import run_sync
from hoshino.typing import MessageSegment

import pyecharts.options as opts
from pyecharts.charts import Pie
from pyecharts.render import make_snapshot
from snapshot_phantomjs import snapshot

from .. import *
from .image import *
from .maimai_best_50 import *
from .maimaidx_api_data import *
from .maimaidx_music import Music, get_cover_len4_id, mai

SONGS_PER_PAGE = 25
level_labels = ['绿', '黄', '红', '紫', '白']
realAchievementList = {}
for acc in [i / 10 for i in range(10, 151)]:
    realAchievementList[f'{acc:.1f}'] = generateAchievementList(acc)
plate_to_version = {
    '初': 'maimai',
    '真': 'maimai PLUS',
    '超': 'maimai GreeN',
    '檄': 'maimai GreeN PLUS',
    '橙': 'maimai ORANGE',
    '暁': 'maimai ORANGE PLUS',
    '晓': 'maimai ORANGE PLUS',
    '桃': 'maimai PiNK',
    '櫻': 'maimai PiNK PLUS',
    '樱': 'maimai PiNK PLUS',
    '紫': 'maimai MURASAKi',
    '菫': 'maimai MURASAKi PLUS',
    '堇': 'maimai MURASAKi PLUS',
    '白': 'maimai MiLK',
    '雪': 'MiLK PLUS',
    '輝': 'maimai FiNALE',
    '辉': 'maimai FiNALE',
    '熊': 'maimai でらっくす',
    '華': 'maimai でらっくす',
    '華': 'maimai でらっくす PLUS',
    '华': 'maimai でらっくす PLUS',
    '华': 'maimai でらっくす',
    '爽': 'maimai でらっくす Splash',
    '煌': 'maimai でらっくす Splash',
    '煌': 'maimai でらっくす Splash PLUS',
}

maimaidir = os.path.join(static, 'mai', 'pic')

SIYUAN = os.path.join(static, 'SourceHanSansSC-Bold.otf')
TBFONT = os.path.join(static, 'Torus SemiBold.otf')
category = {
    'POPSアニメ': 'anime',
    'maimai': 'maimai',
    'niconicoボーカロイド': 'niconico',
    '東方Project': 'touhou',
    'ゲームバラエティ': 'game',
    'オンゲキCHUNITHM': 'ongeki'
}

async def download_arcade_info(save=True):
    try:
        async with aiohttp.request('GET', 'http://wc.wahlap.net/maidx/rest/location', timeout=aiohttp.ClientTimeout(total=5)) as req:
            if req.status == 200:
                arcades_data = await req.json()
                current_names = [c_a['name'] for c_a in arcades]
                for arcade in arcades_data:
                    if arcade['arcadeName'] not in current_names:
                        arcade_dict = {
                            'name': arcade['arcadeName'],
                            'location': arcade['address'],
                            'province': arcade['province'],
                            'mall': arcade['mall'],
                            'num': arcade['machineCount'],
                            'id': arcade['id'],
                            'alias': [], 'group': [],
                            'person': 0, 'by': '', 'time': ''
                        }
                        arcades.append(arcade_dict)
                    else:
                        arcade_dict = arcades[current_names.index(arcade['arcadeName'])]
                        arcade_dict['location'] = arcade['address']
                        arcade_dict['province'] = arcade['province']
                        arcade_dict['mall'] = arcade['mall']
                        arcade_dict['num'] = arcade['machineCount']
                        arcade_dict['id'] = arcade['id']
                if save:
                    async with aiofiles.open(arcades_json, 'w', encoding='utf-8') as f:
                        await f.write(json.dumps(arcades, ensure_ascii=False, indent=4))
            else:
                log.error('获取机厅信息失败')
    except Exception:
        log.error(f'Error: {traceback.format_exc()}')
        log.error('获取机厅信息失败')

async def download_music_pictrue(id: Union[int, str]) -> io.BytesIO:
    try:
        len4id = get_cover_len4_id(id)
        if os.path.exists(file := os.path.join(static, 'mai', 'cover', f'{len4id}.png')):
            return file
        async with aiohttp.request('GET', f"https://www.diving-fish.com/covers/{len4id}.png", timeout=aiohttp.ClientTimeout(total=5)) as req:
            if req.status == 200:
                return io.BytesIO(await req.read())
            else:
                return os.path.join(static, 'mai', 'cover', '0000.png')
    except:
        return os.path.join(static, 'mai', 'cover', '0000.png')

async def draw_music_info(music: Music) -> MessageSegment:
    im = Image.new('RGBA', (800, 1000))

    im = Image.open(os.path.join(maimaidir, 'music_bg.png')).convert('RGBA')
    genre = Image.open(os.path.join(maimaidir, f'music-{category[music.genre]}.png'))
    cover = Image.open(await download_music_pictrue(music.id)).resize((360, 360))
    ver = Image.open(os.path.join(maimaidir, f'{music.type}.png')).resize((94, 35))
    line = Image.new('RGBA', (400, 2), (255, 255, 255, 255))

    im.alpha_composite(genre, (150, 170))
    im.alpha_composite(cover, (170, 260))
    im.alpha_composite(ver, (435, 585))
    im.alpha_composite(line, (150, 710))

    dr = ImageDraw.Draw(im)
    tb = DrawText(dr, TBFONT)
    sy = DrawText(dr, SIYUAN)

    tb.draw(200, 195, 24, music.id, anchor='mm')
    sy.draw(410, 195, 22, music.genre, anchor='mm')
    sy.draw_partial_opacity(350, 660, 30, music.title, 1, anchor='mm')
    sy.draw_partial_opacity(350, 690, 12, music.artist, 1, anchor='mm')
    sy.draw_partial_opacity(150, 725, 15, f'Version: {music.version}', 1, anchor='lm')
    sy.draw_partial_opacity(550, 725, 15, f'BPM: {music.bpm}', 1, anchor='rm')
    for n, i in enumerate(list(map(str, music.ds))):
        if n == 4:
            color = (195, 70, 231, 255)
        else:
            color = (255, 255, 255, 255)
        tb.draw(160 + 95 * n, 814, 25, i, color, 'mm')
    sy.draw(350, 980, 14, F'Designed by Yuri-YuzuChaN | Generated by {BOTNAME} BOT', (255, 255, 255, 255), 'mm', 1, (159, 81, 220, 255))
    msg = MessageSegment.image(image_to_base64(im))

    return msg

async def music_play_data(payload: dict, song: str) -> Union[str, MessageSegment, None]:
    data = await get_player_data('plate', payload)
    if isinstance(data, str):
        return data

    player_data: list[dict[str, Union[float, str, int]]] = []
    for i in data['verlist']:
        if i['id'] == int(song):
            player_data.append(i)
    if not player_data:
        return '您未游玩该曲目'
    
    player_data.sort(key=lambda a: a['level_index'])
    music = mai.total_list.by_id(song)
    diffnum = len(music.ds)

    im = Image.open(os.path.join(maimaidir, 'info_bg.png')).convert('RGBA')
    genre = Image.open(os.path.join(maimaidir, f'info-{category[music.genre]}.png'))
    cover = Image.open(await download_music_pictrue(music.id)).resize((210, 210))
    version = Image.open(os.path.join(maimaidir, f'{music.type}.png')).resize((108, 40))

    dr = ImageDraw.Draw(im)
    tb = DrawText(dr, TBFONT)
    sy = DrawText(dr, SIYUAN)

    im.alpha_composite(genre, (45, 145))
    im.alpha_composite(cover, (69, 184))
    im.alpha_composite(version, (725, 360))

    tb.draw(430, 167, 20, music.id, anchor='mm')
    sy.draw(610, 167, 20, music.genre, anchor='mm')
    sy.draw(295, 225, 30, music.title, anchor='lm')
    sy.draw(295, 260, 15, f'Artist: {music.artist}', anchor='lm')
    sy.draw(295, 310, 15, f'BPM: {music.bpm}', anchor='lm')
    sy.draw(295, 330, 15, f'Version: {music.version}', anchor='lm')

    y = 120
    diff = 0
    TEXT_COLOR = [(14, 117, 54, 255), (199, 69, 12, 255), (175, 0, 50, 255), (103, 20, 141, 255), (103, 20, 141, 255)]
    for num in range(diffnum):
        try:
            if num == player_data[diff]['level_index']:
                _data = player_data[diff]
                ds = music.ds[_data['level_index']]
                ra, rate = computeRa(ds, _data['achievements'], israte=True)

                rank = Image.open(os.path.join(maimaidir, f'UI_TTR_PhotoParts_{rate}.png')).resize((97, 60))
                im.alpha_composite(rank, (440, 515 + y * num))
                if _data['fc']:
                    fcl = {'fc': 'FC', 'fcp': 'FCp', 'ap': 'AP', 'app': 'APp'}
                    fc = Image.open(os.path.join(maimaidir, f'UI_CHR_PlayBonus_{fcl[_data["fc"]]}.png')).resize((76, 76))
                    im.alpha_composite(fc, (575, 511 + y * num))
                if _data['fs']:
                    fsl = {'fs': 'FS', 'fsp': 'FSp', 'fsd': 'FSD', 'fsdp': 'FSDp'}
                    fs = Image.open(os.path.join(maimaidir, f'UI_CHR_PlayBonus_{fsl[_data["fs"]]}.png')).resize((76, 76))
                    im.alpha_composite(fs, (650, 511 + y * num))

                p, s = f'{_data["achievements"]:.4f}'.split('.')
                r = tb.get_box(p, 36)
                tb.draw(90, 545 + y * num, 30, ds, anchor='mm')
                tb.draw(200, 567 + y * num, 36, p, TEXT_COLOR[num], 'ld')
                tb.draw(200 + r[2], 565 + y * num, 30, f'.{s}%', TEXT_COLOR[num], 'ld')
                tb.draw(790, 545 + y * num, 30, ra, TEXT_COLOR[num], 'mm')
                diff += 1
        except IndexError:
            pass

    sy.draw(450, 1180, 20, f'Designed by Yuri-YuzuChaN | Generated by {BOTNAME} BOT', (159, 81, 220, 255), 'mm', 2, (255, 255, 255, 255))
    msg = MessageSegment.image(image_to_base64(im))

    return msg

async def music_global_data(music: Music, level_index: int) -> Union[str, MessageSegment, None]:
    stats = music.stats[level_index]
    fc_data_pair = [list(z) for z in zip([c.upper() if c else "Not FC" for c in [""] + comboRank], stats.fc_dist)]
    acc_data_pair = [list(z) for z in zip([s.upper() for s in scoreRank], stats.dist)]

    Pie(
        init_opts=opts.InitOpts(
            width="1000px",
            height="800px",
            bg_color="#fff",
            js_host=static + '/'
        )
    ).add(
        series_name="全连等级",
        data_pair=fc_data_pair,
        radius=[0, "30%"],
        label_opts=opts.LabelOpts(
            position="outside",
            formatter="{a|{a}}{abg|}\n{hr|}\n {b|{b}: }{c}  {per|{d}%}  ",
            background_color="#eee",
            border_color="#aaa",
            border_width=1,
            border_radius=4,
            rich={
                "a": {"color": "#999", "lineHeight": 22, "align": "center"},
                "abg": {
                    "backgroundColor": "#e3e3e3",
                    "width": "100%",
                    "align": "right",
                    "height": 22,
                    "borderRadius": [4, 4, 0, 0],
                },
                "hr": {
                    "borderColor": "#aaa",
                    "width": "100%",
                    "borderWidth": 0.5,
                    "height": 0,
                },
                "b": {"fontSize": 16, "lineHeight": 33},
                "per": {
                    "color": "#eee",
                    "backgroundColor": "#334455",
                    "padding": [2, 4],
                    "borderRadius": 2,
                },
            },
        )
    ).add(
        series_name="达成率等级",
        data_pair=acc_data_pair,
        radius=["50%", "70%"],
        is_clockwise=True,
        label_opts=opts.LabelOpts(
            position="outside",
            formatter="{a|{a}}{abg|}\n{hr|}\n {b|{b}: }{c}  {per|{d}%}  ",
            background_color="#eee",
            border_color="#aaa",
            border_width=1,
            border_radius=4,
            rich={
                "a": {"color": "#999", "lineHeight": 22, "align": "center"},
                "abg": {
                    "backgroundColor": "#e3e3e3",
                    "width": "100%",
                    "align": "right",
                    "height": 22,
                    "borderRadius": [4, 4, 0, 0],
                },
                "hr": {
                    "borderColor": "#aaa",
                    "width": "100%",
                    "borderWidth": 0.5,
                    "height": 0,
                },
                "b": {"fontSize": 16, "lineHeight": 33},
                "per": {
                    "color": "#eee",
                    "backgroundColor": "#334455",
                    "padding": [2, 4],
                    "borderRadius": 2,
                },
            },
        )
    ).set_global_opts(
        title_opts=opts.TitleOpts(
            title=f"{music.id} {music.title} {diffs[level_index]}",
            pos_left="center",
            pos_top="20",
            title_textstyle_opts=opts.TextStyleOpts(color="#2c343c"),
        ),
        legend_opts=opts.LegendOpts(
            pos_left=15,
            pos_top=10,
            orient="vertical"
        )
    ).set_series_opts(
        tooltip_opts=opts.TooltipOpts(
            trigger="item", formatter="{a} <br/>{b}: {c} ({d}%)"
        )
    ).render(os.path.join(static, "temp_pie.html"))
    await run_sync(make_snapshot)(snapshot, os.path.join(static, "temp_pie.html"), os.path.join(static, "temp_pie.png"), is_remove_html=False)

    im = Image.open(os.path.join(static, "temp_pie.png"))
    msg = MessageSegment.image(image_to_base64(im))

    return msg

async def query_chart_data(match: Match) -> str:
    if match.group(1) != '':
        try:
            level_index = level_labels.index(match.group(1))
            level_name = ['Basic', 'Advanced', 'Expert', 'Master', 'Re: MASTER']
            name = match.group(2)
            music = mai.total_list.by_id(name)
            chart = music.charts[level_index]
            stats = music.stats[level_index]
            ds = music.ds[level_index]
            level = music.level[level_index]
            if len(chart['notes']) == 4:
                result = f'''{level_name[level_index]} {level}({ds})
TAP: {chart.tap}
HOLD: {chart.hold}
SLIDE: {chart.slide}
BREAK: {chart.brk}
谱师: {chart.charter}
拟合难度: {stats.fit_difficulty:.2f}'''
            else:
                result = f'''{level_name[level_index]} {level}({ds})
TAP: {chart.tap}
HOLD: {chart.hold}
SLIDE: {chart.slide}
TOUCH: {chart.touch}
BREAK: {chart.brk}
谱师: {chart.charter}
拟合难度: {stats.fit_difficulty:.2f}'''

            len4id = get_cover_len4_id(music.id)
            if os.path.exists(file := os.path.join(static, 'mai', 'cover', f'{len4id}.png')):
                img = file
            else:
                img = os.path.join(static, 'mai', 'cover', '0000.png')

            msg = f'''{music.id}. {music.title}
{MessageSegment.image(f"file:///{img}")}
{result}'''
        except:
            msg = '未找到该谱面'
    else:
        try:
            name = match.group(2)
            music = mai.total_list.by_id(name)
            msg = await draw_music_info(music)

        except Exception as e:
            log.error(traceback.format_exc())
            msg = '未找到该乐曲'
    
    return msg

async def rise_score_data(payload: dict, match: Match, nickname: Optional[str] = None) -> Union[MessageSegment, str]:
    """
    上分数据
    - `payload` : 传递给查分器的数据
    - `match` : 正则结果
    - `nickname` : 用户昵称
    """
    dx_ra_lowest = 999
    sd_ra_lowest = 999
    player_dx_list = []
    player_sd_list = []
    music_dx_list = []
    music_sd_list = []

    player_data = await get_player_data('best', payload)

    if isinstance(player_data, str):
        return player_data

    for dx in player_data['charts']['dx']:
        dx_ra_lowest = min(dx_ra_lowest, dx['ra'])
        player_dx_list.append([int(dx['song_id']), int(dx["level_index"]), int(dx['ra'])])
    for sd in player_data['charts']['sd']:
        sd_ra_lowest = min(sd_ra_lowest, sd['ra'])
        player_sd_list.append([int(sd['song_id']), int(sd["level_index"]), int(sd['ra'])])
    player_dx_id_list = [[d[0], d[1]] for d in player_dx_list]
    player_sd_id_list = [[s[0], s[1]] for s in player_sd_list]

    for music in mai.total_list:
        for i, ds in enumerate(music.ds):
            for achievement in realAchievementList[f'{ds:.1f}']:
                if match.group(1) and music['level'][i] != match.group(1): continue
                if f'{achievement:.1f}' == '100.5':
                    index_score = 12
                else:
                    index_score = [index for index, acc in enumerate(achievementList[:-1]) if acc <= achievement < achievementList[index + 1]][0]
                if music.is_new:
                    music_ra = computeRa(ds, achievement)
                    if music_ra < dx_ra_lowest: continue
                    if [int(music.id), i] in player_dx_id_list:
                        player_ra = player_dx_list[player_dx_id_list.index([int(music.id), i])][2]
                        if music_ra - player_ra == int(match.group(2)) and [int(music.id), i, music_ra] not in player_dx_list:
                            music_dx_list.append([music, diffs[i], ds, achievement, scoreRank[index_score + 1].upper(), music_ra])
                    else:
                        if music_ra - dx_ra_lowest == int(match.group(2)) and [int(music.id), i, music_ra] not in player_dx_list:
                            music_dx_list.append([music, diffs[i], ds, achievement, scoreRank[index_score + 1].upper(), music_ra])
                else:
                    music_ra = computeRa(ds, achievement)
                    if music_ra < sd_ra_lowest: continue
                    if [int(music.id), i] in player_sd_id_list:
                        player_ra = player_sd_list[player_sd_id_list.index([int(music.id), i])][2]
                        if music_ra - player_ra == int(match.group(2)) and [int(music.id), i, music_ra] not in player_sd_list:
                            music_sd_list.append([music, diffs[i], ds, achievement, scoreRank[index_score + 1].upper(), music_ra])
                    else:
                        if music_ra - sd_ra_lowest == int(match.group(2)) and [int(music.id), i, music_ra] not in player_sd_list:
                            music_sd_list.append([music, diffs[i], ds, achievement, scoreRank[index_score + 1].upper(), music_ra])

    if len(music_dx_list) == 0 and len(music_sd_list) == 0:
        return '没有找到这样的乐曲'
    elif len(music_dx_list) + len(music_sd_list) > 60:
        return f'结果过多({len(music_dx_list) + len(music_sd_list)} 条)，请缩小查询范围。'

    appellation = nickname if nickname else '您'
    msg = ''
    if len(music_sd_list) != 0:
        msg += f'为{appellation}推荐以下标准乐曲：\n'
        for music, diff, ds, achievement, rank, ra in sorted(music_sd_list, key=lambda i: int(i[0]['id'])):
            msg += f'{music["id"]}. {music["title"]} {diff} {ds} {achievement} {rank} {ra}\n'
    if len(music_dx_list) != 0:
        msg += f'\n为{appellation}推荐以下new乐曲：\n'
        for music, diff, ds, achievement, rank, ra in sorted(music_dx_list, key=lambda i: int(i[0]['id'])):
            msg += f'{music["id"]}. {music["title"]} {diff} {ds} {achievement} {rank} {ra}\n'

    return MessageSegment.image(image_to_base64(text_to_image(msg.strip())))

async def player_plate_data(payload: dict, match: Match, nickname: Optional[str]) -> Union[MessageSegment, str]:
    song_played = []
    song_remain_basic = []
    song_remain_advanced = []
    song_remain_expert = []
    song_remain_master = []
    song_remain_re_master = []
    song_remain_difficult = []

    data = await get_player_data('plate', payload)

    if isinstance(data, str):
        return data

    if match.group(2) in ['将', '者']:
        for song in data['verlist']:
            if song['level_index'] == 0 and song['achievements'] < (100.0 if match.group(2) == '将' else 80.0):
                song_remain_basic.append([song['id'], song['level_index']])
            if song['level_index'] == 1 and song['achievements'] < (100.0 if match.group(2) == '将' else 80.0):
                song_remain_advanced.append([song['id'], song['level_index']])
            if song['level_index'] == 2 and song['achievements'] < (100.0 if match.group(2) == '将' else 80.0):
                song_remain_expert.append([song['id'], song['level_index']])
            if song['level_index'] == 3 and song['achievements'] < (100.0 if match.group(2) == '将' else 80.0):
                song_remain_master.append([song['id'], song['level_index']])
            if match.group(1) in ['舞', '霸'] and song['level_index'] == 4 and song['achievements'] < (100.0 if match.group(2) == '将' else 80.0):
                song_remain_re_master.append([song['id'], song['level_index']])
            song_played.append([song['id'], song['level_index']])
    elif match.group(2) in ['極', '极']:
        for song in data['verlist']:
            if song['level_index'] == 0 and not song['fc']:
                song_remain_basic.append([song['id'], song['level_index']])
            if song['level_index'] == 1 and not song['fc']:
                song_remain_advanced.append([song['id'], song['level_index']])
            if song['level_index'] == 2 and not song['fc']:
                song_remain_expert.append([song['id'], song['level_index']])
            if song['level_index'] == 3 and not song['fc']:
                song_remain_master.append([song['id'], song['level_index']])
            if match.group(1) == '舞' and song['level_index'] == 4 and not song['fc']:
                song_remain_re_master.append([song['id'], song['level_index']])
            song_played.append([song['id'], song['level_index']])
    elif match.group(2) == '舞舞':
        for song in data['verlist']:
            if song['level_index'] == 0 and song['fs'] not in ['fsd', 'fsdp']:
                song_remain_basic.append([song['id'], song['level_index']])
            if song['level_index'] == 1 and song['fs'] not in ['fsd', 'fsdp']:
                song_remain_advanced.append([song['id'], song['level_index']])
            if song['level_index'] == 2 and song['fs'] not in ['fsd', 'fsdp']:
                song_remain_expert.append([song['id'], song['level_index']])
            if song['level_index'] == 3 and song['fs'] not in ['fsd', 'fsdp']:
                song_remain_master.append([song['id'], song['level_index']])
            if match.group(1) == '舞' and song['level_index'] == 4 and song['fs'] not in ['fsd', 'fsdp']:
                song_remain_re_master.append([song['id'], song['level_index']])
            song_played.append([song['id'], song['level_index']])
    elif match.group(2) == '神':
        for song in data['verlist']:
            if song['level_index'] == 0 and song['fc'] not in ['ap', 'app']:
                song_remain_basic.append([song['id'], song['level_index']])
            if song['level_index'] == 1 and song['fc'] not in ['ap', 'app']:
                song_remain_advanced.append([song['id'], song['level_index']])
            if song['level_index'] == 2 and song['fc'] not in ['ap', 'app']:
                song_remain_expert.append([song['id'], song['level_index']])
            if song['level_index'] == 3 and song['fc'] not in ['ap', 'app']:
                song_remain_master.append([song['id'], song['level_index']])
            if match.group(1) == '舞' and song['level_index'] == 4 and song['fc'] not in ['ap', 'app']:
                song_remain_re_master.append([song['id'], song['level_index']])
            song_played.append([song['id'], song['level_index']])
    for music in mai.total_list:
        if music.version in payload['version']:
            if [int(music.id), 0] not in song_played:
                song_remain_basic.append([int(music.id), 0])
            if [int(music.id), 1] not in song_played:
                song_remain_advanced.append([int(music.id), 1])
            if [int(music.id), 2] not in song_played:
                song_remain_expert.append([int(music.id), 2])
            if [int(music.id), 3] not in song_played:
                song_remain_master.append([int(music.id), 3])
            if match.group(1) in ['舞', '霸'] and len(music.level) == 5 and [int(music.id), 4] not in song_played:
                song_remain_re_master.append([int(music.id), 4])
    song_remain_basic = sorted(song_remain_basic, key=lambda i: int(i[0]))
    song_remain_advanced = sorted(song_remain_advanced, key=lambda i: int(i[0]))
    song_remain_expert = sorted(song_remain_expert, key=lambda i: int(i[0]))
    song_remain_master = sorted(song_remain_master, key=lambda i: int(i[0]))
    song_remain_re_master = sorted(song_remain_re_master, key=lambda i: int(i[0]))
    for song in song_remain_basic + song_remain_advanced + song_remain_expert + song_remain_master + song_remain_re_master:
        music = mai.total_list.by_id(str(song[0]))
        if music.ds[song[1]] > 13.6:
            song_remain_difficult.append([music.id, music.title, diffs[song[1]], music.ds[song[1]], song[1]])

    appellation = nickname if nickname else '您'

    msg = f'''{appellation}的{match.group(1)}{match.group(2)}剩余进度如下：
Basic剩余{len(song_remain_basic)}首
Advanced剩余{len(song_remain_advanced)}首
Expert剩余{len(song_remain_expert)}首
Master剩余{len(song_remain_master)}首
'''
    song_remain: list[list] = song_remain_basic + song_remain_advanced + song_remain_expert + song_remain_master + song_remain_re_master
    song_record = [[s['id'], s['level_index']] for s in data['verlist']]
    if match.group(1) in ['舞', '霸']:
        msg += f'Re:Master剩余{len(song_remain_re_master)}首\n'
    if len(song_remain_difficult) > 0:
        if len(song_remain_difficult) < 60:
            msg += '剩余定数大于13.6的曲目：\n'
            for i, s in enumerate(sorted(song_remain_difficult, key=lambda i: i[3])):
                self_record = ''
                if [int(s[0]), s[-1]] in song_record:
                    record_index = song_record.index([int(s[0]), s[-1]])
                    if match.group(2) in ['将', '者']:
                        self_record = str(data['verlist'][record_index]['achievements']) + '%'
                    elif match.group(2) in ['極', '极', '神']:
                        if data['verlist'][record_index]['fc']:
                            self_record = comboRank[combo_rank.index(data['verlist'][record_index]['fc'])].upper()
                    elif match.group(2) == '舞舞':
                        if data['verlist'][record_index]['fs']:
                            self_record = syncRank[sync_rank.index(data['verlist'][record_index]['fs'])].upper()
                msg += f'No.{i + 1} {s[0]}. {s[1]} {s[2]} {s[3]} {self_record}'.strip() + '\n'
            if len(song_remain_difficult) > 10:
                msg = MessageSegment.image(image_to_base64(text_to_image(msg.strip())))
        else:
            msg += f'还有{len(song_remain_difficult)}首大于13.6定数的曲目，加油推分捏！\n'
    elif len(song_remain) > 0:
        for i, s in enumerate(song_remain):
            m = mai.total_list.by_id(str(s[0]))
            ds = m.ds[s[1]]
            song_remain[i].append(ds)
        if len(song_remain) < 60:
            msg += '剩余曲目：\n'
            for i, s in enumerate(sorted(song_remain, key=lambda i: i[2])):
                m = mai.total_list.by_id(str(s[0]))
                self_record = ''
                if [int(s[0]), s[-1]] in song_record:
                    record_index = song_record.index([int(s[0]), s[-1]])
                    if match.group(2) in ['将', '者']:
                        self_record = str(data['verlist'][record_index]['achievements']) + '%'
                    elif match.group(2) in ['極', '极', '神']:
                        if data['verlist'][record_index]['fc']:
                            self_record = comboRank[combo_rank.index(data['verlist'][record_index]['fc'])].upper()
                    elif match.group(2) == '舞舞':
                        if data['verlist'][record_index]['fs']:
                            self_record = syncRank[sync_rank.index(data['verlist'][record_index]['fs'])].upper()
                msg += f'No.{i + 1} {m.id}. {m.title} {diffs[s[1]]} {m.ds[s[1]]} {self_record}'.strip() + '\n'
            if len(song_remain) > 10:
                msg = MessageSegment.image(image_to_base64(text_to_image(msg.strip())))
        else:
            msg += '已经没有定数大于13.6的曲目了,加油清谱捏！\n'
    else:
        msg += f'恭喜{appellation}完成{match.group(1)}{match.group(2)}！'

    return msg

async def level_process_data(payload: dict, match: Match, nickname: Optional[str]) -> Union[MessageSegment, str]:
    song_played = []
    song_remain = []

    data = await get_player_data('plate', payload)

    if isinstance(data, str):
        return data

    if match.group(2).lower() in scoreRank:
        achievement = achievementList[scoreRank.index(match.group(2).lower()) - 1]
        for song in data['verlist']:
            if song['level'] == match.group(1) and song['achievements'] < achievement:
                song_remain.append([song['id'], song['level_index']])
            song_played.append([song['id'], song['level_index']])
    elif match.group(2).lower() in comboRank:
        combo_index = comboRank.index(match.group(2).lower())
        for song in data['verlist']:
            if song['level'] == match.group(1) and ((song['fc'] and combo_rank.index(song['fc']) < combo_index) or not song['fc']):
                song_remain.append([song['id'], song['level_index']])
            song_played.append([song['id'], song['level_index']])
    elif match.group(2).lower() in syncRank:
        sync_index = syncRank.index(match.group(2).lower())
        for song in data['verlist']:
            if song['level'] == match.group(1) and ((song['fs'] and sync_rank.index(song['fs']) < sync_index) or not song['fs']):
                song_remain.append([song['id'], song['level_index']])
            song_played.append([song['id'], song['level_index']])
    for music in mai.total_list:
        for i, lv in enumerate(music.level[2:]):
            if lv == match.group(1) and [int(music.id), i + 2] not in song_played:
                song_remain.append([int(music.id), i + 2])
    song_remain = sorted(song_remain, key=lambda i: int(i[1]))
    song_remain = sorted(song_remain, key=lambda i: int(i[0]))
    songs = []
    for song in song_remain:
        music = mai.total_list.by_id(str(song[0]))
        songs.append([music.id, music.title, diffs[song[1]], music.ds[song[1]], song[1]])

    appellation = nickname if nickname else '您'

    msg = ''
    if len(song_remain) > 0:
        if len(song_remain) < 50:
            song_record = [[s['id'], s['level_index']] for s in data['verlist']]
            msg += f'{appellation}的{match.group(1)}全谱面{match.group(2).upper()}剩余曲目如下：\n'
            for i, s in enumerate(sorted(songs, key=lambda i: i[3])):
                self_record = ''
                if [int(s[0]), s[-1]] in song_record:
                    record_index = song_record.index([int(s[0]), s[-1]])
                    if match.group(2).lower() in scoreRank:
                        self_record = str(data['verlist'][record_index]['achievements']) + '%'
                    elif match.group(2).lower() in comboRank:
                        if data['verlist'][record_index]['fc']:
                            self_record = comboRank[combo_rank.index(data['verlist'][record_index]['fc'])].upper()
                    elif match.group(2).lower() in syncRank:
                        if data['verlist'][record_index]['fs']:
                            self_record = syncRank[sync_rank.index(data['verlist'][record_index]['fs'])].upper()
                msg += f'No.{i + 1} {s[0]}. {s[1]} {s[2]} {s[3]} {self_record}'.strip() + '\n'
            if len(songs) > 10:
                msg = MessageSegment.image(image_to_base64(text_to_image(msg.strip())))
        else:
            msg = f'{appellation}还有{len(song_remain)}首{match.group(1)}曲目没有达成{match.group(2).upper()},加油推分捏！'
    else:
        msg = f'恭喜{appellation}达成{match.group(1)}全谱面{match.group(2).upper()}！'

    return msg

async def level_achievement_list_data(payload: dict, match: Match, nickname: Optional[str]) -> Union[MessageSegment, str]:
    song_list = []

    data = await get_player_data('plate', payload)

    if isinstance(data, str):
        return data

    for song in data['verlist']:
        if song['level'] == match.group(1):
            song_list.append(song)

    page = max(min(int(match.group(2)), len(song_list) // SONGS_PER_PAGE + 1), 1) if match.group(2) else 1

    appellation = nickname if nickname else '您'

    msg = f'{appellation}的{match.group(1)}分数列表（从高至低）：\n'
    for i, s in enumerate(sorted(song_list, key=lambda i: i['achievements'], reverse=True)):
        if (page - 1) * SONGS_PER_PAGE <= i < page * SONGS_PER_PAGE:
            m = mai.total_list.by_id(str(s['id']))
            msg += f'No.{i + 1} {s["achievements"]:.4f} {m.id}. {m.title} {diffs[s["level_index"]]} {m.ds[s["level_index"]]}'
            if s["fc"]: msg += f' {comboRank[combo_rank.index(s["fc"])].upper()}'
            if s["fs"]: msg += f' {syncRank[sync_rank.index(s["fs"])].upper()}'
            msg += '\n'
    msg += f'第{page}页，共{len(song_list) // SONGS_PER_PAGE + 1}页'

    return MessageSegment.image(image_to_base64(text_to_image(msg.strip())))

async def rating_ranking_data(name: Optional[str], page: Optional[int]) -> Union[MessageSegment, str]:

    rank_data = await get_rating_ranking_data()

    if isinstance(rank_data, str):
        return rank_data

    sorted_rank_data = sorted(rank_data, key=lambda r: r['ra'], reverse=True)
    if name:
        if name in [r['username'].lower() for r in sorted_rank_data]:
            rank_index = [r['username'].lower() for r in sorted_rank_data].index(name) + 1
            nickname = sorted_rank_data[rank_index - 1]['username']
            data = f'截止至 {time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())}\n玩家 {nickname} 在Diving Fish网站已注册用户ra排行第{rank_index}'
        else:
            data = '未找到该玩家'
    else:
        user_num = len(sorted_rank_data)
        msg = f'截止至 {time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())}，Diving Fish网站已注册用户ra排行：\n'
        if page * 50 > user_num:
            page = user_num // 50 + 1
        end = page * 50 if page * 50 < user_num else user_num
        for i, ranker in enumerate(sorted_rank_data[(page - 1) * 50:end]):
            msg += f'{i + 1 + (page - 1) * 50}. {ranker["username"]} {ranker["ra"]}\n'
        msg += f'第{page}页，共{user_num // 50 + 1}页'
        data = MessageSegment.image(image_to_base64(text_to_image(msg.strip())))

    return data

def modify(operate: str, arg: str, input_dict: dict) -> str:
    msg = ''
    if operate == 'add':
        if input_dict['name'] in [a['name'] for a in arcades]:
            return '该机厅已存在'
        else:
            arcades.append(input_dict)
            msg = f'添加了机厅：{input_dict["name"]}'
    elif operate == 'delete':
        if input_dict['name'] in [a['name'] for a in arcades]:
            arcades.remove(arcades[[a['name'] for a in arcades].index(input_dict['name'])])
            msg = f'删除了机厅：{input_dict["name"]}'
        else:
            return '无此机厅'
    elif operate == 'modify':
        MAX_CARDS = 30
        if arg == 'num':
            if input_dict['name'] in [a['name'] for a in arcades]:
                arcades[[a['name'] for a in arcades].index(input_dict['name'])]['num'] = int(input_dict['num'])
                msg = f'现在的机台数量：{input_dict["num"]}'
            else:
                return '无此机厅'
        elif arg == 'alias_add':
            for i_a in input_dict['alias']:
                for a in arcades:
                    if i_a in a['alias']:
                        return f'已存在别称：{i_a}'
            if input_dict['name'] in [a['name'] for a in arcades]:
                arcade = arcades[[a['name'] for a in arcades].index(input_dict['name'])]
                arcade['alias'] = list(set(arcade['alias'] + input_dict['alias']))
                msg = f'当前别称：{" ".join(arcade["alias"])}'
            else:
                return '无此机厅'
        elif arg == 'alias_delete':
            if input_dict['name'] in [a['name'] for a in arcades]:
                arcade = arcades[[a['name'] for a in arcades].index(input_dict['name'])]
                if input_dict['alias'] in arcade['alias']:
                    arcade['alias'].remove(input_dict['alias'])
                    if len(arcade['alias']) > 0:
                        msg = f'当前别称：{" ".join(arcade["alias"])}'
                    else:
                        msg = '当前该机厅没有别称'
                else:
                    return f'{arcade["name"]}无此别称'
            else:
                return '无此机厅'
        elif arg == 'subscribe':
            if input_dict['name'] in [a['name'] for a in arcades]:
                arcade = arcades[[a['name'] for a in arcades].index(input_dict['name'])]
                arcade['group'].append(input_dict['gid'])
                msg = f'订阅了机厅：{input_dict["name"]}'
            else:
                return '无此机厅'
        elif arg == 'unsubscribe':
            if input_dict['name'] in [a['name'] for a in arcades]:
                arcade = arcades[[a['name'] for a in arcades].index(input_dict['name'])]
                arcade['group'].remove(input_dict['gid'])
                msg = f'取消订阅了机厅：{input_dict["name"]}'
            else:
                return '无此机厅'
        elif arg == 'person_set':
            if input_dict['name'] in [a['name'] for a in arcades]:
                arcade = arcades[[a['name'] for a in arcades].index(input_dict['name'])]
                if abs(int(input_dict['person']) - arcade['person']) > MAX_CARDS:
                    return f'一次最多改变{MAX_CARDS}卡！'
                if int(input_dict['person']) == arcade["person"]:
                    return f'无变化，现在有{arcade["person"]}卡'
                arcade['person'] = int(input_dict['person'])
                arcade['time'] = input_dict['time']
                arcade['by'] = input_dict['by']
                msg = f'现在有{arcade["person"]}卡'
            else:
                return '无此机厅'
        elif arg == 'person_add':
            if input_dict['name'] in [a['name'] for a in arcades]:
                arcade = arcades[[a['name'] for a in arcades].index(input_dict['name'])]
                if int(input_dict['person']) > MAX_CARDS:
                    return f'一次最多改变{MAX_CARDS}卡！'
                if int(input_dict['person']) == 0:
                    return f'无变化，现在有{arcade["person"]}卡'
                arcade['person'] += int(input_dict['person'])
                arcade['time'] = input_dict['time']
                arcade['by'] = input_dict['by']
                msg = f'现在有{arcade["person"]}卡'
            else:
                return '无此机厅'
        elif arg == 'person_minus':
            if input_dict['name'] in [a['name'] for a in arcades]:
                arcade = arcades[[a['name'] for a in arcades].index(input_dict['name'])]
                if int(input_dict['person']) > MAX_CARDS:
                    return f'一次最多改变{MAX_CARDS}卡！'
                if int(input_dict['person']) == 0:
                    arcade['time'] = input_dict['time']
                    arcade['by'] = input_dict['by']
                    return f'无变化，现在有{arcade["person"]}卡'
                if arcade['person'] < int(input_dict['person']):
                    return f'现在{arcade["person"]}卡，不够减！'
                else:
                    arcade['person'] -= int(input_dict['person'])
                    arcade['time'] = input_dict['time']
                    arcade['by'] = input_dict['by']
                    msg = f'现在有{arcade["person"]}卡'
            else:
                return '无此机厅'
    else:
        return '内部错误，请联系维护组'
    try:
        with open(arcades_json, 'w', encoding='utf-8') as f:
            json.dump(arcades, f, ensure_ascii=False, indent=4)
    except Exception as e:
        traceback.print_exc()
        return f'操作失败，错误代码：{e}'
    return '修改成功！' + msg

def arcade_person_data(match: Match, gid: int, nickname: str) -> Union[str, bool]:
    result = None
    empty_name = False
    if match.group(1):
        if '人数' in match.group(1) or '卡' in match.group(1):
            search_key: str = match.group(1)[:-2] if '人数' in match.group(1) else match.group(1)[:-1]
            if search_key:
                for a in arcades:
                    if search_key.lower() == a['name']:
                        result = a
                        break
                    if search_key.lower() in a['alias']:
                        result = a
                        break
                if not result:
                    return '没有这样的机厅哦'
            else:
                empty_name = True
        else:
            for a in arcades:
                if match.group(1).lower() == a['name']:
                    result = a
                    break
                if match.group(1).lower() in a['alias']:
                    result = a
                    break
            if not result:
                return False
    else:
        return False
    if not result or empty_name:
        for a in arcades:
            if gid in a['group']:
                result = a
                break
    if result:
        msg = ''
        num = match.group(3) if match.group(3).isdigit() else 1
        if match.group(2) in ['设置', '设定', '＝', '=']:
            msg = modify('modify', 'person_set', {'name': result['name'], 'person': num,
                                                  'time': time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
                                                  'by': nickname})
        elif match.group(2) in ['增加', '添加', '加', '＋', '+']:
            msg = modify('modify', 'person_add', {'name': result['name'], 'person': num,
                                                  'time': time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
                                                  'by': nickname})
        elif match.group(2) in ['减少', '降低', '减', '－', '-']:
            msg = modify('modify', 'person_minus', {'name': result['name'], 'person': num,
                                                    'time': time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
                                                    'by': nickname})
        if msg and '一次最多改变' in msg:
            msg = '请勿乱玩bot，恼！'
    else:
        msg = '该群未订阅机厅，请发送 订阅机厅 <名称> 指令订阅机厅'

    return msg
