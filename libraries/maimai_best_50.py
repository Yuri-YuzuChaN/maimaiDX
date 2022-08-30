import aiohttp, os, math, io
from PIL import Image, ImageDraw, ImageFont
from typing import Optional, Tuple, Union, Dict, List
from hoshino.config import NICKNAME
from hoshino.typing import MessageSegment
from .image import image_to_base64
from .maimaidx_api_data import get_player_data
from .maimaidx_music import get_cover_len4_id
from .. import static

scoreRank = 'D C B BB BBB A AA AAA S S+ SS SS+ SSS SSS+'.lower().split(' ')
comboRank = 'FC FC+ AP AP+'.lower().split(' ')
combo_rank = 'fc fcp ap app'.split(' ')
syncRank = 'FS FS+ FDX FDX+'.lower().split(' ')
sync_rank = 'fs fsp fsd fsdp'.split(' ')
diffs = 'Basic Advanced Expert Master Re:Master'.split(' ')
levelList = '1 2 3 4 5 6 7 7+ 8 8+ 9 9+ 10 10+ 11 11+ 12 12+ 13 13+ 14 14+ 15'.split(' ')
achievementList = [50.0, 60.0, 70.0, 75.0, 80.0, 90.0, 94.0, 97.0, 98.0, 99.0, 99.5, 100.0, 100.5]
BaseRa = [0.0, 5.0, 6.0, 7.0, 7.5, 8.5, 9.5, 10.5, 12.5, 12.7, 13.0, 13.2, 13.5, 14.0]
BaseRaSpp = [7.0, 8.0, 9.6, 11.2, 12.0, 13.6, 15.2, 16.8, 20.0, 20.3, 20.8, 21.1, 21.6, 22.4]
adobe = os.path.join(static, 'adobe_simhei.otf')
msyh = os.path.join(static, 'msyh.ttc')

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
            self._img.multiline_text((pos_x, pos_y), '\n'.join([i for i in text]), color, font, anchor, stroke_width=stroke_width, stroke_fill=stroke_fill)
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

    def __init__(self, id: str, title: str, level: int, achievement: float, rate: int, ra: int, fc: int, fs: int, ds: float):
        self.id = id
        self.title = title
        self.level = level
        self.achievement = achievement
        self.rate = rate
        self.ra = ra
        self.fc = fc
        self.fs = fs
        self.ds = ds
    
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
            rate = ri,
            ra = data['ra'],
            fc = fi,
            fs = si,
            ds = data['ds']
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
                       qqId: Optional[Union[int, str]] = None, 
                       b50: Optional[bool] = False) -> None:
        self.sdBest = sdBest
        self.dxBest = dxBest
        self.userName = userName
        self.addRating = addRating
        self.rankRating = rankRating
        self.Rating = addRating + rankRating
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
        self.pic_dir = os.path.join(static, 'mai', 'pic')
        self.cover_dir = os.path.join(static, 'mai', 'cover')
        self.new_dir = os.path.join(static, 'mai', 'new')

    def _findRaPic(self) -> str:
        num = '10'
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
        elif self.Rating < (8000 if not self.b50 else 14500):
            num = '08'
        elif self.Rating < (8500 if not self.b50 else 15000):
            num = '09'
        return f'UI_CMN_DXRating_S_{num}.png'
        
    def _findMatchLevel(self) -> str:
        t = '01'
        if self.addRating < 250:
            t = '01'
        elif self.addRating < 500:
            t = '02'
        elif self.addRating < 750:
            t = '03'
        elif self.addRating < 1000:
            t = '04'
        elif self.addRating < 1200:
            t = '05'
        elif self.addRating < 1400:
            t = '06'
        elif self.addRating < 1500:
            t = '07'
        elif self.addRating < 1600:
            t = '08'
        elif self.addRating < 1700:
            t = '09'
        elif self.addRating < 1800:
            t = '10'
        elif self.addRating < 1850:
            t = '11'
        elif self.addRating < 1900:
            t = '12'
        elif self.addRating < 1950:
            t = '13'
        elif self.addRating < 2000:
            t = '14'
        elif self.addRating < 2010:
            t = '15'
        elif self.addRating < 2020:
            t = '16'
        elif self.addRating < 2030:
            t = '17'
        elif self.addRating < 2040:
            t = '18'
        elif self.addRating < 2050:
            t = '19'
        elif self.addRating < 2060:
            t = '20'
        elif self.addRating < 2070:
            t = '21'
        elif self.addRating < 2080:
            t = '22'
        elif self.addRating < 2090:
            t = '23'
        elif self.addRating < 2100:
            t = '24'
        else:
            t = '25'

        return f'UI_CMN_MatchLevel_{t}.png'

    def whiledraw(self, data: BestList, xi: int, yi: int) -> Image.Image:
        y = yi
        color = [(17, 177, 54, 255), (199, 69, 12, 255), (192, 32, 56, 255), (103, 20, 141, 255), (142, 44, 215, 255)]
        rankPic = 'D C B BB BBB A AA AAA S Sp SS SSp SSS SSSp'.split(' ')
        comboPic = ' FC FCp AP APp'.split(' ')
        syncPic = ' FS FSp FSD FSDp'.split(' ')
        for n, i in enumerate(data.data):
            i: ChartInfo
            if n % 5 == 0:
                x = xi
                y += 180 if n != 0 else 0
            else:
                x += 330

            if i.level == 4:
                tcolor = (142, 44, 215, 255)
            else:
                tcolor = (255, 255, 255, 255)

            songid = get_cover_len4_id(i.id)
            cover = Image.open(os.path.join(self.cover_dir, f'{songid}.png')).convert('RGBA').resize((124, 124))
            rate = Image.open(os.path.join(self.pic_dir, f'UI_GAM_Rank_{rankPic[i.rate]}.png')).convert('RGBA')

            self._im.alpha_composite(self._diff[i.level], (x, y))
            self._im.alpha_composite(cover, (x + 7, y + 29))
            self._im.alpha_composite(rate.resize((int(rate.size[0] * 0.78), int((rate.size[1] - 2) * 0.78))), (x + 140, y + 90))
            if i.fc:
                fc = Image.open(os.path.join(self.pic_dir, f'UI_MSS_MBase_Icon_{comboPic[i.fc]}.png')).convert('RGBA')
                self._im.alpha_composite(fc.resize((int(fc.size[0] * 0.8), int(fc.size[1] * 0.8))), (x + 220, y + 90))
            if i.fs:
                fs = Image.open(os.path.join(self.pic_dir, f'UI_MSS_MBase_Icon_{syncPic[i.fs]}.png')).convert('RGBA')
                self._im.alpha_composite(fs.resize((int(fs.size[0] * 0.8), int(fs.size[1] * 0.8))), (x + 260, y + 90))

            if len(i.title) > 20:
                title = f'{i.title[:19]}...'
            else:
                title = i.title
            
            p, s = f'{i.achievement:.4f}'.split('.')
            r = self._fontb.get_box(p, 24)

            self._font.draw(x + 155, y + 18, 14, title, color[i.level], 'mm')
            self._fontb.draw(x + 140, y + 45, 24, p, tcolor, 'lm')
            self._fontb.draw(x + 140 + r[2], y + 60, 15, f'.{s}%', tcolor, 'ld')
            self._fontb.draw(x + 140, y + 70, 15, f'ID | {int(songid)}', tcolor, 'lm')
            self._fontb.draw(x + 140, y + 142, 15, f'Rating {i.ds} -> {computeRa(i.ds, i.achievement, True) if self.b50 else i.ra}', tcolor, 'lm')

    async def draw(self):
        
        meiryo = os.path.join(static, 'meiryo.ttc')
        meiryob = os.path.join(static, 'meiryob.ttc')
        basic = Image.open(os.path.join(self.new_dir, 'b40_basic.png'))
        advanced = Image.open(os.path.join(self.new_dir, 'b40_advanced.png'))
        expert = Image.open(os.path.join(self.new_dir, 'b40_expert.png'))
        master = Image.open(os.path.join(self.new_dir, 'b40_master.png'))
        remaster = Image.open(os.path.join(self.new_dir, 'b40_remaster.png'))
        ratingbg = Image.open(os.path.join(self.pic_dir, self._findRaPic()))
        MatchLevel = Image.open(os.path.join(self.pic_dir, self._findMatchLevel())).resize((90, 38))
        self._diff = [basic, advanced, expert, master, remaster]

        self._im = Image.open(os.path.join(self.new_dir, 'b50_bg.png')).convert('RGBA')

        if self.qqId:
            async with aiohttp.request('GET', f'http://q1.qlogo.cn/g?b=qq&nk={self.qqId}&s=100') as resp:
                qqLogo = Image.open(io.BytesIO(await resp.read()))
            self._im.alpha_composite(qqLogo.convert('RGBA').resize((132, 132)), (402, 48))
        else:
            chara_l = Image.open(os.path.join(self.new_dir, 'chara_l.png'))
            chara_r = Image.open(os.path.join(self.new_dir, 'chara_r.png'))
            self._im.alpha_composite(chara_l, (400, 70))
            self._im.alpha_composite(chara_r, (475, 70))

        text_im = ImageDraw.Draw(self._im)
        self._font = DrawText(text_im, meiryo)
        self._fontb = DrawText(text_im, meiryob)
        self._im.alpha_composite(ratingbg, (555, 40))

        self.Rating = f'{self.Rating:05d}'
        for n, i in enumerate(self.Rating):
            if n == 0 and i == 0:
                continue
            self._im.alpha_composite(Image.open(os.path.join(self.pic_dir, f'UI_NUM_Drating_{i}.png')).resize((15, 18)), (640 + 15 * n, 50))

        self._im.alpha_composite(MatchLevel, (750, 40))
        self._font.draw(570, 120, 35, self.userName, (0, 0, 0, 255), 'lm')
        self._font.draw(740, 175, 20, f'底分：{self.rankRating} + 段位分：{self.addRating}' if not self.b50 else 'Simulation of Splash PLUS Rating', (0, 0, 0, 255), 'mm', 3, (255, 255, 255, 255))

        for n, i in enumerate(['Credit to', 'XybBot & Diving-fish', 'Generated by', f'{NICKNAME if isinstance(NICKNAME, str) else list(NICKNAME)[0]} BOT']):
            self._fontb.draw(1240, 90 + 30 * n, 25, i, (0, 0, 0, 255), 'mm')

        self.whiledraw(self.sdBest, 130, 295)
        self.whiledraw(self.dxBest, 50, 1630)

        return self._im

def computeRa(ds: float, achievement: float, spp: bool = False) -> int:
    baseRa = 22.4 if spp else 14.0
    if achievement < 50:
        baseRa = 7.0 if spp else 0.0
    elif achievement < 60:
        baseRa = 8.0 if spp else 5.0
    elif achievement < 70:
        baseRa = 9.6 if spp else 6.0
    elif achievement < 75:
        baseRa = 11.2 if spp else 7.0
    elif achievement < 80:
        baseRa = 12.0 if spp else 7.5
    elif achievement < 90:
        baseRa = 13.6 if spp else 8.5
    elif achievement < 94:
        baseRa = 15.2 if spp else 9.5
    elif achievement < 97:
        baseRa = 16.8 if spp else 10.5
    elif achievement < 98:
        baseRa = 20.0 if spp else 12.5
    elif achievement < 99:
        baseRa = 20.3 if spp else 12.7
    elif achievement < 99.5:
        baseRa = 20.8 if spp else 13.0
    elif achievement < 100:
        baseRa = 21.1 if spp else 13.2
    elif achievement < 100.5:
        baseRa = 21.6 if spp else 13.5

    return math.floor(ds * (min(100.5, achievement) / 100) * baseRa)

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
    draw_best = DrawBest(sd_best, dx_best, obj['nickname'], obj['additional_rating'], obj['rating'], qqId, b50)
    pic = await draw_best.draw()
    return MessageSegment.image(image_to_base64(pic))