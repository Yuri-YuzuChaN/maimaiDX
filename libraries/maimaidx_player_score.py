import os
import time
from re import Match
from typing import Optional, Union

import pyecharts.options as opts
from PIL import Image
from pyecharts.charts import Pie
from pyecharts.render import make_snapshot
from quart.utils import run_sync
from snapshot_phantomjs import snapshot

from hoshino.typing import MessageSegment

from .. import *
from .image import *
from .maimai_best_50 import computeRa, generateAchievementList
from .maimaidx_api_data import *
from .maimaidx_music import Music, mai

realAchievementList = {}
for acc in [i / 10 for i in range(10, 151)]:
    realAchievementList[f'{acc:.1f}'] = generateAchievementList(acc)


async def music_global_data(music: Music, level_index: int) -> Union[str, MessageSegment, None]:
    """
    指令 `Ginfo`，查看当前谱面游玩详情
    """
    stats = music.stats[level_index]
    fc_data_pair = [list(z) for z in zip([c.upper() if c else 'Not FC' for c in [''] + comboRank], stats.fc_dist)]
    acc_data_pair = [list(z) for z in zip([s.upper() for s in scoreRank], stats.dist)]

    Pie(
        init_opts=opts.InitOpts(
            width='1000px',
            height='800px',
            bg_color='#fff',
            js_host='./'
        )
    ).add(
        series_name='全连等级',
        data_pair=fc_data_pair,
        radius=[0, '30%'],
        label_opts=opts.LabelOpts(
            position='outside',
            formatter='{a|{a}}{abg|}\n{hr|}\n {b|{b}: }{c}  {per|{d}%}  ',
            background_color='#eee',
            border_color='#aaa',
            border_width=1,
            border_radius=4,
            rich={
                'a': {'color': '#999', 'lineHeight': 22, 'align': 'center'},
                'abg': {
                    'backgroundColor': '#e3e3e3',
                    'width': '100%',
                    'align': 'right',
                    'height': 22,
                    'borderRadius': [4, 4, 0, 0],
                },
                'hr': {
                    'borderColor': '#aaa',
                    'width': '100%',
                    'borderWidth': 0.5,
                    'height': 0,
                },
                'b': {'fontSize': 16, 'lineHeight': 33},
                'per': {
                    'color': '#eee',
                    'backgroundColor': '#334455',
                    'padding': [2, 4],
                    'borderRadius': 2,
                },
            },
        )
    ).add(
        series_name='达成率等级',
        data_pair=acc_data_pair,
        radius=['50%', '70%'],
        is_clockwise=True,
        label_opts=opts.LabelOpts(
            position='outside',
            formatter='{a|{a}}{abg|}\n{hr|}\n {b|{b}: }{c}  {per|{d}%}  ',
            background_color='#eee',
            border_color='#aaa',
            border_width=1,
            border_radius=4,
            rich={
                'a': {'color': '#999', 'lineHeight': 22, 'align': 'center'},
                'abg': {
                    'backgroundColor': '#e3e3e3',
                    'width': '100%',
                    'align': 'right',
                    'height': 22,
                    'borderRadius': [4, 4, 0, 0],
                },
                'hr': {
                    'borderColor': '#aaa',
                    'width': '100%',
                    'borderWidth': 0.5,
                    'height': 0,
                },
                'b': {'fontSize': 16, 'lineHeight': 33},
                'per': {
                    'color': '#eee',
                    'backgroundColor': '#334455',
                    'padding': [2, 4],
                    'borderRadius': 2,
                },
            },
        )
    ).set_global_opts(
        title_opts=opts.TitleOpts(
            title=f'{music.id} {music.title} {diffs[level_index]}',
            pos_left='center',
            pos_top='20',
            title_textstyle_opts=opts.TextStyleOpts(color='#2c343c'),
        ),
        legend_opts=opts.LegendOpts(
            pos_left=15,
            pos_top=10,
            orient='vertical'
        )
    ).set_series_opts(
        tooltip_opts=opts.TooltipOpts(
            trigger='item', formatter='{a} <br/>{b}: {c} ({d}%)'
        )
    ).render(os.path.join(static, 'temp_pie.html'))
    await run_sync(make_snapshot)(snapshot, os.path.join(static, 'temp_pie.html'), os.path.join(static, 'temp_pie.png'), is_remove_html=False)

    im = Image.open(os.path.join(static, 'temp_pie.png'))
    msg = MessageSegment.image(image_to_base64(im))

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
    music_dx_list: List[List[Union[Music, str, float, int]]] = []
    music_sd_list: List[List[Union[Music, str, float, int]]] = []

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
                if match.group(1) and music.level[i] != match.group(1): continue
                if f'{achievement:.1f}' == '100.5':
                    index_score = 12
                else:
                    index_score = [index for index, acc in enumerate(achievementList[:-1]) if acc <= achievement < achievementList[index + 1]][0]
                if music.basic_info.is_new:
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

    appellation = nickname if nickname else '您'
    msg = ''
    if len(music_sd_list) != 0:
        msg += f'为{appellation}推荐以下标准乐曲：\n'
        for music, diff, ds, achievement, rank, ra in sorted(music_sd_list, key=lambda i: int(i[0].id)):
            msg += f'{music.id}. {music.title} {diff} {ds} {achievement} {rank} {ra}\n'
    if len(music_dx_list) != 0:
        msg += f'\n为{appellation}推荐以下new乐曲：\n'
        for music, diff, ds, achievement, rank, ra in sorted(music_dx_list, key=lambda i: int(i[0].id)):
            msg += f'{music.id}. {music.title} {diff} {ds} {achievement} {rank} {ra}\n'

    return MessageSegment.image(image_to_base64(text_to_image(msg.strip())))


async def player_plate_data(payload: dict, match: Match, nickname: Optional[str]) -> Union[MessageSegment, str]:
    """
    查看将牌
    """
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
    
    if match.group(1) == '真':
        verlist = list(filter(lambda x: x['title'] != 'ジングルベル', data['verlist']))
    else:
        verlist = data['verlist']

    if match.group(2) in ['将', '者']:
        for song in verlist:
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
        for song in verlist:
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
        for song in verlist:
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
        for song in verlist:
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
        if match.group(1) == '真' and music.title == 'ジングルベル':
            continue
        if music.basic_info.version in payload['version']:
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
    song_record = [[s['id'], s['level_index']] for s in verlist]
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
                        self_record = str(verlist[record_index]['achievements']) + '%'
                    elif match.group(2) in ['極', '极', '神']:
                        if verlist[record_index]['fc']:
                            self_record = comboRank[combo_rank.index(verlist[record_index]['fc'])].upper()
                    elif match.group(2) == '舞舞':
                        if verlist[record_index]['fs']:
                            self_record = syncRank[sync_rank.index(verlist[record_index]['fs'])].upper()
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
                        self_record = str(verlist[record_index]['achievements']) + '%'
                    elif match.group(2) in ['極', '极', '神']:
                        if verlist[record_index]['fc']:
                            self_record = comboRank[combo_rank.index(verlist[record_index]['fc'])].upper()
                    elif match.group(2) == '舞舞':
                        if verlist[record_index]['fs']:
                            self_record = syncRank[sync_rank.index(verlist[record_index]['fs'])].upper()
                msg += f'No.{i + 1} {m.id}. {m.title} {diffs[s[1]]} {m.ds[s[1]]} {self_record}'.strip() + '\n'
            if len(song_remain) > 10:
                msg = MessageSegment.image(image_to_base64(text_to_image(msg.strip())))
        else:
            msg += '已经没有定数大于13.6的曲目了,加油清谱捏！\n'
    else:
        msg += f'恭喜{appellation}完成{match.group(1)}{match.group(2)}！'

    return msg


async def level_process_data(payload: dict, match: Match, nickname: Optional[str]) -> Union[MessageSegment, str]:
    """
    查看谱面等级进度
    """
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
    """
    查看分数列表
    """
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
    """
    查看查分器排行榜
    """
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