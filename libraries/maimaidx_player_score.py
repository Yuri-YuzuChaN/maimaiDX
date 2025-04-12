import random
import time
import traceback
from typing import Callable

import pyecharts.options as opts
from pyecharts.charts import Pie
from pyecharts.render import make_snapshot
from quart.utils import run_sync
from snapshot_phantomjs import snapshot

from hoshino.typing import MessageSegment

from .. import *
from .image import *
from .maimai_best_50 import ScoreBaseImage, changeColumnWidth, coloumWidth, computeRa
from .maimaidx_api_data import *
from .maimaidx_model import PlanInfo, PlayInfoDefault, PlayInfoDev, RaMusic
from .maimaidx_music import Music, mai

Filter = Tuple[
    List[PlayInfoDefault],
    List[PlayInfoDefault],
    List[PlayInfoDefault],
    List[PlayInfoDefault],
    List[PlayInfoDefault]
]
Condition = Callable[[PlayInfoDefault], bool]


async def music_global_data(music: Music, level_index: int) -> MessageSegment:
    """
    绘制曲目游玩详情
    
    Params:
        `music`: :class:Music
        `level_index`: 难度
    Returns:
        `MessageSegment`
    """
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
        title=f'{music.id} {music.title} 「{diffs[level_index]}」',
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


class DrawScore(ScoreBaseImage):
    
    def __init__(self, image: Image.Image = None) -> None:
        super().__init__(image)
        self._im.alpha_composite(self.aurora_bg)
        self._im.alpha_composite(self.shines_bg, (34, 0))
        self._im.alpha_composite(self.rainbow_bg, (319, self._im.size[1] - 643))
        self._im.alpha_composite(self.rainbow_bottom_bg, (100, self._im.size[1] - 343))
        for h in range((self._im.size[1] // 358) + 1):
            self._im.alpha_composite(self.pattern_bg, (0, (358 + 7) * h))

    def whilepic(self, data: List[RaMusic], y: int = 200):
        """
        循环绘制谱面
        
        Params:
            `data`: `谱面数据`
            `y`: `Y轴偏移`
        """
        dy = 65
        x = 0
        for n, v in enumerate(data):
            if n % 20 == 0:
                x = 55
                y += dy if n != 0 else 0
            else:
                x += 65
            cover = Image.open(music_picture(v.id)).resize((55, 55))
            self._im.alpha_composite(cover, (x, y))
            self._im.alpha_composite(self.id_diff[int(v.lv)], (x, y + 45))
            self._tb.draw(x + 27, y + 50, 10, v.id, self.t_color[int(v.lv)], 'mm')
    
    def whilerisepic(self, data: List[RiseScore], low_score: int, isdx: bool):
        """
        循环绘制上分推荐数据
        
        Params:
            `data`: `上分数据`
            `low_score`: `最低分`
            `isdx`: `是否DX版本`
        """
        y = 120
        for index, _d in enumerate(data):
            x = 200 if isdx else 700
            y += 140 if index != 0 else 0
            
            rate = Image.open(maimaidir / f'UI_TTR_Rank_{_d.rate}.png').resize((63, 28))
            
            self._im.alpha_composite(self._rise[_d.level_index], (x + 30, y))
            self._im.alpha_composite(Image.open(music_picture(_d.song_id)).resize((80, 80)), (x + 55, y + 40))
            self._im.alpha_composite(Image.open(maimaidir / f'{_d.type.upper()}.png').resize((60, 22)), (x + 240, y + 114))
            if _d.oldrate:
                oldrate = Image.open(maimaidir / f'UI_TTR_Rank_{_d.oldrate}.png').resize((63, 28))
                self._im.alpha_composite(oldrate, (x + 145, y + 82))
            self._im.alpha_composite(rate, (x + 305, y + 82))
            
            title = _d.title
            if coloumWidth(title) > 26:
                title = changeColumnWidth(title, 25) + '...'
            self._sy.draw(x + 142, y + 44, 17, title, self.t_color[_d.level_index], 'lm')
            self._tb.draw(x + 145, y + 124, 18, f'ID: {_d.song_id}', self.id_color[_d.level_index], 'lm')
            self._tb.draw(x + 210, y + 71, 25, f'{_d.oldachievements:.4f}%', self.t_color[_d.level_index], anchor='mm')
            self._tb.draw(x + 245, y + 96, 17, f'Ra: {_d.oldra}', self.t_color[_d.level_index], anchor='mm')
            self._tb.draw(x + 370, y + 71, 25, f'{_d.achievements:.4f}%', self.t_color[_d.level_index], anchor='mm')
            self._tb.draw(x + 415, y + 96, 17, f'Ra: {_d.ra}', self.t_color[_d.level_index], anchor='mm')
            self._tb.draw(x + 315, y + 124, 18, f'ds:{_d.ds}', self.id_color[_d.level_index], anchor='lm')
            if _d.oldra > low_score:
                new_ra = _d.ra - _d.oldra
            else:
                new_ra = _d.ra - low_score
            self._tb.draw(x + 390, y + 124, 18, f'Ra +{new_ra}', self.id_color[_d.level_index], 'lm')
         
    def draw_rise(self, sd: List[RiseScore], sd_score: int, dx: List[RiseScore], dx_score: int) -> Image.Image:
        """
        绘制上分数据表
        
        Params:
            `sd`: `旧版本谱面`
            `sd_score`: `旧版本最低分`
            `sd`: `新版本谱面`
            `dx_score`: `新版本最低分`
        Returns:
            `Image.Image`
        """
        title_bg = self.title_bg.copy().resize((273, 80))
        self._im.alpha_composite(title_bg, (314, 30))
        self._sy.draw(450, 68, 18, '旧版本谱面推荐', self.text_color, 'mm')
        self.whilerisepic(sd, sd_score, True)
        self._im.alpha_composite(title_bg, (814, 30))
        self._sy.draw(950, 68, 18, '新版本谱面推荐', self.text_color, 'mm')
        self.whilerisepic(dx, dx_score, False)
        
        height = self._im.size[1]
        self._im.alpha_composite(self.design_bg.resize((800, 72)), (300, height - 110))
        self._sy.draw(700, height - 76, 18, f'Designed by Yuri-YuzuChaN & BlueDeer233. Generated by {BOTNAME} BOT', self.text_color, 'mm')
        return self._im

    def draw_plan(
        self,
        completed: Union[List[PlayInfoDefault], List[PlayInfoDev]],
        completed_y: int,
        unfinished: Union[List[PlayInfoDefault], List[PlayInfoDev]],
        unfinished_y: int,
        notstarted: List[RaMusic],
        plan: str,
        completed_len: int
    ) -> Image.Image:
        """
        绘制进度表
        
        Params:
            `completed`: `已完成谱面`
            `completed_y`: `已完成谱面高度`
            `unfinished`: `未完成谱面`
            `unfinished_y`: `未完成谱面高度`
            `notstarted`: `未游玩谱面`
            `plan`: `目标`
            `completed_len`: `已完成谱面数量`
        Returns:
            `Image.Image`
        """
        max = len(completed + unfinished + notstarted)

        self._im.alpha_composite(self.title_lengthen_bg, (475, 30))
        self._im.alpha_composite(self.title_lengthen_bg, (475, 30 + completed_y))
        self._im.alpha_composite(self.title_lengthen_bg, (475, 30 + completed_y + unfinished_y))
        
        self._sy.draw(700, 77, 22, f'已完成谱面「{len(completed)}」个', self.text_color, 'mm')
        self._sy.draw(700, 77 + completed_y, 22, f'未完成谱面「{len(unfinished)}」个', self.text_color, 'mm')
        self._sy.draw(700, 77 + completed_y + unfinished_y, 22, f'未游玩谱面「{len(notstarted)}」个', self.text_color, 'mm')
        
        self.whiledraw(completed[:completed_len], True, 140)
        self.whiledraw(unfinished[:30], True, 140 + completed_y)
        self.whilepic(notstarted[:100], 140 + completed_y + unfinished_y)

        self._im.alpha_composite(self.design_bg, (200, self._im.size[1] - 113))
        pagemsg = f'共计「{max}」个谱面，剩余「{len(unfinished + notstarted)}」个谱面未完成「{plan.upper()}」'
        self._sy.draw(700, self._im.size[1] - 70, 25, pagemsg, self.text_color, 'mm')
        return self._im

    def draw_category(
        self, 
        category: str, 
        data: Union[List[PlayInfoDefault], List[PlayInfoDev], List[RaMusic]],
        page: int = 1, 
        end_page: int = 1
    ) -> Image.Image:
        """
        绘制指定进度表
        
        Params:
            `category`: `类别`
            `data`: `数据`
            `page`: `页数`
            `end_page`: `总页数`
        Returns:
            `Image.Image`
        """
        lendata = len(data)
        newdata = data[(page - 1) * 80: page * 80]
        self._im.alpha_composite(self.title_lengthen_bg, (475, 30))
        if category == 'completed' or category == 'unfinished':
            txt = '已完成' if category == 'completed' else '未完成'
            self._sy.draw(700, 77, 28, f'{txt}谱面', self.text_color, 'mm')
            self.whiledraw(newdata, True, 140)
            self._im.alpha_composite(self.design_bg, (200, self._im.size[1] - 113))
            
            pagemsg = f'{txt}谱面共计「{lendata}」个，'
            pagemsg += f'展示第「{(page - 1) * 80 + 1}-{80 * (page - 1) + len(newdata)}」个，'
            pagemsg += f'当前第「{page} / {end_page}」页'
            self._sy.draw(700, self._im.size[1] - 70, 25, pagemsg, self.text_color, 'mm')
        else:
            self._sy.draw(700, 77, 28, '未游玩谱面', self.text_color, 'mm')
            self.whilepic(data)
            self._im.alpha_composite(self.design_bg, (200, self._im.size[1] - 113))
            self._sy.draw(700, self._im.size[1] - 70, 25, f'未游玩谱面共计「{len(data)}」个', self.text_color, 'mm')
        return self._im
    
    def draw_scorelist(
        self, 
        rating: Union[str, float], 
        data: Union[List[PlayInfoDefault], List[PlayInfoDev]], 
        page: int = 1, 
        end_page: int = 1
    ) -> Image.Image:
        """
        绘制分数列表
        
        Params:
            `rating`: `定数`
            `data`: `数据`
            `page`: `页数`
            `end_page`: `总页数`
        Returns:
            `Image.Image`
        """
        lendata = len(data)
        newdata = data[(page - 1) * 80: page * 80]
        r = len(newdata) // 20 + (0 if len(newdata) % 20 == 0 else 1)
        for n in range(r):
            y = (109 * 4 + 140) * n
            self._im.alpha_composite(self.title_lengthen_bg, (475, 30 + y))
            start = (20 * n + 1) + 80 * (page - 1)
            self._sy.draw(700, 77 + y, 28, f'No.{start}- No.{start + len(newdata[n * 20: (n + 1) * 20]) - 1}', self.text_color, 'mm')
            self.whiledraw(newdata[n * 20: (n + 1) * 20], True, 140 + y)
        self._im.alpha_composite(self.design_bg, (200, self._im.size[1] - 113))
        
        pagemsg = f'「{rating}」共计「{lendata}」个成绩，'
        pagemsg += f'展示第「{(page - 1) * 80 + 1}-{80 * (page - 1) + len(newdata)}」个，'
        pagemsg += f'当前第「{page} / {end_page}」页'
        self._sy.draw(700, self._im.size[1] - 70, 25, pagemsg, self.text_color, 'mm')
        return self._im


def get_rise_score_list(
    old_records: Dict[int, Dict[str, Union[int, float]]],
    type: str, 
    info: List[ChartInfo], 
    level: Optional[str] = None, 
    score: Optional[int] = None
) -> Tuple[List[RiseScore], int]:
    """
    随机获取加分曲目
    
    Params:
        `type`: 版本
        `info`: 游玩成绩列表
        `level`: 等级
        `score`: 分数
    Returns:
        `Tuple[List[RiseScore], int]`
    """
    ignore = [m.song_id for m in info if m.achievements >= 100.5]
    ra = info[-1].ra
    music: List[RiseScore] = []
    if score is None:
        ss_ds = round(ra / 20.8, 1)
    else:
        ss_ds = round((ra + score) / 20.8, 1)
    sssp_ds = round(ra / 22.4, 1)
    ds = (sssp_ds + 0.1, ss_ds + 0.1)
    version = list(plate_to_version.values())[-2] if type == 'DX' else list(plate_to_version.values())[:-2]
    musiclist = mai.total_list.filter(level=level, ds=ds, version=version)
    for _m in musiclist:
        if (song_id := int(_m.id)) in ignore:
            continue
        if song_id >= 100000:
            continue
        for index in _m.diff:
            for r in achievementList[-4:]:
                basera, rate = computeRa(_m.ds[index], r, israte=True)
                if basera <= ra:
                    continue
                if score and basera - score < ra:
                    continue
                if song_id in old_records and old_records[song_id]['level_index'] == index:
                    oldra, oldrate = computeRa(_m.ds[index], old_records[song_id]['achievements'], israte=True)
                    if oldra >= basera:
                        continue
                    ss = RiseScore(
                        song_id=song_id,
                        title=_m.title,
                        type=_m.type,
                        level_index=index,
                        ds=_m.ds[index],
                        ra=basera,
                        rate=rate,
                        achievements=r,
                        oldra=oldra,
                        oldrate=oldrate,
                        oldachievements=old_records[song_id]['achievements']
                    )
                else:
                    ss = RiseScore(
                        song_id=song_id,
                        title=_m.title,
                        type=_m.type,
                        level_index=index,
                        ds=_m.ds[index],
                        ra=basera,
                        rate=rate,
                        achievements=r
                    )
                music.append(ss)
                break
    if not music:
        return music, 0
    new = random.sample(music, musiclen if 0 < (musiclen := len(musiclist)) < 5 else 5)
    new.sort(key=lambda x: x.song_id, reverse=True)
    return new, ra


async def rise_score_data(
    qqid: int, 
    username: Optional[str] = None, 
    level: Optional[str] = None, 
    score: Optional[int] = None
) -> Union[MessageSegment, str]:
    """
    上分数据
    
    Params:
        `qqid`: 用户QQ
        `username`: 查分器用户名
        `level`: 定数
        `score`: 分数
    Returns:
        `Union[Image.Image, str]`
    """
    try:
        user = await maiApi.query_user_b50(qqid=qqid, username=username)
        records = await maiApi.query_user_plate(qqid=qqid, username=username, version=list(plate_to_version.values()))
        old_records: Dict[int, Dict[str, Union[int, float]]] = {
            m.song_id: {
                'level_index': m.level_index,
                'achievements': m.achievements
            } for m in records
        }
        
        sd, sd_low_score = get_rise_score_list(old_records, 'SD', user.charts.sd, level, score)
        dx, dx_low_score = get_rise_score_list(old_records, 'DX', user.charts.dx, level, score)
        
        if not sd and not dx:
            return '没有推荐的铺面'
        
        lensd, lendx = len(sd), len(dx)
        
        h = max(lensd, lendx)
        height = h * 140 + 110 + 150
        image = tricolor_gradient(1400, height)
        
        ds = DrawScore(image)
        im = ds.draw_rise(sd, sd_low_score, dx, dx_low_score).crop((200, 0, 1200, height))
        
        msg = MessageSegment.image(image_to_base64(im))
    except (UserNotFoundError, UserNotExistsError, UserDisabledQueryError) as e:
        msg = str(e)
    except Exception as e:
        log.error(traceback.format_exc())
        msg = f'未知错误：{type(e)}\n请联系Bot管理员'
        
    return msg


def plate_message(
    result: str, 
    plan: str, 
    music_list: List[PlayInfoDefault], 
    played: List[Tuple[int, int]]
) -> Union[MessageSegment, str]:
    """
    Params:
        `result`: 结果
        `plan`: 目标
        `music_list`: 谱面列表
        `played`: 已游玩谱面
    Returns:
        `Union[MessageSegment, str]`
    """
    for n, m in enumerate(music_list):
        self_record = ''
        if (m.song_id, m.level_index) in played:
            if plan in ['将', '者']:
                self_record = f'{m.achievements}%'
            if plan in ['極', '极', '神']:
                self_record = m.fc
            if plan in '舞舞':
                self_record = m.fs
        result += f'No.{n + 1:02d} {f"「{m.song_id}」":>7} {f"「{diffs[m.level_index]}」":>11} 「{m.ds}」 {m.title}  {self_record}\n'
    if len(music_list) > 10:
        result = MessageSegment.image(image_to_base64(text_to_image(result.strip())))
    return result


async def player_plate_data(qqid: int, username: str, version: str, plan: str) -> Union[MessageSegment, str]:
    """
    查看牌子进度
    
    Params:
        `qqid`: 用户QQ
        `username`: 查分器用户名
        `version`: 版本
        `plan`: 目标
    Returns:
        `Union[MessageSegment, str]`
    """
    if version in platecn:
        version = platecn[version]
    if version == '真':
        ver = [plate_to_version['真']] + [plate_to_version['初']]
        _ver = version
    elif version in ['霸', '舞']:
        ver = list(set(_v for _v in list(plate_to_version.values())[:-9]))
        _ver = '舞'
    elif version in ['熊', '华', '華']:
        ver = [plate_to_version['熊']]
        _ver = '熊&华'
    elif version in ['爽', '煌']:
        ver = [plate_to_version['爽']]
        _ver = '爽&煌'
    elif version in ['宙', '星']:
        ver = [plate_to_version['宙']]
        _ver = '宙&星'
    elif version in ['祭', '祝']:
        ver = [plate_to_version['祭']]
        _ver = '祭&祝'
    elif version in ['双', '宴']:
        ver = [plate_to_version['双']]
        _ver = '双&宴'
    else:
        ver = [plate_to_version[version]]
        _ver = version
    
    try:
        verlist = await maiApi.query_user_plate(qqid=qqid, username=username, version=ver)
    except (UserNotFoundError, UserNotExistsError, UserDisabledQueryError) as e:
        return str(e)
    
    if plan in ['将', '者']:
        achievement = 100 if plan == '将' else 80
        callable_: Condition = lambda x: x.achievements < achievement
    elif plan in ['極', '极']:
        callable_: Condition = lambda x: not x.fc
    elif plan == '舞舞':
        callable_: Condition = lambda x: x.fs not in ['fsd', 'fsdp']
    elif plan  == '神':
        callable_: Condition = lambda x: x.fc not in ['ap', 'app']
    else:
        raise ValueError
    
    unfinished_model_list: Filter = ([], [], [], [], [])
    unfinished: List[Tuple[int, int]] = []
    played: List[Tuple[int, int]] = []
    remaster: List[int] = []
    
    # 已游玩未完成曲目
    plate_id_list = mai.total_plate_id_list[_ver]
    if version in ['舞', '霸']:
        remaster = mai.total_plate_id_list['舞ReMASTER']
        for music in verlist:
            if music.song_id not in plate_id_list:
                continue
            if music.level_index == 4 and music.song_id not in remaster:
                continue
            if callable_(music):
                unfinished.append((music.song_id, music.level_index))
            played.append((music.song_id, music.level_index))
    else:
        for music in verlist:
            if music.song_id not in plate_id_list:
                continue
            if callable_(music):
                unfinished.append((music.song_id, music.level_index))
            played.append((music.song_id, music.level_index))
    
    # 未游玩未完成曲目
    for music in mai.total_list:
        if int(music.id) not in plate_id_list:
            continue
        info = PlayInfoDefault(
            achievements=0,
            level='',
            level_index=0,
            title=music.title,
            type=music.type,
            id=int(music.id)
        )
        range_ = range(5 if version in ['舞', '霸'] and int(music.id) in remaster else 4)
        for level_index in range_:
            if (m := (info.song_id, level_index)) not in played or m in unfinished:
                _info = info.model_copy()
                _info.level = music.level[level_index]
                _info.ds = music.ds[level_index]
                _info.level_index = level_index
                unfinished_model_list[level_index].append(_info)

    basic, advanced, expert, master, re_master = unfinished_model_list
    
    ramain = basic + advanced + expert + master + re_master
    ramain.sort(key=lambda x: x.ds, reverse=True)
    difficult = [_m for _m in ramain if _m.ds > 13.6]

    appellation = username if username else '您'
    result = dedent(f'''\
        {appellation}的「{version}{plan}」剩余进度如下：
        Basic剩余「{len(basic)}」首
        Advanced剩余「{len(advanced)}」首
        Expert剩余「{len(expert)}」首
        Master剩余「{len(master)}」首
    ''')
    if version in ['舞', '霸']:
        result += f'Re:Master剩余「{len(re_master)}」首\n'
    
    if len(difficult) > 0:
        if len(difficult) < 60:
            result += '剩余定数大于13.6的曲目：\n'
            result = plate_message(result, plan, difficult, played)
        else:
            result += f'还有{len(difficult)}首大于13.6定数的曲目，加油推分捏！\n'
    elif len(ramain) > 0:
        if len(ramain) < 60:
            result += '剩余曲目：\n'
            result = plate_message(result, plan, ramain, played)
        else:
            result += '已经没有定数大于13.6的曲目了，加油清谱捏！\n'
    else:
        result = f'已经没有剩余的的曲目了，恭喜{appellation}完成「{version}{plan}」！'
    return result


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
) -> Union[MessageSegment, str]:
    """
    查看谱面等级进度

    Params:
        `qqid`: 用户QQ
        `username`: 查分器用户名
        `level`: 定数
        `plan`: 评价等级
    Returns:
        `Union[MessageSegment, str]`
    """
    try:
        if maiApi.token:
            devobj = await maiApi.query_user_get_dev(qqid=qqid, username=username)
            obj = devobj.records
        else:
            version = list(set(_v for _v in list(plate_to_version.values())))
            obj = await maiApi.query_user_plate(qqid=qqid, username=username, version=version)
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
        else:
            raise
        
        for _d in obj:
            if isinstance(_d, PlayInfoDefault):
                _m = mai.total_list.by_id(_d.song_id)
                ds: float = _m.ds[_d.level_index]
                a: float = _d.achievements
                ra, rate = computeRa(ds, a, israte=True)
                _d.ra = ra
                _d.rate = rate
            if (song_id := str(_d.song_id)) in music and _d.level == level:
                if isinstance(music[song_id], Dict):
                    music[song_id][_d.level_index] = PlanInfo()
                    _p = music[song_id][_d.level_index]
                else:
                    music[song_id] = PlanInfo()
                    _p = music[song_id]
                
                if (plannum == 0 and _d.achievements >= planlist[plannum]) or \
                    (plannum == 1 and _d.fc and combo_rank.index(_d.fc) >= planlist[plannum]) or \
                    (plannum == 2 and _d.fs and (sync_rank.index(_d.fs) >= planlist[plannum] if _d.fs and _d.fs in sync_rank else sync_rank_p.index(_d.fs) >= planlist[plannum])):
                    _p.completed = _d
                else:
                    _p.unfinished = _d

        notplayed: List[RaMusic] = []
        completed: Union[List[PlayInfoDefault], List[PlayInfoDev]] = []
        unfinished: Union[List[PlayInfoDefault], List[PlayInfoDev]] = []
        for m in music:
            play = music[m]
            if isinstance(play, Dict):
                for index, p in play.items():
                    if isinstance(p, RaMusic):
                        notplayed.append(p)
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
                notplayed.append(play)
        completed.sort(key=lambda x: x.achievements if plannum == 0 else x.fc if plannum == 1 else x.fs, reverse=True)
        unfinished.sort(key=lambda x: x.achievements if plannum == 0 else x.fc if plannum == 1 else x.fs, reverse=True)
        notplayed.sort(key=lambda x: x.ds, reverse=True)

        if category == 'default':
            completed_len = 60 if len(unfinished) == 0 and len(notplayed) == 0 else 30
            clen = len(completed[:completed_len])
            completed_y = (clen // 5 + (0 if clen % 5 == 0 else 1)) * 109 + 140
            ulen = len(unfinished[:30])
            unfinished_y = (ulen // 5 + (0 if ulen % 5 == 0 else 1)) * 109 + 140
            nlen = len(notplayed[:100])
            notstarted_y = (nlen // 20 + (0 if nlen % 20 == 0 else 1)) * 65 + 140
            image = tricolor_gradient(1400, 150 + completed_y + unfinished_y + notstarted_y)
            dp = DrawScore(image)
            im = dp.draw_plan(completed, completed_y, unfinished, unfinished_y, notplayed, plan, completed_len)
        elif category == 'completed' or category == 'unfinished':
            data = completed if category == 'completed' else unfinished
            lendata = len(data)
            end_page_num = lendata // 80 + 1
            if page > end_page_num:
                return f'超出页数，您的成绩共计「{end_page_num}」页，请重新输入'
            topage = len(data[(page - 1) * 80: page * 80])
            plc = (topage // 5 + (0 if topage % 5 == 0 else 1)) * 109
            image = tricolor_gradient(1400, 240 + plc + 120)
            dp = DrawScore(image)
            im = dp.draw_category(category, data, page, end_page_num)
        else:
            lennotstarted = len(notplayed)
            pln = (lennotstarted // 20 + (0 if lennotstarted % 20 == 0 else 1)) * 65
            image = tricolor_gradient(1400, 240 + pln + 120)
            dp = DrawScore(image)
            im = dp.draw_category(category, notplayed)
        
        msg = MessageSegment.image(image_to_base64(im))
    except (UserNotFoundError, UserNotExistsError, UserDisabledQueryError) as e:
        msg = str(e)
    except Exception as e:
        log.error(traceback.format_exc())
        msg = f'未知错误：{type(e)}\n请联系Bot管理员'
    return msg


async def level_achievement_list_data(
    qqid: int, 
    username: Optional[str], 
    rating: Union[str, float], 
    page: int = 1
) -> Union[MessageSegment, str]:
    """
    查看分数列表

    Params:
        `qqid` : 用户QQ
        `username` : 查分器用户名
        `rating` : 定数
        `page` : 页数
        `nickname` : 用户昵称
    Returns:
        `Union[MessageSegment, str]
    """
    try:
        data: Union[List[PlayInfoDefault], List[PlayInfoDev]] = []
        if maiApi.token:
            obj = await maiApi.query_user_get_dev(qqid=qqid, username=username)
            data = obj.records
        else:
            version = list(set(_v for _v in list(plate_to_version.values())))
            obj = await maiApi.query_user_plate(qqid=qqid, username=username, version=version)
            for _d in obj:
                music = mai.total_list.by_id(_d.song_id)
                _d.ds = music.ds[_d.level_index]
                _d.ra, _d.rate = computeRa(_d.ds, _d.achievements, israte=True)
            data = obj

        if isinstance(rating, str):
            newdata = sorted(list(filter(lambda x: x.level == rating, data)), key=lambda z: z.achievements, reverse=True)
        else:
            newdata = sorted(list(filter(lambda x: x.ds == rating, data)), key=lambda z: z.achievements, reverse=True)
        
        lendata = len(newdata)
        end_page_num = lendata // 80 + 1
        if page > end_page_num:
            return f'超出页数，您的成绩共计「{end_page_num}」页，请重新输入'
        
        topage = len(newdata[(page - 1) * 80: page * 80])
        line = topage // 5 + (0 if topage % 5 == 0 else 1)
        if page < end_page_num:
            plc = line * 109 + 140 * 4
        elif topage <= 20:
            plc = 4 * 109 + 140
        elif topage <= 40:
            plc = line * 109 + 140 * 2
        elif topage <= 60:
            plc = line * 109 + 140 * 3
        else:
            plc = line * 109 + 140 * 4
        
        image = tricolor_gradient(1400, 150 + plc)

        sc = DrawScore(image)
        im = sc.draw_scorelist(rating, newdata, page, end_page_num)
        msg = MessageSegment.image(image_to_base64(im))
    except (UserNotFoundError, UserNotExistsError, UserDisabledQueryError) as e:
        msg = str(e)
    except Exception as e:
        log.error(traceback.format_exc())
        msg = f'未知错误：{type(e)}\n请联系Bot管理员'
    return msg


async def rating_ranking_data(name: str, page: int) -> Union[MessageSegment, str]:
    """
    查看查分器排行榜
    
    Params:
        `name`: 指定用户名
        `page`: 页数
    Returns:
        `Union[MessageSegment, str]`
    """
    try:
        rank_data = await maiApi.rating_ranking()

        _time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        if name != '':
            if name in [r.username.lower() for r in rank_data]:
                rank_index = [r.username.lower() for r in rank_data].index(name) + 1
                nickname = rank_data[rank_index - 1].username
                data = f'截止至 {_time}\n玩家 {nickname} 在查分器已注册用户ra排行第{rank_index}'
            else:
                data = '未找到该玩家'
        else:
            user_num = len(rank_data)
            msg = f'截止至 {_time}，查分器已注册用户ra排行：\n'
            if page * 50 > user_num:
                page = user_num // 50 + 1
            end = page * 50 if page * 50 < user_num else user_num
            for i, ranker in enumerate(rank_data[(page - 1) * 50:end]):
                msg += f'No.{i + 1 + (page - 1) * 50:02d}.「{ranker.ra}」 {ranker.username} \n'
            msg += f'第「{page}」页，共「{user_num // 50 + 1}」页'
            data = MessageSegment.image(image_to_base64(text_to_image(msg.strip())))
    except Exception as e:
        log.error(traceback.format_exc())
        data = f'未知错误：{type(e)}\n请联系Bot管理员'
    return data