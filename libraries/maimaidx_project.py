from typing import Optional, Union
from re import Match
from PIL import Image, ImageDraw
from hoshino.typing import MessageSegment
from hoshino.config import NICKNAME

from .maimai_best_50 import *
from .maimaidx_api_data import *
from .maimaidx_music import MusicList, mai, get_cover_len4_id
from .image import *
from .. import static

import time, traceback, io

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

newdir = os.path.join(static, 'mai', 'new')
meiryo = os.path.join(static, 'meiryo.ttc')
meiryob = os.path.join(static, 'meiryob.ttc')
category = {
    'POPSアニメ': 'anime',
    'maimai': 'maimai',
    'niconicoボーカロイド': 'niconico',
    '東方Project': 'touhou',
    'ゲームバラエティ': 'game',
    'オンゲキCHUNITHM': 'ongeki'
}

async def download_music_pictrue(id: Union[int, str]) -> io.BytesIO:
    try:
        async with aiohttp.request('GET', f"https://www.diving-fish.com/covers/{get_cover_len4_id(id)}.png") as req:
            data = await req.read()
        return io.BytesIO(data)
    except:
        return os.path.join(static, 'mai', 'cover', '0000.png')

async def draw_music_info(music: MusicList) -> MessageSegment:
    im = Image.new('RGBA', (800, 1000))
    genre = category[music['basic_info']['genre']]

    music_bg = Image.open(os.path.join(newdir, 'music_bg.png')).convert('RGBA')
    cover = Image.open(await download_music_pictrue(music['id'])).convert('RGBA').resize((500, 500))
    anime = Image.open(os.path.join(newdir, f'{genre}.png')).convert('RGBA')
    anime_bg = Image.open(os.path.join(newdir, f'{genre}_bg.png')).convert('RGBA')
    music_title = Image.open(os.path.join(newdir, 'music_title.png')).convert('RGBA')
    diff = Image.open(os.path.join(newdir, 'diff.png')).convert('RGBA').resize((530, 79))
    line = Image.open(os.path.join(newdir, 'line.png')).convert('RGBA').resize((793, 14))
    verbpm = Image.open(os.path.join(newdir, 'ver&bpm.png')).convert('RGBA')

    im.alpha_composite(music_bg)
    im.alpha_composite(music_title, (52, 14))
    im.alpha_composite(anime_bg, (142, 175))
    im.alpha_composite(cover, (150, 183))
    im.alpha_composite(anime, (200, 135))
    im.alpha_composite(line, (5, 785))
    im.alpha_composite(diff, (135, 810))
    im.alpha_composite(verbpm, (50, 915))

    fontd = ImageDraw.Draw(im)

    font = DrawText(fontd, meiryo)
    font2 = DrawText(fontd, meiryob)

    font2.draw(270, 170, 28, music['id'], anchor='mm')
    font.draw_partial_opacity(400, 710, 20, music['basic_info']['artist'], anchor='mm')
    font.draw_partial_opacity(400, 750, 38, music['title'], anchor='mm')
    for n, i in enumerate(list(map(str, music["ds"]))):
        if n == 4:
            x = 615
            color = (195, 70, 231, 255)
        else:
            x = 190 + 105 * n
            color = (255, 255, 255, 255)
        font2.draw(x, 850, 28, i, color, anchor='mm')

    font.draw_partial_opacity(240, 940, 20, f'Ver:{music["basic_info"]["from"]}', anchor='mm')
    font.draw_partial_opacity(580, 940, 20, f'BPM:{music["basic_info"]["bpm"]}', anchor='mm')

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
        return None
    
    player_data.sort(key=lambda a: a['level_index'])
    music = mai.total_list.by_id(song)
    diffnum = len(music.ds)

    im = Image.new('RGBA', (1000, 1500))
    bg = Image.open(os.path.join(newdir, 'musicscore.png')).convert('RGBA')
    genre = Image.open(os.path.join(newdir, f'Score-{category[music.genre]}.png')).convert('RGBA')
    cover = Image.open(await download_music_pictrue(music.id)).convert('RGBA').resize((300, 300))
    ver = Image.open(os.path.join(newdir, f'{music.type}.png')).convert('RGBA').resize((140, 52))

    im.alpha_composite(bg)
    im.alpha_composite(genre, (45, 181))
    im.alpha_composite(cover, (60, 240))
    im.alpha_composite(ver, (800, 488))

    fontd = ImageDraw.Draw(im)
    font = DrawText(fontd, meiryo)
    fontb = DrawText(fontd, meiryob)

    if len(music.title) > 20:
        title = f'{music.title[:19]}...'
    else:
        title = music.title

    fontb.draw(515, 225, 28, song, anchor='mm')
    font.draw(380, 300, 40, title, (0, 0, 0, 255), 'lm')
    font.draw(380, 340, 20, f'Artist: {music.artist}', (0, 0, 0, 255), 'lm')
    font.draw(380, 400, 30, f'BPM: {music.bpm}', (0, 0, 0, 255), 'lm')
    font.draw(380, 450, 30, f'Version: {music.version}', (0, 0, 0, 255), 'lm')

    num = 0
    for z in range(diffnum):
        if z < 3:
            x = 305 * z
            xl = [i + x for i in [90, 195, 250, 90, 90, 195]]
            yl = [835, 730, 790, 815, 925]
        else:
            x = 330 * (z - 3)
            xl = [i + x for i in [230, 335, 390, 230, 230, 335]]
            yl = [1240, 1135, 1195, 1220, 1330]
        if z == 4:
            color = (103, 20, 141, 255)
        else:
            color = (255, 255, 255, 255)
        try:
            if z == player_data[num]['level_index']:
                _data = player_data[num]
                
                ds = music.ds[_data['level_index']]
                ra, rate = computeRa(ds, _data['achievements'], israte=True)

                rank = Image.open(os.path.join(static, 'mai', 'pic', f'UI_GAM_Rank_{rate}.png'))
                im.alpha_composite(rank, (xl[0], yl[0]))
                if _data['fc']:
                    fcl = {'fc': 'FC', 'fcp': 'FCp', 'ap': 'AP', 'app': 'APp'}
                    fc = Image.open(os.path.join(static, 'mai', 'pic', f'UI_MSS_MBase_Icon_{fcl[_data["fc"]]}.png')).convert('RGBA')
                    im.alpha_composite(fc, (xl[1], yl[0]))
                if _data['fs']:
                    fsl = {'fs': 'FS', 'fsp': 'FSp', 'fsd': 'FSD', 'fsdp': 'FSDp'}
                    fs = Image.open(os.path.join(static, 'mai', 'pic', f'UI_MSS_MBase_Icon_{fsl[_data["fs"]]}.png')).convert('RGBA')
                    im.alpha_composite(fs, (xl[2], yl[0]))

                p, s = f'{_data["achievements"]:.4f}'.split('.')
                r = fontb.get_box(p, 40)
                fontb.draw(xl[1], yl[1], 30, f'Base: {ds}', color, 'mm')
                fontb.draw(xl[3], yl[2], 40, p, color, 'lm')
                fontb.draw(xl[4] + r[2], yl[3], 27, f'.{s}%', color, 'ld')
                fontb.draw(xl[5], yl[4], 25, f'Rating: {ra}', color, 'mm')

                num += 1
            else:
                fontb.draw(xl[1], yl[3], 60, 'なし', color, 'mm')
        except IndexError:
            fontb.draw(xl[1], yl[3], 60, 'なし', color, 'mm')
    
    if diffnum != 5:
        font.draw(665, 1230, 50, '難易度\nなし', (103, 20, 141, 255), anchor='mm', multiline=True)
    
    fontb.draw(500, 1475, 25, f'Generated by {NICKNAME if isinstance(NICKNAME, str) else list(NICKNAME)[0]} Bot', anchor='mm')
    msg = MessageSegment.image(image_to_base64(im))

    return msg

async def query_chart_data(match: Match) -> str:
    if match.group(1) != '':
        try:
            level_index = level_labels.index(match.group(1))
            level_name = ['Basic', 'Advanced', 'Expert', 'Master', 'Re: MASTER']
            name = match.group(2)
            music = mai.total_list.by_id(name)
            chart = music['charts'][level_index]
            stats = music['stats'][level_index]
            ds = music['ds'][level_index]
            level = music['level'][level_index]
            if len(chart['notes']) == 4:
                result = f'''{level_name[level_index]} {level}({ds})
TAP: {chart['notes'][0]}
HOLD: {chart['notes'][1]}
SLIDE: {chart['notes'][2]}
BREAK: {chart['notes'][3]}
谱师: {chart['charter']}
难易度参考: {stats['tag'] if 'tag' in stats else '无'}'''
            else:
                result = f'''{level_name[level_index]} {level}({ds})
TAP: {chart['notes'][0]}
HOLD: {chart['notes'][1]}
SLIDE: {chart['notes'][2]}
TOUCH: {chart['notes'][3]}
BREAK: {chart['notes'][4]}
谱师: {chart['charter']}
难易度参考: {stats['tag'] if 'tag' in stats else '无'}'''

            msg = f'''{music["id"]}. {music["title"]}
{MessageSegment.image(f"https://www.diving-fish.com/covers/{get_cover_len4_id(music['id'])}.png")}
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

def aliases(name: str, match: Match) -> str:
    titles = []
    music = None
    if name.isdigit() and name not in ['9', '135']:
        music = mai.total_list.by_id(name)
        if music:
            titles = mai.music_aliases[music.title.lower()]
    if not titles:
        if name not in mai.music_aliases and not music:
            return '未找到此歌曲'
        elif name in mai.music_aliases:
            titles = mai.music_aliases[name]
    if len(titles) > 1:
        return '匹配到多首曲目，请缩小搜索范围'

    addition: str = match.group(4).strip()
    if match.group(2) in ['删除', '删去', '去除']:
        if len(titles) == 0 or addition.lower() not in mai.music_aliases_reverse[titles[0]][1:]:
            data = f'该曲目无此别称'
        else:
            for i, l in enumerate(mai.music_aliases_lines):
                if titles[0] in l:
                    mai.music_aliases_lines[i] = mai.music_aliases_lines[i].replace(f'\t{addition}', '')
                    mai.music_aliases_reverse[titles[0]].remove(addition)
                    break
            mai.save_aliases(''.join(mai.music_aliases_lines))
            msg = '\n'.join(mai.music_aliases_reverse[titles[0]][1:])
            data = f'操作成功，{titles[0]}有以下别名：\n{msg}'
    elif match.group(2) in ['添加', '增加', '增添']:
        if len(titles) == 0:
            music = mai.total_list.by_id(name)
            mai.save_aliases(''.join(mai.music_aliases_lines) + f'\n{music.title}\t{addition}')
            msg = '\n'.join(mai.music_aliases_reverse[music.title][1:])
            data = f'操作成功，{music.title}有以下别名：\n{msg}'
        else:
            if addition.lower() in mai.music_aliases_reverse[titles[0]][1:]:
                data = f'{titles[0]}已有别名{addition}'
            else:
                for i, l in enumerate(mai.music_aliases_lines):
                    if titles[0] in l:
                        ending = '\n' if l[-1] == '\n' else ''
                        mai.music_aliases_lines[i] = f'{l.strip()}\t{addition}{ending}'
                        mai.music_aliases_reverse[titles[0]].append(addition)
                        break
                mai.save_aliases(''.join(mai.music_aliases_lines))
                msg = '\n'.join(mai.music_aliases_reverse[titles[0]][1:])
                data = f'操作成功，{titles[0]}有以下别名：\n{msg}'
    
    return data

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
                            music_dx_list.append([music, diffs[i], ds, achievement, scoreRank[index_score + 1].upper(), music_ra, music.stats[i].difficulty])
                    else:
                        if music_ra - dx_ra_lowest == int(match.group(2)) and [int(music.id), i, music_ra] not in player_dx_list:
                            music_dx_list.append([music, diffs[i], ds, achievement, scoreRank[index_score + 1].upper(), music_ra, music.stats[i].difficulty])
                else:
                    music_ra = computeRa(ds, achievement)
                    if music_ra < sd_ra_lowest: continue
                    if [int(music.id), i] in player_sd_id_list:
                        player_ra = player_sd_list[player_sd_id_list.index([int(music.id), i])][2]
                        if music_ra - player_ra == int(match.group(2)) and [int(music.id), i, music_ra] not in player_sd_list:
                            music_sd_list.append([music, diffs[i], ds, achievement, scoreRank[index_score + 1].upper(), music_ra, music.stats[i].difficulty])
                    else:
                        if music_ra - sd_ra_lowest == int(match.group(2)) and [int(music.id), i, music_ra] not in player_sd_list:
                            music_sd_list.append([music, diffs[i], ds, achievement, scoreRank[index_score + 1].upper(), music_ra, music.stats[i].difficulty])

    if len(music_dx_list) == 0 and len(music_sd_list) == 0:
        return '没有找到这样的乐曲'
    elif len(music_dx_list) + len(music_sd_list) > 60:
        return f'结果过多({len(music_dx_list) + len(music_sd_list)} 条)，请缩小查询范围。'

    appellation = nickname if nickname else '您'
    msg = ''
    if len(music_sd_list) != 0:
        msg += f'为{appellation}推荐以下标准乐曲：\n'
        for music, diff, ds, achievement, rank, ra, difficulty in sorted(music_sd_list, key=lambda i: int(i[0]['id'])):
            msg += f'{music["id"]}. {music["title"]} {diff} {ds} {achievement} {rank} {ra} {difficulty}\n'
    if len(music_dx_list) != 0:
        msg += f'\n为{appellation}推荐以下2021乐曲：\n'
        for music, diff, ds, achievement, rank, ra, difficulty in sorted(music_dx_list, key=lambda i: int(i[0]['id'])):
            msg += f'{music["id"]}. {music["title"]} {diff} {ds} {achievement} {rank} {ra} {difficulty}\n'

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
            song_remain_difficult.append([music.id, music.title, diffs[song[1]], music.ds[song[1]], music.stats[song[1]].difficulty, song[1]])

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
                msg += f'No.{i + 1} {s[0]}. {s[1]} {s[2]} {s[3]} {s[4]} {self_record}'.strip() + '\n'
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
                msg += f'No.{i + 1} {m.id}. {m.title} {diffs[s[1]]} {m.ds[s[1]]} {m.stats[s[1]].difficulty} {self_record}'.strip() + '\n'
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
        songs.append([music.id, music.title, diffs[song[1]], music.ds[song[1]], music.stats[song[1]].difficulty, song[1]])

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
                msg += f'No.{i + 1} {s[0]}. {s[1]} {s[2]} {s[3]} {s[4]} {self_record}'.strip() + '\n'
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
    if match.group(2): page = max(min(int(match.group(2)), len(song_list) // SONGS_PER_PAGE + 1), 1)
    else: page = 1

    appellation = nickname if nickname else '您'

    msg = f'{appellation}的{match.group(1)}分数列表（从高至低）：\n'
    for i, s in enumerate(sorted(song_list, key=lambda i: i['achievements'], reverse=True)):
        if (page - 1) * SONGS_PER_PAGE <= i < page * SONGS_PER_PAGE:
            m = mai.total_list.by_id(str(s['id']))
            msg += f'No.{i + 1} {s["achievements"]:.4f} {m.id}. {m.title} {diffs[s["level_index"]]} {m.ds[s["level_index"]]} {m.stats[s["level_index"]].difficulty}'
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