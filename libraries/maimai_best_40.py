# Author: xyb, Diving_Fish
import asyncio
import os
import math
import numpy as np
from typing import Optional, Dict, List
from io import BytesIO
from hoshino.config.__bot__ import NICKNAME

import requests
import aiohttp
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from .maimaidx_music import total_list
from .. import static

scoreRank = 'D C B BB BBB A AA AAA S S+ SS SS+ SSS SSS+'.split(' ')
combo = ' FC FC+ AP AP+'.split(' ')
diffs = 'Basic Advanced Expert Master Re:Master'.split(' ')
adobe = os.path.join(static, 'adobe_simhei.otf')
msyh = os.path.join(static, 'msyh.ttc')


class ChartInfo(object):
    def __init__(self, idNum: str, diff: int, tp: str, achievement: float, ra: int, comboId: int, scoreId: int,
                 title: str, ds: float, lv: str):
        self.idNum = idNum
        self.diff = diff
        self.tp = tp
        self.achievement = achievement
        self.ra = ra
        self.comboId = comboId
        self.scoreId = scoreId
        self.title = title
        self.ds = ds
        self.lv = lv

    def __str__(self):
        return '%-50s' % f'{self.title} [{self.tp}]' + f'{self.ds}\t{diffs[self.diff]}\t{self.ra}'

    def __eq__(self, other):
        return self.ra == other.ra

    def __lt__(self, other):
        return self.ra < other.ra

    @classmethod
    def from_json(cls, data):
        rate = ['d', 'c', 'b', 'bb', 'bbb', 'a', 'aa', 'aaa', 's', 'sp', 'ss', 'ssp', 'sss', 'sssp']
        ri = rate.index(data["rate"])
        fc = ['', 'fc', 'fcp', 'ap', 'app']
        fi = fc.index(data["fc"])
        return cls(
            idNum=total_list.by_title(data["title"]).id,
            title=data["title"],
            diff=data["level_index"],
            ra=data["ra"],
            ds=data["ds"],
            comboId=fi,
            scoreId=ri,
            lv=data["level"],
            achievement=data["achievements"],
            tp=data["type"]
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

    def pop(self):
        del self.data[-1]

    def __str__(self):
        return '[\n\t' + ', \n\t'.join([str(ci) for ci in self.data]) + '\n]'

    def __len__(self):
        return len(self.data)

    def __getitem__(self, index):
        return self.data[index]


class DrawBest(object):

    def __init__(self, sdBest: BestList, dxBest: BestList, userName: str, playerRating: int, musicRating: int, qqId: int or str = None, b50: bool = False):
        self.sdBest = sdBest
        self.dxBest = dxBest
        self.userName = self._stringQ2B(userName)
        self.playerRating = playerRating
        self.musicRating = musicRating
        self.qqId = qqId
        self.b50 = b50
        self.rankRating = self.playerRating - self.musicRating
        if self.b50:
            self.playerRating = 0
            for sd in sdBest:
                self.playerRating += computeRa(sd.ds, sd.achievement, True)
            for dx in dxBest:
                self.playerRating += computeRa(dx.ds, dx.achievement, True)
        self.pic_dir = os.path.join(static, 'mai', 'pic')
        self.cover_dir = os.path.join(static, 'mai', 'cover')
        self.img = Image.open(os.path.join(self.pic_dir, 'UI_TTR_BG_Base_Plus.png')).convert('RGBA')
        self.ROWS_IMG = [2]
        for i in range(6):
            self.ROWS_IMG.append(116 + 96 * i)
        if self.b50:
            self.COLOUMS_IMG = []
            for i in range(8):
                self.COLOUMS_IMG.append(2 + 138 * i)
            for i in range(4):
                self.COLOUMS_IMG.append(988 + 138 * i)
        else:
            self.COLOUMS_IMG = []
            for i in range(6):
                self.COLOUMS_IMG.append(2 + 172 * i)
            for i in range(4):
                self.COLOUMS_IMG.append(888 + 172 * i)
        self.draw()

    def _Q2B(self, uchar):
        """单个字符 全角转半角"""
        inside_code = ord(uchar)
        if inside_code == 0x3000:
            inside_code = 0x0020
        else:
            inside_code -= 0xfee0
        if inside_code < 0x0020 or inside_code > 0x7e:  # 转完之后不是半角字符返回原来的字符
            return uchar
        return chr(inside_code)

    def _stringQ2B(self, ustring):
        """把字符串全角转半角"""
        return "".join([self._Q2B(uchar) for uchar in ustring])

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

    def _coloumWidth(self, s: str):
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

    def _resizePic(self, img: Image.Image, time: float):
        return img.resize((int(img.size[0] * time), int(img.size[1] * time)))

    def _findRaPic(self) -> str:
        num = '10'
        if self.playerRating < 1000:
            num = '01'
        elif self.playerRating < 2000:
            num = '02'
        elif self.playerRating < (3000 if not self.b50 else 4000):
            num = '03'
        elif self.playerRating < (4000 if not self.b50 else 7000):
            num = '04'
        elif self.playerRating < (5000 if not self.b50 else 10000):
            num = '05'
        elif self.playerRating < (6000 if not self.b50 else 12000):
            num = '06'
        elif self.playerRating < (7000 if not self.b50 else 13000):
            num = '07'
        elif self.playerRating < (8000 if not self.b50 else 14500):
            num = '08'
        elif self.playerRating < (8500 if not self.b50 else 15000):
            num = '09'
        return f'UI_CMN_DXRating_S_{num}.png'

    def _drawRating(self, ratingBaseImg: Image.Image):
        COLOUMS_RATING = [86, 100, 115, 130, 145]
        theRa = self.playerRating
        i = 4
        while theRa:
            digit = theRa % 10
            theRa = theRa // 10
            digitImg = Image.open(os.path.join(self.pic_dir, f'UI_NUM_Drating_{digit}.png')).convert('RGBA')
            digitImg = self._resizePic(digitImg, 0.6)
            ratingBaseImg.paste(digitImg, (COLOUMS_RATING[i] - 2, 9), mask=digitImg.split()[3])
            i -= 1
        return ratingBaseImg

    def _drawBestList(self, img: Image.Image, sdBest: BestList, dxBest: BestList):
        itemW = 164 if not self.b50 else 131
        itemH = 88
        Color = [(69, 193, 36), (255, 186, 1), (255, 90, 102), (134, 49, 200), (217, 197, 233)]
        levelTriagle = [(itemW, 0), (itemW - 27, 0), (itemW, 27)]
        rankPic = 'D C B BB BBB A AA AAA S Sp SS SSp SSS SSSp'.split(' ')
        comboPic = ' FC FCp AP APp'.split(' ')
        imgDraw = ImageDraw.Draw(img)
        titleFontName = adobe
        for num in range(0, len(sdBest)):
            i = num // 5 if not self.b50 else num // 7
            j = num % 5 if not self.b50 else num % 7
            chartInfo = sdBest[num]
            pngPath = os.path.join(self.cover_dir, f'{chartInfo.idNum}.jpg')
            if not os.path.exists(pngPath):
                pngPath = os.path.join(self.cover_dir, '1000.png')
            temp = Image.open(pngPath).convert('RGB')
            temp = self._resizePic(temp, itemW / temp.size[0])
            temp = temp.crop((0, (temp.size[1] - itemH) / 2, itemW, (temp.size[1] + itemH) / 2))
            temp = temp.filter(ImageFilter.GaussianBlur(3))
            temp = temp.point(lambda p: p * 0.72)

            tempDraw = ImageDraw.Draw(temp)
            tempDraw.polygon(levelTriagle, Color[chartInfo.diff])
            font = ImageFont.truetype(titleFontName, 16 if not self.b50 else 14, encoding='utf-8')
            title = chartInfo.title
            if self._coloumWidth(title) > 15 if not self.b50 else 13:
                title = self._changeColumnWidth(title, 14 if not self.b50 else 12) + '...'
            tempDraw.text((8, 8), title, 'white', font)
            font = ImageFont.truetype(titleFontName, 14 if not self.b50 else 12, encoding='utf-8')

            tempDraw.text((7, 28), f'{"%.4f" % chartInfo.achievement}%', 'white', font)
            rankImg = Image.open(os.path.join(self.pic_dir, f'UI_GAM_Rank_{rankPic[chartInfo.scoreId]}.png')).convert('RGBA')
            rankImg = self._resizePic(rankImg, 0.3)
            temp.paste(rankImg, (88 if not self.b50 else 72, 28), rankImg.split()[3])
            if chartInfo.comboId:
                comboImg = Image.open(os.path.join(self.pic_dir, f'UI_MSS_MBase_Icon_{comboPic[chartInfo.comboId]}_S.png')).convert('RGBA')
                comboImg = self._resizePic(comboImg, 0.45)
                temp.paste(comboImg, (119 if not self.b50 else 103, 27), comboImg.split()[3])
            font = ImageFont.truetype(adobe, 12, encoding='utf-8')
            tempDraw.text((8, 44), f'Base: {chartInfo.ds} -> {chartInfo.ra if not self.b50 else computeRa(chartInfo.ds, chartInfo.achievement, True)}', 'white', font)
            font = ImageFont.truetype(adobe, 18, encoding='utf-8')
            tempDraw.text((8, 60), f'#{num + 1}', 'white', font)

            recBase = Image.new('RGBA', (itemW, itemH), 'black')
            recBase = recBase.point(lambda p: p * 0.8)
            img.paste(recBase, (self.COLOUMS_IMG[j] + 5, self.ROWS_IMG[i + 1] + 5))
            img.paste(temp, (self.COLOUMS_IMG[j] + 4, self.ROWS_IMG[i + 1] + 4))
        for num in range(len(sdBest), sdBest.size):
            i = num // 5 if not self.b50 else num // 7
            j = num % 5 if not self.b50 else num % 7
            temp = Image.open(os.path.join(self.cover_dir, f'1000.png')).convert('RGB')
            temp = self._resizePic(temp, itemW / temp.size[0])
            temp = temp.crop((0, (temp.size[1] - itemH) / 2, itemW, (temp.size[1] + itemH) / 2))
            temp = temp.filter(ImageFilter.GaussianBlur(1))
            img.paste(temp, (self.COLOUMS_IMG[j] + 4, self.ROWS_IMG[i + 1] + 4))
        for num in range(0, len(dxBest)):
            i = num // 3
            j = num % 3
            chartInfo = dxBest[num]
            pngPath = os.path.join(self.cover_dir, f'{int(chartInfo.idNum)}.jpg')
            if not os.path.exists(pngPath):
                pngPath = os.path.join(self.cover_dir, f'{int(chartInfo.idNum)}.png')
            if not os.path.exists(pngPath):
                pngPath = os.path.join(self.cover_dir, '1000.png')
            temp = Image.open(pngPath).convert('RGB')
            temp = self._resizePic(temp, itemW / temp.size[0])
            temp = temp.crop((0, (temp.size[1] - itemH) / 2, itemW, (temp.size[1] + itemH) / 2))
            temp = temp.filter(ImageFilter.GaussianBlur(3))
            temp = temp.point(lambda p: p * 0.72)

            tempDraw = ImageDraw.Draw(temp)
            tempDraw.polygon(levelTriagle, Color[chartInfo.diff])
            font = ImageFont.truetype(titleFontName, 16 if not self.b50 else 14, encoding='utf-8')
            title = chartInfo.title
            if self._coloumWidth(title) > 15 if not self.b50 else 13:
                title = self._changeColumnWidth(title, 14 if not self.b50 else 12) + '...'
            tempDraw.text((8, 8), title, 'white', font)
            font = ImageFont.truetype(titleFontName, 14 if not self.b50 else 12, encoding='utf-8')

            tempDraw.text((7, 28), f'{"%.4f" % chartInfo.achievement}%', 'white', font)
            rankImg = Image.open(os.path.join(self.pic_dir, f'UI_GAM_Rank_{rankPic[chartInfo.scoreId]}.png')).convert('RGBA')
            rankImg = self._resizePic(rankImg, 0.3)
            temp.paste(rankImg, (88 if not self.b50 else 72, 28), rankImg.split()[3])
            if chartInfo.comboId:
                comboImg = Image.open(os.path.join(self.pic_dir, f'UI_MSS_MBase_Icon_{comboPic[chartInfo.comboId]}_S.png')).convert('RGBA')
                comboImg = self._resizePic(comboImg, 0.45)
                temp.paste(comboImg, (119 if not self.b50 else 103, 27), comboImg.split()[3])
            font = ImageFont.truetype(adobe, 12, encoding='utf-8')
            tempDraw.text((8, 44), f'Base: {chartInfo.ds} -> {chartInfo.ra if not self.b50 else computeRa(chartInfo.ds, chartInfo.achievement, True)}', 'white', font)
            font = ImageFont.truetype(adobe, 18, encoding='utf-8')
            tempDraw.text((8, 60), f'#{num + 1}', 'white', font)

            recBase = Image.new('RGBA', (itemW, itemH), 'black')
            recBase = recBase.point(lambda p: p * 0.8)
            img.paste(recBase, (self.COLOUMS_IMG[j + (6 if not self.b50 else 8)] + 5, self.ROWS_IMG[i + 1] + 5))
            img.paste(temp, (self.COLOUMS_IMG[j + (6 if not self.b50 else 8)] + 4, self.ROWS_IMG[i + 1] + 4))
        for num in range(len(dxBest), dxBest.size):
            i = num // 3
            j = num % 3
            temp = Image.open(os.path.join(self.cover_dir, f'1000.png')).convert('RGB')
            temp = self._resizePic(temp, itemW / temp.size[0])
            temp = temp.crop((0, (temp.size[1] - itemH) / 2, itemW, (temp.size[1] + itemH) / 2))
            temp = temp.filter(ImageFilter.GaussianBlur(1))
            img.paste(temp, (self.COLOUMS_IMG[j + (6 if not self.b50 else 8)] + 4, self.ROWS_IMG[i + 1] + 4))

    @staticmethod
    def _drawRoundRec(im, color, x, y, w, h, r):
        drawObject = ImageDraw.Draw(im)
        drawObject.ellipse((x, y, x + r, y + r), fill=color)
        drawObject.ellipse((x + w - r, y, x + w, y + r), fill=color)
        drawObject.ellipse((x, y + h - r, x + r, y + h), fill=color)
        drawObject.ellipse((x + w - r, y + h - r, x + w, y + h), fill=color)
        drawObject.rectangle((x + r / 2, y, x + w - (r / 2), y + h), fill=color)
        drawObject.rectangle((x, y + r / 2, x + w, y + h - (r / 2)), fill=color)

    def draw(self):
        if self.qqId:
            resp = requests.get(f'http://q1.qlogo.cn/g?b=qq&nk={self.qqId}&s=100')
            qqLogo = Image.open(BytesIO(resp.content))
            borderImg1 = Image.fromarray(np.zeros((200, 200, 4), dtype=np.uint8)).convert('RGBA')
            borderImg2 = Image.fromarray(np.zeros((200, 200, 4), dtype=np.uint8)).convert('RGBA')
            self._drawRoundRec(borderImg1, (255, 0, 80), 0, 0, 200, 200, 40)
            self._drawRoundRec(borderImg2, (255, 255, 255), 3, 3, 193, 193, 30)
            borderImg1.paste(borderImg2, (0, 0), mask=borderImg2.split()[3])
            borderImg = borderImg1.resize((108, 108))
            borderImg.paste(qqLogo, (4, 4))
            borderImg = self._resizePic(borderImg, 0.926)
            self.img.paste(borderImg, (22, 10), mask=borderImg.split()[3])
        else:
            splashLogo = Image.open(os.path.join(self.pic_dir, 'UI_CMN_TabTitle_MaimaiTitle_Ver214.png')).convert('RGBA')
            splashLogo = self._resizePic(splashLogo, 0.65)
            self.img.paste(splashLogo, (10, 10), mask=splashLogo.split()[3])

        ratingBaseImg = Image.open(os.path.join(self.pic_dir, self._findRaPic())).convert('RGBA')
        ratingBaseImg = self._drawRating(ratingBaseImg)
        ratingBaseImg = self._resizePic(ratingBaseImg, 0.85)
        self.img.paste(ratingBaseImg, (240 if not self.qqId else 140, 8), mask=ratingBaseImg.split()[3])

        namePlateImg = Image.open(os.path.join(self.pic_dir, 'UI_TST_PlateMask.png')).convert('RGBA')
        namePlateImg = namePlateImg.resize((285, 40))
        namePlateDraw = ImageDraw.Draw(namePlateImg)
        font1 = ImageFont.truetype(msyh, 28, encoding='unic')
        namePlateDraw.text((12, 4), ' '.join(list(self.userName)), 'black', font1)
        nameDxImg = Image.open(os.path.join(self.pic_dir, 'UI_CMN_Name_DX.png')).convert('RGBA')
        nameDxImg = self._resizePic(nameDxImg, 0.9)
        namePlateImg.paste(nameDxImg, (230, 4), mask=nameDxImg.split()[3])
        self.img.paste(namePlateImg, (240 if not self.qqId else 140, 40), mask=namePlateImg.split()[3])

        shougouImg = Image.open(os.path.join(self.pic_dir, 'UI_CMN_Shougou_Rainbow.png')).convert('RGBA')
        shougouDraw = ImageDraw.Draw(shougouImg)
        font2 = ImageFont.truetype(adobe, 14, encoding='utf-8')
        playCountInfo = f'底分: {self.musicRating} + 段位分: {self.rankRating}' if not self.b50 else 'Simulation of Splash PLUS Rating'
        shougouImgW, shougouImgH = shougouImg.size
        playCountInfoW, playCountInfoH = shougouDraw.textsize(playCountInfo, font2)
        textPos = ((shougouImgW - playCountInfoW - font2.getoffset(playCountInfo)[0]) / 2, 5)
        shougouDraw.text((textPos[0] - 1, textPos[1]), playCountInfo, 'black', font2)
        shougouDraw.text((textPos[0] + 1, textPos[1]), playCountInfo, 'black', font2)
        shougouDraw.text((textPos[0], textPos[1] - 1), playCountInfo, 'black', font2)
        shougouDraw.text((textPos[0], textPos[1] + 1), playCountInfo, 'black', font2)
        shougouDraw.text((textPos[0] - 1, textPos[1] - 1), playCountInfo, 'black', font2)
        shougouDraw.text((textPos[0] + 1, textPos[1] - 1), playCountInfo, 'black', font2)
        shougouDraw.text((textPos[0] - 1, textPos[1] + 1), playCountInfo, 'black', font2)
        shougouDraw.text((textPos[0] + 1, textPos[1] + 1), playCountInfo, 'black', font2)
        shougouDraw.text(textPos, playCountInfo, 'white', font2)
        shougouImg = self._resizePic(shougouImg, 1.05)
        self.img.paste(shougouImg, (240 if not self.qqId else 140, 83), mask=shougouImg.split()[3])

        self._drawBestList(self.img, self.sdBest, self.dxBest)

        authorBoardImg = Image.open(os.path.join(self.pic_dir, 'UI_CMN_MiniDialog_01.png')).convert('RGBA')
        authorBoardImg = self._resizePic(authorBoardImg, 0.35)
        authorBoardDraw = ImageDraw.Draw(authorBoardImg)
        authorBoardDraw.text((17, 15), f'            Credit to\nXybBot & Diving-fish\n        Generated by\n             {NICKNAME} bot', 'black', font2)
        self.img.paste(authorBoardImg, (1224, 19), mask=authorBoardImg.split()[3])

        dxImg = Image.open(os.path.join(self.pic_dir, 'UI_RSL_MBase_Parts_01.png')).convert('RGBA')
        self.img.paste(dxImg, (887 if not self.b50 else 988, 65), mask=dxImg.split()[3])
        sdImg = Image.open(os.path.join(self.pic_dir, 'UI_RSL_MBase_Parts_02.png')).convert('RGBA')
        self.img.paste(sdImg, (758 if not self.b50 else 865, 65), mask=sdImg.split()[3])

        # self.img.show()

    def getDir(self):
        return self.img


def computeRa(ds: float, achievement: float, spp: bool = False) -> int:
    baseRa = 22.4 if spp else 14.0
    if achievement < 50:
        baseRa = 0.0 if spp else 0.0
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
        baseRa = 20.0 if spp else 12.7
    elif achievement < 99.5:
        baseRa = 20.8 if spp else 13.0
    elif achievement < 100:
        baseRa = 21.1 if spp else 13.2
    elif achievement < 100.5:
        baseRa = 21.6 if spp else 13.5

    return math.floor(ds * (min(100.5, achievement) / 100) * baseRa)


async def get_player_data(payload: Dict):
    async with aiohttp.request("POST", "https://www.diving-fish.com/api/maimaidxprober/query/player", json=payload) as resp:
        if resp.status == 400:
            return None, 400
        elif resp.status == 403:
            return None, 403
        player_data = await resp.json()
        return player_data, 0


async def generate(payload: Dict) -> (Optional[Image.Image], bool):
    obj, success = await get_player_data(payload)
    if success != 0: return None, success
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

    dx: List[Dict] = obj["charts"]["dx"]
    sd: List[Dict] = obj["charts"]["sd"]
    for c in sd:
        sd_best.push(ChartInfo.from_json(c))
    for c in dx:
        dx_best.push(ChartInfo.from_json(c))
    pic = DrawBest(sd_best, dx_best, obj["nickname"], obj["rating"] + obj["additional_rating"], obj["rating"], qqId, b50).getDir()
    return pic, 0
