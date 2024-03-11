import asyncio
import json
import random
import traceback
from collections import namedtuple
from copy import deepcopy
from io import BytesIO
from typing import Any, Dict, List, Optional, Tuple, Union

import aiofiles
import aiohttp
from PIL import Image
from pydantic import BaseModel, Field

from .. import *
from .image import image_to_base64
from .maimaidx_api_data import *


class Stats(BaseModel):

    cnt: Optional[float] = None
    diff: Optional[str] = None
    fit_diff: Optional[float] = None
    avg: Optional[float] = None
    avg_dx: Optional[float] = None
    std_dev: Optional[float] = None
    dist: Optional[List[int]] = None
    fc_dist: Optional[List[float]] = None


Notes1 = namedtuple('Notes', ['tap', 'hold', 'slide', 'brk'])
Notes2 = namedtuple('Notes', ['tap', 'hold', 'slide', 'touch', 'brk'])


class Chart(BaseModel):

    notes: Optional[Union[Notes1, Notes2]]
    charter: Optional[str] = None


class BasicInfo(BaseModel):

    title: Optional[str]
    artist: Optional[str]
    genre: Optional[str]
    bpm: Optional[int]
    release_date: Optional[str]
    version: Optional[str] = Field(alias='from')
    is_new: Optional[bool]


def cross(checker: Union[List[str], List[float]], elem: Optional[Union[str, float, List[str], List[float], Tuple[float, float]]], diff: List[int]) -> Tuple[bool, List[int]]:
    ret = False
    diff_ret = []
    if not elem or elem is Ellipsis:
        return True, diff
    if isinstance(elem, List):
        for _j in (range(len(checker)) if diff is Ellipsis else diff):
            if _j >= len(checker):
                continue
            __e = checker[_j]
            if __e in elem:
                diff_ret.append(_j)
                ret = True
    elif isinstance(elem, Tuple):
        for _j in (range(len(checker)) if diff is Ellipsis else diff):
            if _j >= len(checker):
                continue
            __e = checker[_j]
            if elem[0] <= __e <= elem[1]:
                diff_ret.append(_j)
                ret = True
    else:
        for _j in (range(len(checker)) if diff is Ellipsis else diff):
            if _j >= len(checker):
                continue
            __e = checker[_j]
            if elem == __e:
                diff_ret.append(_j)
                ret = True
    return ret, diff_ret


def in_or_equal(checker: Union[str, int], elem: Optional[Union[str, float, List[str], List[float], Tuple[float, float]]]) -> bool:
    if elem is Ellipsis:
        return True
    if isinstance(elem, List):
        return checker in elem
    elif isinstance(elem, Tuple):
        return elem[0] <= checker <= elem[1]
    else:
        return checker == elem


class Music(BaseModel):

    id: Optional[str] = None
    title: Optional[str] = None
    type: Optional[str] = None
    ds: Optional[List[float]] = []
    level: Optional[List[str]] = []
    cids: Optional[List[int]] = []
    charts: Optional[List[Chart]] = []
    basic_info: Optional[BasicInfo] = None
    stats: Optional[List[Optional[Stats]]] = []
    diff: Optional[List[int]] = []


class RaMusic(BaseModel):
    
    id: str
    ds: float
    lv: str
    type: str


class MusicList(List[Music]):
    
    def by_id(self, music_id: str) -> Optional[Music]:
        for music in self:
            if music.id == music_id:
                return music
        return None

    def by_title(self, music_title: str) -> Optional[Music]:
        for music in self:
            if music.title == music_title:
                return music
        return None
    
    def by_level(self, level: Union[str, List[str]], byid: bool = False) -> Optional[Union[List[Music], List[str]]]:
        levelList = []             
        if isinstance(level, str):
            levelList = [music.id if byid else music for music in self if level in music.level]
        else:
            levelList = [music.id if byid else music for music in self for lv in level if lv in music.level]
        return levelList

    def lvList(self, rating: bool = False) -> Dict[str, Dict[str, Union[List[Music], List[RaMusic]]]]:
        level = {}
        for lv in levelList:
            if lv == '15':
                r = range(1)
            elif lv in levelList[:6]:
                r = range(9, -1, -1)
            elif '+' in lv:
                r = range(9, 6, -1)
            else:
                r = range(6, -1, -1)
            levellist = { f'{lv if "+" not in lv else lv[:-1]}.{_}': [] for _ in r }
            musiclist = self.by_level(lv)
            for music in musiclist:
                for diff, ds in enumerate(music.ds):
                    if str(ds) in levellist:
                        if rating:
                            levellist[str(ds)].append(RaMusic(id=music.id, ds=ds, lv=str(diff), type=music.type))
                        else:
                            levellist[str(ds)].append(music)
            level[lv] = levellist
        
        return level

    def random(self):
        return random.choice(self)

    def filter(self,
               *,
               level: Optional[Union[str, List[str]]] = ...,
               ds: Optional[Union[float, List[float], Tuple[float, float]]] = ...,
               title_search: Optional[str] = ...,
               artist_search: Optional[str] = ...,
               charter_search: Optional[str] = ...,
               genre: Optional[Union[str, List[str]]] = ...,
               bpm: Optional[Union[float, List[float], Tuple[float, float]]] = ...,
               type: Optional[Union[str, List[str]]] = ...,
               diff: List[int] = ...,
               ):
        new_list = MusicList()
        for music in self:
            diff2 = diff
            music = deepcopy(music)
            ret, diff2 = cross(music.level, level, diff2)
            if not ret:
                continue
            ret, diff2 = cross(music.ds, ds, diff2)
            if not ret:
                continue
            ret, diff2 = search_charts(music.charts, charter_search, diff2)
            if not ret:
                continue
            if not in_or_equal(music.basic_info.genre, genre):
                continue
            if not in_or_equal(music.type, type):
                continue
            if not in_or_equal(music.basic_info.bpm, bpm):
                continue
            if title_search is not Ellipsis and title_search.lower() not in music.title.lower():
                continue
            if artist_search is not Ellipsis and artist_search.lower() not in music.basic_info.artist.lower():
                continue
            music.diff = diff2
            new_list.append(music)
        return new_list


def search_charts(checker: List[Chart], elem: str, diff: List[int]):
    ret = False
    diff_ret = []
    if not elem or elem is Ellipsis:
        return True, diff
    for _j in (range(len(checker)) if diff is Ellipsis else diff):
        if elem.lower() in checker[_j].charter.lower():
            diff_ret.append(_j)
            ret = True
    return ret, diff_ret


class Alias(BaseModel):

    SongID: Optional[int] = None
    Name: Optional[str] = None
    Alias: Optional[List[str]] = None

class AliasList(List[Alias]):

    def by_id(self, music_id: int) -> Optional[List[Alias]]:
        alias_music = []
        for music in self:
            if music.SongID == int(music_id):
                alias_music.append(music)
        return alias_music
    
    def by_alias(self, music_alias: str) -> Optional[List[Alias]]:
        alias_list = []
        for music in self:
            if music_alias in music.Alias:
                alias_list.append(music)
        return alias_list


async def download_music_pictrue(song_id: Union[int, str]) -> Union[str, BytesIO]:
    try:
        if (file := coverdir / f'{song_id}.png').exists():
            return file
        song_id = int(song_id)
        if len(str(song_id)) == 4 or (song_id > 10000 and song_id <= 11000):
            for _id in [song_id + 10000, song_id - 10000]:
                if (file := coverdir / f'{_id}.png').exists():
                    return file
        async with aiohttp.request('GET', f'https://www.diving-fish.com/covers/{song_id:05d}.png', timeout=aiohttp.ClientTimeout(total=60)) as req:
            if req.status == 200:
                return BytesIO(await req.read())
            else:
                return coverdir / '11000.png'
    except:
        return coverdir / '11000.png'


async def openfile(file: str) -> Union[dict, list]:
    async with aiofiles.open(file, 'r', encoding='utf-8') as f:
        data = json.loads(await f.read())
    return data


async def writefile(file: str, data: Any) -> bool:
    async with aiofiles.open(file, 'w', encoding='utf-8') as f:
        await f.write(json.dumps(data, ensure_ascii=False, indent=4))
    return True


async def get_music_list() -> MusicList:
    """
    获取所有数据
    """
    # MusicData
    try:
        try:
            music_data = await maiApi.music_data()
            await writefile(music_file, music_data)
        except asyncio.exceptions.TimeoutError:
            log.error('从diving-fish获取maimaiDX曲目数据超时，正在使用yuzuapi中转获取曲目数据')
            music_data = await maiApi.transfer_music()
            await writefile(music_file, music_data)
        except UnknownError:
            log.error('从diving-fish获取maimaiDX曲目数据失败，请检查网络环境。已切换至本地暂存文件')
            music_data = await openfile(music_file)
        except Exception:
            log.error(f'Error: {traceback.format_exc()}')
            log.error('maimaiDX曲目数据获取失败，请检查网络环境。已切换至本地暂存文件')
            music_data = await openfile(music_file)
    except FileNotFoundError:
        log.error(f'未找到文件，请自行使用浏览器访问 "https://www.diving-fish.com/api/maimaidxprober/music_data" 将内容保存为 "music_data.json" 存放在 "static" 目录下并重启bot')
    
    # ChartStats
    try:
        try:
            chart_stats = await maiApi.chart_stats()
            await writefile(chart_file, chart_stats)
        except asyncio.exceptions.TimeoutError:
            log.error('从diving-fish获取maimaiDX数据获取超时，正在使用yuzuapi中转获取单曲数据')
            chart_stats = await maiApi.transfer_chart()
            await writefile(chart_file, chart_stats)
        except UnknownError:
            log.error('从diving-fish获取maimaiDX单曲数据获取错误。已切换至本地暂存文件')
            chart_stats = await openfile(chart_file)
        except Exception:
            log.error(f'Error: {traceback.format_exc()}')
            log.error('maimaiDX数据获取错误，请检查网络环境。已切换至本地暂存文件')
            chart_stats = await openfile(chart_file)
    except FileNotFoundError:
        log.error(f'未找到文件，请自行使用浏览器访问 "https://www.diving-fish.com/api/maimaidxprober/chart_stats" 将内容保存为 "chart_stats.json" 存放在 "static" 目录下并重启bot')

    total_list: MusicList = MusicList(music_data)
    for num, music in enumerate(total_list):
        if music['id'] in chart_stats['charts']:
            _stats = [_data if _data else None for _data in chart_stats['charts'][music['id']]] if {} in chart_stats['charts'][music['id']] else chart_stats['charts'][music['id']]
        else:
            _stats = None
        total_list[num] = Music(stats=_stats, **total_list[num])

    return total_list

async def get_music_alias_list() -> AliasList:
    """
    获取所有别名
    """
    if local_alias_file.exists():
        local_alias_data: Dict[str, Dict[str, Union[str, List[str]]]] = await openfile(local_alias_file)
    else:
        local_alias_data = {}
    alias_data: List[Dict[str, Union[int, str, List[str]]]] = []
    try:
        alias_data = await maiApi.get_alias()
        await writefile(alias_file, alias_data)
    except ServerError as e:
        log.error(e)
    except UnknownError:
        log.error('获取所有曲目别名信息错误，请检查网络环境。已切换至本地暂存文件')
        alias_data = await openfile(alias_file)
        if not alias_data:
            log.error('本地暂存别名文件为空，请自行使用浏览器访问 "https://api.yuzuchan.moe/maimaidx/maimaidxalias" 获取别名数据并保存在 "static/all_alias.json" 文件中并重启bot')
            raise ValueError

    for _a in alias_data:
        if (song_id := str(_a['SongID'])) in local_alias_data:
            _a['Alias'].extend(local_alias_data[song_id])
    
    total_alias_list = AliasList(alias_data)
    for _ in range(len(total_alias_list)):
        total_alias_list[_] = Alias(**alias_data[_])

    return total_alias_list

async def update_local_alias(id: str, alias_name: str) -> bool:
    try:
        if local_alias_file.exists():
            local_alias_data: Dict[str, List[str]] = await openfile(local_alias_file)
        else:
            local_alias_data: Dict[str, List[str]] = {}
        if id not in local_alias_data:
            local_alias_data[id] = []
        local_alias_data[id].append(alias_name.lower())
        mai.total_alias_list.by_id(id)[0].Alias.append(alias_name.lower())
        await writefile(local_alias_file, local_alias_data)
        return True
    except Exception as e:
        log.error(f'添加本地别名失败: {e}')
        return False

class MaiMusic:

    total_list: Optional[MusicList]

    def __init__(self) -> None:
        """
        封装所有曲目信息以及猜歌数据，便于更新
        """

    async def get_music(self) -> MusicList:
        """
        获取所有曲目数据
        """
        self.total_list = await get_music_list()

    async def get_music_alias(self) -> AliasList:
        """
        获取所有曲目别名
        """
        self.total_alias_list = await get_music_alias_list()

    def guess(self):
        """
        初始化猜歌数据
        """
        self.hot_music_ids = []
        for music in self.total_list:
            if music.stats:
                count = 0
                for stats in music.stats:
                    if stats:
                        count += stats.cnt if stats.cnt else 0
                if count > 10000:
                    self.hot_music_ids.append(music.id)  # 游玩次数超过1w次加入猜歌库
        self.guess_data = list(filter(lambda x: x.id in self.hot_music_ids, self.total_list))

mai = MaiMusic()


class GuessData(BaseModel):
    
    music: Music
    options: List[str]
    answer: List[str]
    img: str
    end: bool = False


class Guess:

    Group: Dict[str, GuessData] = {}

    def __init__(self) -> None:
        """
        猜歌类
        """
        if not guess_file.exists():
            with open(guess_file, 'w', encoding='utf-8') as f:
                json.dump({'enable': [], 'disable': []}, f)
        self.config: Dict[str, List[int]] = json.load(open(guess_file, 'r', encoding='utf-8'))
    
    async def start(self, gid: str):
        """
        开始猜歌
        """
        self.Group[gid] = await self.guessData()

    async def guessData(self) -> GuessData:
        """
        获取猜歌数据
        """
        music: Music = random.choice(mai.guess_data)
        guess_options = random.sample([
            f'的 Expert 难度是 {music.level[2]}',
            f'的 Master 难度是 {music.level[3]}',
            f'的分类是 {music.basic_info.genre}',
            f'的版本是 {music.basic_info.version}',
            f'的艺术家是 {music.basic_info.artist}',
            f'{"不" if music.type == "SD" else ""}是 DX 谱面',
            f'{"没" if len(music.ds) == 4 else ""}有白谱',
            f'的 BPM 是 {music.basic_info.bpm}'
        ], 6)
        answer = mai.total_alias_list.by_id(music.id)[0].Alias
        answer.append(music.id)
        img = Image.open(await download_music_pictrue(music.id))
        w, h = img.size
        w2, h2 = int(w / 3), int(h / 3)
        l, u = random.randrange(0, int(2 * w / 3)), random.randrange(0, int(2 * h / 3))
        img = img.crop((l, u, l+w2, u+h2))
        self.is_end = False
        return GuessData(**{
            'music': music,
            'options': guess_options,
            'answer': answer,
            'img': image_to_base64(img),
            'end': False})

    def end(self, gid: str):
        """
        结束猜歌
        """
        del self.Group[gid]

    async def on(self, gid: int):
        """开启猜歌"""
        if gid not in self.config['enable']:
            self.config['enable'].append(gid)
        if gid in self.config['disable']:
            self.config['disable'].remove(gid)
        await writefile(guess_file, self.config)
        return '群猜歌功能已开启'
    
    async def off(self, gid: int):
        """关闭猜歌"""
        if gid not in self.config['disable']:
            self.config['disable'].append(gid)
        if gid in self.config['enable']:
            self.config['enable'].remove(gid)
        if str(gid) in self.Group:
            self.end(str(gid))
        await writefile(guess_file, self.config)
        return '群猜歌功能已关闭'


guess = Guess()


class GroupAlias:

    def __init__(self) -> None:
        if not group_alias_file.exists():
            with open(group_alias_file, 'w', encoding='utf-8') as f:
                json.dump({'enable': [], 'disable': [], 'global': True}, f)
        self.config: Dict[str, List[int]] = json.load(open(group_alias_file, 'r', encoding='utf-8'))

    async def on(self, gid: int) -> str:
        """开启推送"""
        if gid not in self.config['enable']:
            self.config['enable'].append(gid)
        if gid in self.config['disable']:
            self.config['disable'].remove(gid)
        await writefile(group_alias_file, self.config)
        return '群别名推送功能已开启'

    async def off(self, gid: int) -> str:
        """关闭推送"""
        if gid not in self.config['disable']:
            self.config['disable'].append(gid)
        if gid in self.config['enable']:
            self.config['enable'].remove(gid)
        await writefile(group_alias_file, self.config)
        return '群别名推送功能已关闭'

    async def alias_global_change(self, set: bool):
        self.config['global'] = set
        await writefile(group_alias_file, self.config)


alias = GroupAlias()
