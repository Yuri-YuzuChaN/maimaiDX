import io
import math
import os
from typing import Dict, List, Optional, Tuple, Union

import aiohttp
from hoshino.typing import MessageSegment
from PIL import Image, ImageDraw, ImageFont

from .. import BOTNAME, static
from .image import image_to_base64
from .maimaidx_api_data import get_player_data
from .maimaidx_music import get_cover_len4_id, mai

scoreRank = ['d', 'c', 'b', 'bb', 'bbb', 'a', 'aa', 'aaa', 's', 's+', 'ss', 'ss+', 'sss', 'sss+']
comboRank = ['fc', 'fc+', 'ap', 'ap+']
combo_rank = ['fc', 'fcp', 'ap', 'app']
syncRank = ['fs', 'fs+', 'fdx', 'fdx+']
sync_rank = ['fs', 'fsp', 'fsd', 'fsdp']
diffs = ['Basic', 'Advanced', 'Expert', 'Master', 'Re:Master']
levelList = ['1', '2', '3', '4', '5', '6', '7', '7+', '8', '8+', '9', '9+', '10', '10+', '11', '11+', '12', '12+', '13', '13+', '14', '14+', '15']
achievementList = [50.0, 60.0, 70.0, 75.0, 80.0, 90.0, 94.0, 97.0, 98.0, 99.0, 99.5, 100.0, 100.5]
BaseRa = [0.0, 5.0, 6.0, 7.0, 7.5, 8.5, 9.5, 10.5, 12.5, 12.7, 13.0, 13.2, 13.5, 14.0]
BaseRaSpp = [7.0, 8.0, 9.6, 11.2, 12.0, 13.6, 15.2, 16.8, 20.0, 20.3, 20.8, 21.1, 21.6, 22.4]

class DrawText:

    def __init__(self, image: ImageDraw.ImageDraw, font: str) -> None:
        self._img = image
        self._font = font

    def get_box(self, text: str, size: int):
        return ImageFont.truetype(self._font, size).getbbox(text)

    def draw(self,
            pos_x: int,
            pos_y: int,
            size: int,
            text: str,
            color: Tuple[int, int, int, int] = (255, 255, 255, 255),
            anchor: str = 'lt',
            stroke_width: int = 0,
            stroke_fill: Tuple[int, int, int, int] = (0, 0, 0, 0),
            multiline: bool = False):

        font = ImageFont.truetype(self._font, size)
        if multiline:
            self._img.multiline_text((pos_x, pos_y), str(text), color, font, anchor, stroke_width=stroke_width, stroke_fill=stroke_fill)
        else:
            self._img.text((pos_x, pos_y), str(text), color, font, anchor, stroke_width=stroke_width, stroke_fill=stroke_fill)
    
    def draw_partial_opacity(self,
            pos_x: int,
            pos_y: int,
            size: int,
            text: str,
            po: int = 2,
            color: Tuple[int, int, int, int] = (255, 255, 255, 255),
            anchor: str = 'lt',
            stroke_width: int = 0,
            stroke_fill: Tuple[int, int, int, int] = (0, 0, 0, 0)):

        font = ImageFont.truetype(self._font, size)
        self._img.text((pos_x + po, pos_y + po), str(text), (0, 0, 0, 128), font, anchor, stroke_width=stroke_width, stroke_fill=stroke_fill)
        self._img.text((pos_x, pos_y), str(text), color, font, anchor, stroke_width=stroke_width, stroke_fill=stroke_fill)

class ChartInfo(object):

    def __init__(self, id: str, title: str, level: int, achievement: float, dxscore: int, rate: int, ra: int, fc: int, fs: int, ds: float, type: str):
        self.id = id
        self.title = title
        self.level = level
        self.achievement = achievement
        self.dxscore = dxscore
        self.rate = rate
        self.ra = ra
        self.fc = fc
        self.fs = fs
        self.ds = ds
        self.type = type
    
    def __eq__(self, other):
        return self.ra == other.ra

    def __lt__(self, other):
        return self.ra < other.ra

    @classmethod
    def from_json(cls, data):
        rate = ['d', 'c', 'b', 'bb', 'bbb', 'a', 'aa', 'aaa', 's', 'sp', 'ss', 'ssp', 'sss', 'sssp']
        ri = rate.index(data['rate'])
        fc = ['', 'fc', 'fcp', 'ap', 'app']
        fi = fc.index(data['fc'])
        fs = ['', 'fs', 'fsp', 'fsd', 'fsdp']
        si = fs.index(data['fs'])
        return cls(
            id = data['song_id'],
            title = data['title'],
            level = data['level_index'],
            achievement = data['achievements'],
            dxscore = data['dxScore'],
            rate = ri,
            ra = data['ra'],
            fc = fi,
            fs = si,
            ds = data['ds'],
            type = data['type']
        )

class BestList(object):

    def __init__(self, size: int):
        self.data = []
        self.size = size

    def push(self, elem: ChartInfo):
        if len(self.data) >= self.size and elem < self.data[-1]:
            return
        self.data.append(elem)
        self.data.sort()
        self.data.reverse()
        while (len(self.data) > self.size):
            del self.data[-1]
    
    def __getitem__(self, index):
        return self.data[index]

class DrawBest:

    def __init__(self, sdBest: BestList, 
                       dxBest: BestList, 
                       userName: str, 
                       addRating: int, 
                       rankRating: int, 
                       plate: str,
                       qqId: Optional[Union[int, str]] = None, 
                       b50: Optional[bool] = False) -> None:
        self.sdBest = sdBest
        self.dxBest = dxBest
        self.userName = userName
        self.addRating = addRating
        self.rankRating = rankRating
        self.Rating = addRating + rankRating
        self.plate = plate
        self.qqId = qqId
        self.b50 = b50
        if self.b50:
            self.Rating = 0
            for sd in sdBest:
                sd: ChartInfo
                self.Rating += computeRa(sd.ds, sd.achievement, True)
            for dx in dxBest:
                dx: ChartInfo
                self.Rating += computeRa(dx.ds, dx.achievement, True)
        self.cover_dir = os.path.join(static, 'mai', 'cover')
        self.maimai_dir = os.path.join(static, 'mai', 'pic')

    def _getCharWidth(self, o) -> int:
        widths = [
            (126, 1), (159, 0), (687, 1), (710, 0), (711, 1), (727, 0), (733, 1), (879, 0), (1154, 1), (1161, 0),
            (4347, 1), (4447, 2), (7467, 1), (7521, 0), (8369, 1), (8426, 0), (9000, 1), (9002, 2), (11021, 1),
            (12350, 2), (12351, 1), (12438, 2), (12442, 0), (19893, 2), (19967, 1), (55203, 2), (63743, 1),
            (64106, 2), (65039, 1), (65059, 0), (65131, 2), (65279, 1), (65376, 2), (65500, 1), (65510, 2),
            (120831, 1), (262141, 2), (1114109, 1),
        ]
        if o == 0xe or o == 0xf:
            return 0
        for num, wid in widths:
            if o <= num:
                return wid
        return 1

    def _coloumWidth(self, s: str) -> int:
        res = 0
        for ch in s:
            res += self._getCharWidth(ord(ch))
        return res

    def _changeColumnWidth(self, s: str, len: int) -> str:
        res = 0
        sList = []
        for ch in s:
            res += self._getCharWidth(ord(ch))
            if res <= len:
                sList.append(ch)
        return ''.join(sList)

    def _dxScore(self, info: ChartInfo) -> Tuple[int, int]:
        notes: list[int] = mai.total_list.by_id(str(info.id)).charts[info.level]['notes']
        value = 0
        for i in notes:
            value += i
        dx = info.dxscore / (value * 3) * 100
        if dx <= 85:
            result = (0, 0)
        elif dx <= 90:
            result = (0, 1)
        elif dx <= 93:
            result = (0, 2)
        elif dx <= 95:
            result = (1, 3)
        elif dx <= 97:
            result = (1, 4)
        else:
            result = (2, 5)
        return result

    def _findRaPic(self) -> str:
        if self.Rating < 1000:
            num = '01'
        elif self.Rating < 2000:
            num = '02'
        elif self.Rating < (3000 if not self.b50 else 4000):
            num = '03'
        elif self.Rating < (4000 if not self.b50 else 7000):
            num = '04'
        elif self.Rating < (5000 if not self.b50 else 10000):
            num = '05'
        elif self.Rating < (6000 if not self.b50 else 12000):
            num = '06'
        elif self.Rating < (7000 if not self.b50 else 13000):
            num = '07'
        elif self.Rating < (8000 if not self.b50 else 14000):
            num = '08'
        elif self.Rating < (8500 if not self.b50 else 14500):
            num = '09'
        elif self.b50 and self.Rating < 15000:
            num = '10'
        else:
            num = '11'
        return f'UI_CMN_DXRating_{num}.png'
        
    def _findMatchLevel(self) -> str:
        if self.b50:
            ra = [1000, 1200, 1400, 1500, 1600, 1700, 1800, 1850, 1900, 1950, 2000, 2010, 2020, 2030, 2040, 2050, 2060, 2070, 2080, 2090, 2100]
            for n, v in enumerate(ra):
                if self.addRating < v:
                    return f'UI_DNM_DaniPlate_{n:02d}.png'
                elif n == (len(ra) -1) and self.addRating >= v:
                    return f'UI_DNM_DaniPlate_{n:02d}.png'
        else:
            ra = [250, 500, 750, 1000, 1200, 1400, 1500, 1600, 1700, 1800, 1850, 1900, 1950, 2000, 2010, 2020, 2030, 2040, 2050, 2060, 2070, 2080, 2090, 2100]
            for n, v in enumerate(ra):
                if self.addRating < v:
                    return f'UI_CMN_MatchLevel_{n + 1:02d}.png'
                elif n == (len(ra) -1) and self.addRating >= v:
                    return f'UI_CMN_MatchLevel_{n + 1:02d}.png'

    def whiledraw(self, data: BestList, type: bool, b50: bool = False) -> Image.Image:
        # y为第一排纵向坐标，dy为各排间距
        if b50:
            y = 430 if type else 1670
            dy = 170
        else:
            y = 500 if type else 1500
            dy = 190

        TITLE_COLOR = [(14, 117, 54, 255), (199, 69, 12, 255), (192, 32, 56, 255), (103, 20, 141, 255), (230, 230, 230, 255)]
        TEXT_COLOR = [(14, 117, 54, 255), (199, 69, 12, 255), (175, 0, 50, 255), (103, 20, 141, 255), (103, 20, 141, 255)]
        rankPic = ['D', 'C', 'B', 'BB', 'BBB', 'A', 'AA', 'AAA', 'S', 'Sp', 'SS', 'SSp', 'SSS', 'SSSp']
        comboPic = ['', 'FC', 'FCp', 'AP', 'APp']
        syncPic = ['', 'FS', 'FSp', 'FSD', 'FSDp']

        dxstar = [Image.open(os.path.join(self.maimai_dir, f'UI_RSL_DXScore_Star_0{_ + 1}.png')).resize((20, 20)) for _ in range(3)]

        for num, info in enumerate(data.data):
            info: ChartInfo
            if num % 5 == 0:
                x = 100
                y += dy if num != 0 else 0
            else:
                x += 404

            songid = get_cover_len4_id(info.id)
            cover = Image.open(os.path.join(self.cover_dir, f'{songid}.png')).resize((135, 135))
            version = Image.open(os.path.join(self.maimai_dir, f'UI_RSL_MBase_Parts_{info.type}.png')).resize((55, 19))
            rate = Image.open(os.path.join(self.maimai_dir, f'UI_TTR_PhotoParts_{rankPic[info.rate]}.png')).resize((80, 50))

            self._im.alpha_composite(self._diff[info.level], (x, y))
            self._im.alpha_composite(cover, (x + 5, y + 5))
            self._im.alpha_composite(version, (x + 80, y + 141))
            self._im.alpha_composite(rate, (x + 153, y + 68))
            if info.fc:
                fc = Image.open(os.path.join(self.maimai_dir, f'UI_MSS_MBase_Icon_{comboPic[info.fc]}.png')).resize((45, 45))
                self._im.alpha_composite(fc, (x + 240, y + 70))
            if info.fs:
                fs = Image.open(os.path.join(self.maimai_dir, f'UI_MSS_MBase_Icon_{syncPic[info.fs]}.png')).resize((45, 45))
                self._im.alpha_composite(fs, (x + 285, y + 70))
            
            dx = self._dxScore(info)
            for _ in range(dx[1]):
                self._im.alpha_composite(dxstar[dx[0]], (x + 355, y + 40 + 20 * _))

            self._tb.draw(x + 40, y + 148, 20, info.id, anchor='mm')
            title = info.title
            if self._coloumWidth(title) > 16:
                title = self._changeColumnWidth(title, 15) + '...'
            self._siyuan.draw(x + 155, y + 20, 20, title, TITLE_COLOR[info.level], anchor='lm')
            p, s = f'{info.achievement:.4f}'.split('.')
            r = self._tb.get_box(p, 35)
            self._tb.draw(x + 155, y + 70, 35, p, TEXT_COLOR[info.level], anchor='ld')
            self._tb.draw(x + 155 + r[2], y + 68, 25, f'.{s}%', TEXT_COLOR[info.level], anchor='ld')
            self._tb.draw(x + 155, y + 125, 22, f'Rating {info.ds} -> {computeRa(info.ds, info.achievement, True) if self.b50 else info.ra}', TEXT_COLOR[info.level], anchor='lm')

    async def draw(self):
        
        meiryo = os.path.join(static, 'meiryo.ttc')
        siyuan = os.path.join(static, 'SourceHanSansSC-Bold.otf')
        Torus_SemiBold = os.path.join(static, 'Torus SemiBold.otf')
        basic = Image.open(os.path.join(self.maimai_dir, 'b40_score_basic.png'))
        advanced = Image.open(os.path.join(self.maimai_dir, 'b40_score_advanced.png'))
        expert = Image.open(os.path.join(self.maimai_dir, 'b40_score_expert.png'))
        master = Image.open(os.path.join(self.maimai_dir, 'b40_score_master.png'))
        remaster = Image.open(os.path.join(self.maimai_dir, 'b40_score_remaster.png'))
        logo = Image.open(os.path.join(self.maimai_dir, 'logo.png')).resize((378, 172))
        dx_rating = Image.open(os.path.join(self.maimai_dir, self._findRaPic())).resize((425, 80))
        Name = Image.open(os.path.join(self.maimai_dir, 'Name.png'))
        MatchLevel = Image.open(os.path.join(self.maimai_dir, self._findMatchLevel())).resize((134, 55) if self.b50 else (128, 58))
        rating = Image.open(os.path.join(self.maimai_dir, 'UI_CMN_Shougou_Rainbow.png')).resize((454, 50))
        self._diff = [basic, advanced, expert, master, remaster]

        # 作图
        self._im = Image.open(os.path.join(self.maimai_dir, 'b40_bg.png')).convert('RGBA')

        self._im.alpha_composite(logo, (5, 130))
        if self.plate:
            plate = Image.open(os.path.join(self.maimai_dir, f'{self.plate}.png')).resize((1420, 230))
        else:
            plate = Image.open(os.path.join(self.maimai_dir, 'UI_Plate_000011.png')).resize((1420, 230))
        self._im.alpha_composite(plate, (390, 100))
        icon = Image.open(os.path.join(self.maimai_dir, 'UI_Icon_0000.png')).resize((214, 214))
        self._im.alpha_composite(icon, (398, 108))
        if self.qqId:
            async with aiohttp.request('GET', f'http://q1.qlogo.cn/g?b=qq&nk={self.qqId}&s=100') as resp:
                qqLogo = Image.open(io.BytesIO(await resp.read()))
            self._im.alpha_composite(Image.new('RGBA', (203, 203), (255, 255, 255, 255)), (404, 114))
            self._im.alpha_composite(qqLogo.convert('RGBA').resize((201, 201)), (405, 115))
        self._im.alpha_composite(dx_rating, (620, 108))
        self.Rating = f'{self.Rating:05d}'
        for n, i in enumerate(self.Rating):
            if n == 0 and i == 0:
                continue
            self._im.alpha_composite(Image.open(os.path.join(self.maimai_dir, f'UI_NUM_Drating_{i}.png')), (820 + 33 * n, 133))
        self._im.alpha_composite(Name, (620, 200))
        self._im.alpha_composite(MatchLevel, (935, 205))
        self._im.alpha_composite(rating, (620, 275))

        text_im = ImageDraw.Draw(self._im)
        self._meiryo = DrawText(text_im, meiryo)
        self._siyuan = DrawText(text_im, siyuan)
        self._tb = DrawText(text_im, Torus_SemiBold)

        self._meiryo.draw(635, 235, 40, self.userName, (0, 0, 0, 255), 'lm')
        self._meiryo.draw(847, 300, 22, f'底分：{self.rankRating} + 段位分：{self.addRating}' if not self.b50 else 'Simulation of New Rating System', (0, 0, 0, 255), 'mm', 3, (255, 255, 255, 255))
        self._meiryo.draw(900, 2365, 35, f'Designed by Yuri-YuzuChaN & BlueDeer233 | Generated by {BOTNAME} BOT', (103, 20, 141, 255), 'mm', 3, (255, 255, 255, 255))

        self.whiledraw(self.sdBest, True, self.b50)
        self.whiledraw(self.dxBest, False, self.b50)

        return self._im

def computeRa(ds: float, achievement: float, spp: bool = False, israte: bool = False) -> Union[int, Tuple[int, str]]:
    baseRa = 22.4 if spp else 14.0
    rate = 'SSSp'
    if achievement < 50:
        baseRa = 7.0 if spp else 0.0
        rate = 'D'
    elif achievement < 60:
        baseRa = 8.0 if spp else 5.0
        rate = 'C'
    elif achievement < 70:
        baseRa = 9.6 if spp else 6.0
        rate = 'B'
    elif achievement < 75:
        baseRa = 11.2 if spp else 7.0
        rate = 'BB'
    elif achievement < 80:
        baseRa = 12.0 if spp else 7.5
        rate = 'BBB'
    elif achievement < 90:
        baseRa = 13.6 if spp else 8.5
        rate = 'A'
    elif achievement < 94:
        baseRa = 15.2 if spp else 9.5
        rate = 'AA'
    elif achievement < 97:
        baseRa = 16.8 if spp else 10.5
        rate = 'AAA'
    elif achievement < 98:
        baseRa = 20.0 if spp else 12.5
        rate = 'S'
    elif achievement < 99:
        baseRa = 20.3 if spp else 12.7
        rate = 'Sp'
    elif achievement < 99.5:
        baseRa = 20.8 if spp else 13.0
        rate = 'SS'
    elif achievement < 100:
        baseRa = 21.1 if spp else 13.2
        rate = 'SSp'
    elif achievement < 100.5:
        baseRa = 21.6 if spp else 13.5
        rate = 'SSS'
    
    if israte:
        data = (math.floor(ds * (min(100.5, achievement) / 100) * baseRa), rate)
    else:
        data = math.floor(ds * (min(100.5, achievement) / 100) * baseRa)

    return data

def generateAchievementList(ds: float, spp: bool=False):
    _achievementList = []
    for index, acc in enumerate(achievementList):
        if index == len(achievementList) - 1:
            continue
        _achievementList.append(acc)
        c_acc = (computeRa(ds, achievementList[index]) + 1) / ds / (BaseRaSpp[index + 1] if spp else BaseRa[index + 1]) * 100
        c_acc = math.ceil(c_acc * 10000) / 10000
        while c_acc < achievementList[index + 1]:
            _achievementList.append(c_acc)
            c_acc = (computeRa(ds, c_acc + 0.0001) + 1) / ds / (BaseRaSpp[index + 1] if spp else BaseRa[index + 1]) * 100
            c_acc = math.ceil(c_acc * 10000) / 10000
    _achievementList.append(100.5)
    return _achievementList

async def generate(payload: dict) -> Union[MessageSegment, str]:
    obj = await get_player_data('best', payload)
    if isinstance(obj, str):
        return obj
    qqId = None
    b50 = False
    if 'qq' in payload:
        qqId = payload['qq']
    if 'b50' in payload:
        b50 = True
        sd_best = BestList(35)
    else:
        sd_best = BestList(25)
    dx_best = BestList(15)

    dx: List[Dict] = obj['charts']['dx']
    sd: List[Dict] = obj['charts']['sd']
    for c in sd:
        sd_best.push(ChartInfo.from_json(c))
    for c in dx:
        dx_best.push(ChartInfo.from_json(c))
    draw_best = DrawBest(sd_best, dx_best, obj['nickname'], obj['additional_rating'], obj['rating'], obj['plate'], qqId, b50)
    pic = await draw_best.draw()
    return MessageSegment.image(image_to_base64(pic))