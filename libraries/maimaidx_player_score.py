import time
import traceback
from textwrap import dedent
from typing import Optional

import pyecharts.options as opts
from pyecharts.charts import Pie
from pyecharts.render import make_snapshot
from quart.utils import run_sync
from snapshot_phantomjs import snapshot

from hoshino.typing import MessageSegment

from .. import *
from .image import *
from .maimai_best_50 import Draw, computeRa, generateAchievementList
from .maimaidx_api_data import maiApi
from .maimaidx_error import *
from .maimaidx_model import Music, PlanInfo, PlayInfoDefault, PlayInfoDev, RaMusic
from .maimaidx_music import mai

realAchievementList = {}
for acc in [i / 10 for i in range(10, 151)]:
    realAchievementList[f'{acc:.1f}'] = generateAchievementList(acc)


async def music_global_data(music: Music, level_index: int) -> MessageSegment:
    """指令 `Ginfo`，查看当前谱面游玩详情"""
    stats = music.stats[level_index]
    fc_data_pair = [list(z) for z in zip([c.upper() if c else 'Not FC' for c in [''] + comboRank], stats.fc_dist)]
    acc_data_pair = [list(z) for z in zip([s.upper() for s in scoreRank], stats.dist)]

    initopts = opts.InitOpts(width='1000px', height='800px', bg_color='#fff', js_host='./')
    labelopts = opts.LabelOpts(
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
    titleopts = opts.TitleOpts(
        title=f'{music.id} {music.title} {diffs[level_index]}',
        pos_left='center',
        pos_top='20',
        title_textstyle_opts=opts.TextStyleOpts(color='#2c343c'),
    )
    legendopts = opts.LegendOpts(pos_left=15, pos_top=10, orient='vertical')

    pie = Pie(initopts)
    pie.add('全连等级', fc_data_pair, radius=[0, '30%'], label_opts=labelopts)
    pie.add('达成率等级', acc_data_pair, radius=['50%', '70%'], is_clockwise=True, label_opts=labelopts)
    pie.set_global_opts(title_opts=titleopts, legend_opts=legendopts)
    pie.set_series_opts(tooltip_opts=opts.TooltipOpts(trigger='item', formatter='{a} <br/>{b}: {c} ({d}%)'))
    pie.render(str(static / 'temp_pie.html'))
    await run_sync(make_snapshot)(snapshot, str(static / 'temp_pie.html'), str(static / 'temp_pie.png'), is_remove_html=False)

    im = Image.open(static / 'temp_pie.png')
    return MessageSegment.image(image_to_base64(im))


async def rise_score_data(qqid: int, username: Optional[str], rating: str, score: str) -> str:
    """
    上分数据
    
    - `qqid` : 用户QQ
    - `username` : 查分器用户名
    - `rating` : 定数
    - `score` : 分数
    - `nickname` : 用户昵称
    """
    try:
        dx_ra_lowest = 999
        sd_ra_lowest = 999
        player_dx_list = []
        player_sd_list = []
        music_dx_list: List[List[Union[Music, str, float, int]]] = []
        music_sd_list: List[List[Union[Music, str, float, int]]] = []

        player_data = await maiApi.query_user('player', qqid=qqid, username=username)

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
                    if rating and music.level[i] != rating: continue
                    if f'{achievement:.1f}' == '100.5':
                        index_score = 12
                    else:
                        index_score = [index for index, acc in enumerate(achievementList[:-1]) if acc <= achievement < achievementList[index + 1]][0]
                    if music.basic_info.is_new:
                        music_ra = computeRa(ds, achievement)
                        if music_ra < dx_ra_lowest: continue
                        if [int(music.id), i] in player_dx_id_list:
                            player_ra = player_dx_list[player_dx_id_list.index([int(music.id), i])][2]
                            if music_ra - player_ra == int(score) and [int(music.id), i, music_ra] not in player_dx_list:
                                music_dx_list.append([music, diffs[i], ds, achievement, scoreRank[index_score + 1].upper(), music_ra])
                        else:
                            if music_ra - dx_ra_lowest == int(score) and [int(music.id), i, music_ra] not in player_dx_list:
                                music_dx_list.append([music, diffs[i], ds, achievement, scoreRank[index_score + 1].upper(), music_ra])
                    else:
                        music_ra = computeRa(ds, achievement)
                        if music_ra < sd_ra_lowest: continue
                        if [int(music.id), i] in player_sd_id_list:
                            player_ra = player_sd_list[player_sd_id_list.index([int(music.id), i])][2]
                            if music_ra - player_ra == int(score) and [int(music.id), i, music_ra] not in player_sd_list:
                                music_sd_list.append([music, diffs[i], ds, achievement, scoreRank[index_score + 1].upper(), music_ra])
                        else:
                            if music_ra - sd_ra_lowest == int(score) and [int(music.id), i, music_ra] not in player_sd_list:
                                music_sd_list.append([music, diffs[i], ds, achievement, scoreRank[index_score + 1].upper(), music_ra])

        if len(music_dx_list) == 0 and len(music_sd_list) == 0:
            return '没有找到这样的乐曲'

        appellation = username if username else '您'
        result = ''
        if len(music_sd_list) != 0:
            result += f'为{appellation}推荐以下标准乐曲：\n'
            for music, diff, ds, achievement, rank, ra in sorted(music_sd_list, key=lambda i: int(i[0].id)):
                result += f'{music.id}. {music.title} {diff} {ds} {achievement} {rank} {ra}\n'
        if len(music_dx_list) != 0:
            result += f'\n为{appellation}推荐以下new乐曲：\n'
            for music, diff, ds, achievement, rank, ra in sorted(music_dx_list, key=lambda i: int(i[0].id)):
                result += f'{music.id}. {music.title} {diff} {ds} {achievement} {rank} {ra}\n'
                
        msg = MessageSegment.image(image_to_base64(text_to_image(result.strip())))
    except UserNotFoundError as e:
        msg = str(e)
    except UserDisabledQueryError as e:
        msg = str(e)
    except Exception as e:
        log.error(traceback.format_exc())
        msg = f'未知错误：{type(e)}\n请联系Bot管理员'
        
    return msg


async def player_plate_data(qqid: int, username: Optional[str], ver: str, plan: str) -> str:
    """
    查看牌子进度
    
    - `qqid` : 用户QQ
    - `username` : 查分器用户名
    - `ver` : 版本
    - `plan` : 目标
    - `nickname` : 用户昵称
    """
    try:
        song_played = []
        song_remain_basic = []
        song_remain_advanced = []
        song_remain_expert = []
        song_remain_master = []
        song_remain_re_master = []
        song_remain_difficult = []
        
        if ver in ['霸', '舞']:
            version = list(set(_v for _v in list(plate_to_version.values())[:-9]))
        elif ver == '真':
            version = list(set(_v for _v in list(plate_to_version.values())[0:2]))
        elif ver == '华':
            version = [plate_to_version['熊']]
        elif ver == '星':
            version = [plate_to_version['宙']]
        elif ver == '祝':
            version = [plate_to_version['祭']]
        else:
            version = [plate_to_version[ver]]
        data = await maiApi.query_user('plate', qqid=qqid, username=username, version=version)
        
        if ver == '真':
            verlist = list(filter(lambda x: x['title'] != 'ジングルベル', data['verlist']))
        else:
            verlist = data['verlist']

        if plan in ['将', '者']:
            for song in verlist:
                if song['level_index'] == 0 and song['achievements'] < (100.0 if plan == '将' else 80.0):
                    song_remain_basic.append([song['id'], song['level_index']])
                if song['level_index'] == 1 and song['achievements'] < (100.0 if plan == '将' else 80.0):
                    song_remain_advanced.append([song['id'], song['level_index']])
                if song['level_index'] == 2 and song['achievements'] < (100.0 if plan == '将' else 80.0):
                    song_remain_expert.append([song['id'], song['level_index']])
                if song['level_index'] == 3 and song['achievements'] < (100.0 if plan == '将' else 80.0):
                    song_remain_master.append([song['id'], song['level_index']])
                if ver in ['舞', '霸'] and song['level_index'] == 4 and song['achievements'] < (100.0 if plan == '将' else 80.0):
                    song_remain_re_master.append([song['id'], song['level_index']])
                song_played.append([song['id'], song['level_index']])
        elif plan in ['極', '极']:
            for song in verlist:
                if song['level_index'] == 0 and not song['fc']:
                    song_remain_basic.append([song['id'], song['level_index']])
                if song['level_index'] == 1 and not song['fc']:
                    song_remain_advanced.append([song['id'], song['level_index']])
                if song['level_index'] == 2 and not song['fc']:
                    song_remain_expert.append([song['id'], song['level_index']])
                if song['level_index'] == 3 and not song['fc']:
                    song_remain_master.append([song['id'], song['level_index']])
                if ver == '舞' and song['level_index'] == 4 and not song['fc']:
                    song_remain_re_master.append([song['id'], song['level_index']])
                song_played.append([song['id'], song['level_index']])
        elif plan == '舞舞':
            for song in verlist:
                if song['level_index'] == 0 and song['fs'] not in ['fsd', 'fsdp']:
                    song_remain_basic.append([song['id'], song['level_index']])
                if song['level_index'] == 1 and song['fs'] not in ['fsd', 'fsdp']:
                    song_remain_advanced.append([song['id'], song['level_index']])
                if song['level_index'] == 2 and song['fs'] not in ['fsd', 'fsdp']:
                    song_remain_expert.append([song['id'], song['level_index']])
                if song['level_index'] == 3 and song['fs'] not in ['fsd', 'fsdp']:
                    song_remain_master.append([song['id'], song['level_index']])
                if ver == '舞' and song['level_index'] == 4 and song['fs'] not in ['fsd', 'fsdp']:
                    song_remain_re_master.append([song['id'], song['level_index']])
                song_played.append([song['id'], song['level_index']])
        elif plan == '神':
            for song in verlist:
                if song['level_index'] == 0 and song['fc'] not in ['ap', 'app']:
                    song_remain_basic.append([song['id'], song['level_index']])
                if song['level_index'] == 1 and song['fc'] not in ['ap', 'app']:
                    song_remain_advanced.append([song['id'], song['level_index']])
                if song['level_index'] == 2 and song['fc'] not in ['ap', 'app']:
                    song_remain_expert.append([song['id'], song['level_index']])
                if song['level_index'] == 3 and song['fc'] not in ['ap', 'app']:
                    song_remain_master.append([song['id'], song['level_index']])
                if ver == '舞' and song['level_index'] == 4 and song['fc'] not in ['ap', 'app']:
                    song_remain_re_master.append([song['id'], song['level_index']])
                song_played.append([song['id'], song['level_index']])
        for music in mai.total_list:
            if music.id in ignore_music:
                continue
            if music.basic_info.version in version:
                if [int(music.id), 0] not in song_played:
                    song_remain_basic.append([int(music.id), 0])
                if [int(music.id), 1] not in song_played:
                    song_remain_advanced.append([int(music.id), 1])
                if [int(music.id), 2] not in song_played:
                    song_remain_expert.append([int(music.id), 2])
                if [int(music.id), 3] not in song_played:
                    song_remain_master.append([int(music.id), 3])
                if ver in ['舞', '霸'] and len(music.level) == 5 and [int(music.id), 4] not in song_played:
                    song_remain_re_master.append([int(music.id), 4])
        song_remain_basic = sorted(song_remain_basic, key=lambda i: int(i[0]))
        song_remain_advanced = sorted(song_remain_advanced, key=lambda i: int(i[0]))
        song_remain_expert = sorted(song_remain_expert, key=lambda i: int(i[0]))
        song_remain_master = sorted(song_remain_master, key=lambda i: int(i[0]))
        song_remain_re_master = sorted(song_remain_re_master, key=lambda i: int(i[0]))
        for song in song_remain_basic + song_remain_advanced + song_remain_expert + song_remain_master + song_remain_re_master:
            music = mai.total_list.by_id(str(song[0]))
            if int(music.id) < 100000:      # 跳过宴谱id
                if music.ds[song[1]] > 13.6:
                    song_remain_difficult.append([music.id, music.title, diffs[song[1]], music.ds[song[1]], song[1]])

        appellation = username if username else '您'

        msg = dedent(f'''\
            {appellation}的{ver}{plan}剩余进度如下：
            Basic剩余{len(song_remain_basic)}首
            Advanced剩余{len(song_remain_advanced)}首
            Expert剩余{len(song_remain_expert)}首
            Master剩余{len(song_remain_master)}首
        ''')
        song_remain: List[List] = song_remain_basic + song_remain_advanced + song_remain_expert + song_remain_master + song_remain_re_master
        song_record = [[s['id'], s['level_index']] for s in verlist]
        fs = ['fsd', 'fdx', 'fsdp', 'fdxp']
        if ver in ['舞', '霸']:
            msg += f'Re:Master剩余{len(song_remain_re_master)}首\n'
        if len(song_remain_difficult) > 0:
            if len(song_remain_difficult) < 60:
                msg += '剩余定数大于13.6的曲目：\n'
                for i, s in enumerate(sorted(song_remain_difficult, key=lambda i: i[3])):
                    self_record = ''
                    if [int(s[0]), s[-1]] in song_record:
                        record_index = song_record.index([int(s[0]), s[-1]])
                        if plan in ['将', '者']:
                            self_record = str(verlist[record_index]['achievements']) + '%'
                        elif plan in ['極', '极', '神']:
                            if fc := verlist[record_index]['fc']:
                                self_record = comboRank[combo_rank.index(fc)].upper()
                        elif plan == '舞舞':
                            if (sync := verlist[record_index]['fs']) and sync in fs:
                                self_record = syncRank[sync_rank.index(sync)].upper()
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
                        if plan in ['将', '者']:
                            self_record = str(verlist[record_index]['achievements']) + '%'
                        elif plan in ['極', '极', '神']:
                            if verlist[record_index]['fc']:
                                self_record = comboRank[combo_rank.index(verlist[record_index]['fc'])].upper()
                        elif plan == '舞舞':
                            if verlist[record_index]['fs']:
                                self_record = syncRank[sync_rank.index(verlist[record_index]['fs'])].upper()
                    msg += f'No.{i + 1} {m.id}. {m.title} {diffs[s[1]]} {m.ds[s[1]]} {self_record}'.strip() + '\n'
                if len(song_remain) > 10:
                    msg = MessageSegment.image(image_to_base64(text_to_image(msg.strip())))
            else:
                msg += '已经没有定数大于13.6的曲目了,加油清谱捏！\n'
        else:
            msg = f'已经没有剩余的的曲目了，恭喜{appellation}完成{ver}{plan}！'
    except UserNotFoundError as e:
        msg = str(e)
    except UserDisabledQueryError as e:
        msg = str(e)
    except Exception as e:
        log.error(traceback.format_exc())
        msg = f'未知错误：{type(e)}\n请联系Bot管理员'
    return msg


class DrawPlan(Draw):
    bg_color = [(111, 212, 61, 255), (248, 183, 9, 255), (255, 129, 141, 255), (159, 81, 220, 255),
                (219, 170, 255, 255)]
    diff = [Image.new('RGBA', (75, 75), color) for color in bg_color]

    def image_crop(height: int) -> Image.Image:
        """
        - `height`: 图片高度

        返回 `Image` 对象
        """
        bg = Image.open(maimaidir / 'buddies_bg_2.png').convert('RGBA').resize((2200, 3667))
        bg_w, bg_h = bg.size
        y = bg_h - height
        im = bg.crop((0, y, bg_w, bg_h))
        return im

    async def whilepic(self, data: List[RaMusic], y: int = 200):
        dy = 85
        x = 0
        for n, v in enumerate(data):
            if n % 20 == 0:
                x = 280
                y += dy if n != 0 else 0
            else:
                x += 85
            cover = Image.open(await maiApi.download_music_pictrue(v.id))
            if (lv := int(v.lv)) != 3:
                cover_bg = self.diff[lv]
                cover_bg.alpha_composite(cover.resize((65, 65)), (5, 5))
            else:
                cover_bg = cover.resize((75, 75))
            self._im.alpha_composite(cover_bg, (x, y))

    async def draw_plan(
        self,
        completed: Union[List[PlayInfoDefault], List[PlayInfoDev]],
        clen: int,
        unfinished: Union[List[PlayInfoDefault], List[PlayInfoDev]],
        ulen: int,
        notstarted: List[RaMusic],
        plan: str
    ) -> Image.Image:
        max = len(completed + unfinished + notstarted)

        self._im.alpha_composite(self.title_bg, (800, 50))
        self._sy.draw(1100, 105, 30, f'已完成数量 「{len(completed)}」 个', (247, 75, 75, 255), 'mm')
        await self.whiledraw(completed[:30], True, 200)

        self._im.alpha_composite(self.title_bg, (800, 280 + clen))
        self._sy.draw(1100, 335 + clen, 30, f'未完成数量 「{len(unfinished)}」 个', (247, 75, 75, 255), 'mm')
        await self.whiledraw(unfinished[:30], True, 430 + clen)

        self._im.alpha_composite(self.title_bg, (800, 510 + clen + ulen))
        self._sy.draw(1100, 565 + clen + ulen, 30, f'未游玩数量 「{len(notstarted)}」 个', (247, 75, 75, 255), 'mm')
        await self.whilepic(notstarted[:100], 660 + clen + ulen)

        self._im.alpha_composite(self.design_bg, (440, self._im.size[1] - 197))
        pagemsg = f'共计「{max}」个谱面，剩余「{len(unfinished + notstarted)}」个谱面未完成「{plan.upper()}」'
        self._sy.draw(1100, self._im.size[1] - 140, 35, pagemsg, (5, 100, 150, 255), 'mm')
        return self._im

    async def draw_category(
        self, 
        category: str, 
        data: Union[List[PlayInfoDefault], List[PlayInfoDev], List[RaMusic]],
        page: int = 1, 
        end_page: int = 1
    ) -> Image.Image:
        lendata = len(data)
        newdata = data[(page - 1) * 80: page * 80]
        self._im.alpha_composite(self.title_bg, (800, 50))
        if category == 'completed' or category == 'unfinished':
            txt = '已完成' if category == 'completed' else '未完成'
            self._sy.draw(1100, 105, 36, f'{txt}谱面', (247, 75, 75, 255), 'mm')
            await self.whiledraw(newdata, True, 200)
            self._im.alpha_composite(self.design_bg, (440, self._im.size[1] - 197))
            pagemsg = f'{txt}谱面共计「{lendata}」个，展示第「{(page - 1) * 80 + 1}-{80 * (page - 1) + len(newdata)}」个，当前第「{page} / {end_page}」页'
            self._sy.draw(1100, self._im.size[1] - 140, 35, pagemsg, (5, 100, 150, 255), 'mm')
        else:
            self._sy.draw(1100, 105, 36, '未游玩谱面', (247, 75, 75, 255), 'mm')
            await self.whilepic(data)
            self._im.alpha_composite(self.design_bg, (440, self._im.size[1] - 197))
            self._sy.draw(1100, self._im.size[1] - 140, 35, f'未游玩谱面共计「{len(data)}」个', (5, 100, 150, 255), 'mm')
        return self._im


def calc(data: dict) -> Union[PlayInfoDefault, PlayInfoDev]:
    if not maiApi.token:
        _m = mai.total_list.by_id(data['id'])
        ds: float = _m.ds[data['level_index']]
        a: float = data['achievements']
        ra, rate = computeRa(ds, a, israte=True)
        info = PlayInfoDefault(**data, ds=ds, ra=ra, rate=rate)
    else:
        info = PlayInfoDev(**data)
    return info


async def level_process_data(
    qqid: int, 
    username: Optional[str], 
    level: str, 
    plan: str, 
    category: str = 'default', 
    page: int = 1
) -> Union[str, Image.Image]:
    """
    查看谱面等级进度

    - `qqid` : 用户QQ
    - `username` : 查分器用户名
    - `level` : 定数
    - `plan` : 评价等级
    """
    try:
        if maiApi.token:
            obj = (await maiApi.query_user_dev(qqid=qqid, username=username))['records']
        else:
            version = list(set(_v for _v in list(plate_to_version.values())))
            obj = (await maiApi.query_user('plate', qqid=qqid, username=username, version=version))['verlist']
        music = mai.total_list.by_plan(level)

        planlist = [0, 0, 0]
        plannum = 0
        if plan.lower() in scoreRank:
            plannum = 0
            planlist[0] = achievementList[scoreRank.index(plan.lower()) - 1]
        elif plan.lower() in comboRank:
            plannum = 1
            planlist[1] = comboRank.index(plan.lower())
        elif plan.lower() in syncRank:
            plannum = 2
            planlist[2] = syncRank.index(plan.lower())

        for _d in obj:
            info = calc(_d)
            if (song_id := str(info.song_id)) in music and info.level == level:
                if isinstance(music[song_id], Dict):
                    music[song_id][info.level_index] = PlanInfo()
                    _p = music[song_id][info.level_index]
                else:
                    music[song_id] = PlanInfo()
                    _p = music[song_id]
                if (plannum == 0 and info.achievements >= planlist[plannum]) \
                        or (plannum == 1 and info.fc and combo_rank.index(info.fc) >= planlist[plannum]) \
                        or (plannum == 2 and info.fs and (sync_rank.index(info.fs) >= planlist[plannum] if info.fs and info.fs in sync_rank else sync_rank_p.index(info.fs) >= planlist[plannum])):
                    _p.completed = info
                else:
                    _p.unfinished = info

        notstarted: List[RaMusic] = []
        completed: Union[List[PlayInfoDefault], List[PlayInfoDev]] = []
        unfinished: Union[List[PlayInfoDefault], List[PlayInfoDev]] = []
        for m in music:
            play = music[m]
            if isinstance(play, Dict):
                for index, p in play.items():
                    if isinstance(p, RaMusic):
                        notstarted.append(p)
                    elif p.completed:
                        completed.append(p.completed)
                    elif p.unfinished:
                        unfinished.append(p.unfinished)
            elif isinstance(play, PlanInfo):
                if play.completed:
                    completed.append(play.completed)
                if play.unfinished:
                    unfinished.append(play.unfinished)
            else:
                notstarted.append(play)

        completed.sort(key=lambda x: x.achievements if plannum == 0 else x.fc if plannum == 1 else x.fs, reverse=True)
        unfinished.sort(key=lambda x: x.achievements if plannum == 0 else x.fc if plannum == 1 else x.fs, reverse=True)
        notstarted.sort(key=lambda x: x.ds, reverse=True)

        if category == 'default':
            clen = len(completed[:30])
            completed_Y = (clen // 5 + (0 if clen % 5 == 0 else 1)) * 160
            ulen = len(unfinished[:30])
            unfinished_Y = (ulen // 5 + (0 if ulen % 5 == 0 else 1)) * 160
            nlen = len(notstarted[:100])
            notstarted_Y = (nlen // 20 + (0 if nlen % 20 == 0 else 1)) * 85
            image = DrawPlan.image_crop(660 + completed_Y + unfinished_Y + notstarted_Y + 225)
            dp = DrawPlan(image)
            im = await dp.draw_plan(completed, completed_Y, unfinished, unfinished_Y, notstarted, plan)
        elif category == 'completed' or category == 'unfinished':
            data = completed if category == 'completed' else unfinished
            lendata = len(data)
            end_page_num = lendata // 80 + 1
            if page > end_page_num:
                return '超出页数，请重新输入'
            topage = len(data[(page - 1) * 80: page * 80])
            plc = (topage // 5 + (0 if topage % 5 == 0 else 1)) * 160
            image = DrawPlan.image_crop(350 + plc + 225)
            dp = DrawPlan(image)
            im = await dp.draw_category(category, data, page, end_page_num)
        else:
            lennotstarted = len(notstarted)
            pln = (lennotstarted // 20 + (0 if lennotstarted % 20 == 0 else 1)) * 85
            image = DrawPlan.image_crop(350 + pln + 225)
            dp = DrawPlan(image)
            im = await dp.draw_category(category, notstarted)

        msg = MessageSegment.image(image_to_base64(im.resize((1400, int(im.size[1] * round(1400 / 2200, 2))))))
    except UserNotFoundError as e:
        msg = str(e)
    except UserDisabledQueryError as e:
        msg = str(e)
    except Exception as e:
        log.error(traceback.format_exc())
        msg = f'未知错误：{type(e)}\n请联系Bot管理员'
    return msg


class DrawScoreList(Draw):
    fix_num = 80

    def image_crop(num: int) -> Image.Image:
        """
        - `height`: 图片高度

        返回元组 `(缩放图片, 坐标x, 坐标y)`
        """
        bg = Image.open(maimaidir / 'buddies_bg_2.png').convert('RGBA').resize((2200, 3667))
        bg_w, bg_h = bg.size
        fix_height = 350
        score_height = 165 * 5 * num
        bg_height = fix_height + score_height
        y = bg_h - bg_height
        im = bg.crop((0, y, bg_w, bg_h))
        return im

    async def draw_scorelist(self, data: Union[List[PlayInfoDefault], List[PlayInfoDev]], page: int,
                             end_page: int) -> Image.Image:
        datalen = len(data)
        newdata = data[(page - 1) * self.fix_num: page * self.fix_num]
        size = self._im.size
        r = len(newdata) // 20 + (0 if len(newdata) % 20 == 0 else 1)
        for n in range(r):
            y = 210 * 4 * n
            self._im.alpha_composite(self.title_bg, (800, 50 + y))
            start = (20 * n + 1) + self.fix_num * (page - 1)
            self._tb.draw(1100, 105 + y, 50, f'No.{start} - No.{start + len(newdata[n * 20: (n + 1) * 20]) - 1}', (247, 75, 75, 255), 'mm')
            await self.whiledraw(newdata[n * 20: (n + 1) * 20], True, 200 + y)
        pagemsg = f'共计「{datalen}」个成绩，展示第「{(page - 1) * self.fix_num + 1}-{self.fix_num * (page - 1) + len(newdata)}」个，当前第「{page} / {end_page}」页'
        self._im.alpha_composite(self.design_bg, (440, size[1] - 217))
        self._sy.draw(1100, size[1] - 160, 35, pagemsg, (5, 100, 150, 255), 'mm')
        return self._im


async def level_achievement_list_data(
    qqid: int, 
    username: Optional[str], 
    rating: Union[str, float], 
    page: int = 1
) -> Union[str, Image.Image]:
    """
    查看分数列表

    - `qqid` : 用户QQ
    - `username` : 查分器用户名
    - `rating` : 定数
    - `page` : 页数
    - `nickname` : 用户昵称
    """
    try:
        data: Union[List[PlayInfoDefault], List[PlayInfoDev]] = []
        if maiApi.token:
            obj = await maiApi.query_user_dev(qqid=qqid, username=username)
            data = [PlayInfoDev(**_d) for _d in obj['records']]
        else:
            version = list(set(_v for _v in list(plate_to_version.values())))
            obj = await maiApi.query_user('plate', qqid=qqid, username=username, version=version)
            for _d in obj['verlist']:
                music = mai.total_list.by_id(_d['id'])
                ds: float = music.ds[_d['level_index']]
                a: float = _d['achievements']
                ra, rate = computeRa(ds, a, israte=True)
                data.append(PlayInfoDefault(**_d, ds=ds, ra=ra, rate=rate))

        if isinstance(rating, str):
            newdata = sorted(list(filter(lambda x: x.level == rating, data)), key=lambda z: z.achievements, reverse=True)
        else:
            newdata = sorted(list(filter(lambda x: x.ds == rating, data)), key=lambda z: z.achievements, reverse=True)
        data_num = len(newdata)
        end_page_num = data_num // DrawScoreList.fix_num + 1
        remainder = data_num % DrawScoreList.fix_num
        if page > end_page_num:
            return '超出页数，请重新输入'

        if page < end_page_num:
            image = DrawScoreList.image_crop(4)
        elif remainder <= 20:
            image = DrawScoreList.image_crop(1)
        elif remainder <= 40:
            image = DrawScoreList.image_crop(2)
        elif remainder <= 60:
            image = DrawScoreList.image_crop(3)
        else:
            image = DrawScoreList.image_crop(4)

        sc = DrawScoreList(image)
        im = await sc.draw_scorelist(newdata, page, end_page_num)
        msg = MessageSegment.image(image_to_base64(im.resize((1400, int(im.size[1] * round(1400 / 2200, 2))))))
    except UserNotFoundError as e:
        msg = str(e)
    except UserDisabledQueryError as e:
        msg = str(e)
    except Exception as e:
        log.error(traceback.format_exc())
        msg = f'未知错误：{type(e)}\n请联系Bot管理员'
    return msg


async def rating_ranking_data(name: Optional[str], page: Optional[int]) -> str:
    """
    查看查分器排行榜
    
    - `name`: 指定用户名
    - `page`: 页数
    """
    try:
        rank_data = await maiApi.rating_ranking()

        sorted_rank_data = sorted(rank_data, key=lambda r: r['ra'], reverse=True)
        _time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        if name:
            if name in [r['username'].lower() for r in sorted_rank_data]:
                rank_index = [r['username'].lower() for r in sorted_rank_data].index(name) + 1
                nickname = sorted_rank_data[rank_index - 1]['username']
                data = f'截止至 {_time}\n玩家 {nickname} 在Diving Fish网站已注册用户ra排行第{rank_index}'
            else:
                data = '未找到该玩家'
        else:
            user_num = len(sorted_rank_data)
            msg = f'截止至 {_time}，Diving Fish网站已注册用户ra排行：\n'
            if page * 50 > user_num:
                page = user_num // 50 + 1
            end = page * 50 if page * 50 < user_num else user_num
            for i, ranker in enumerate(sorted_rank_data[(page - 1) * 50:end]):
                msg += f'{i + 1 + (page - 1) * 50}. {ranker["username"]} {ranker["ra"]}\n'
            msg += f'第{page}页，共{user_num // 50 + 1}页'
            data = MessageSegment.image(image_to_base64(text_to_image(msg.strip())))
    except Exception as e:
        log.error(traceback.format_exc())
        data = f'未知错误：{type(e)}\n请联系Bot管理员'
    return data