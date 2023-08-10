import asyncio
import json
import os
import random
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

    ID: Optional[str] = None
    Name: Optional[str] = None
    Alias: Optional[List[str]] = None

class AliasList(List[Alias]):

    def by_id(self, music_id: int) -> Optional[List[Alias]]:
        alias_music = []
        for music in self:
            if music.ID == music_id:
                alias_music.append(music)
        return alias_music
    
    def by_alias(self, music_alias: str) -> Optional[List[Alias]]:
        alias_list = []
        for music in self:
            if music_alias in music.Alias:
                alias_list.append(music)
        return alias_list


async def download_music_pictrue(id: Union[int, str]) -> Union[str, BytesIO]:
    try:
        if os.path.exists(file := os.path.join(coverdir, f'{id}.png')):
            return file
        id = int(id)
        if id > 10000 and id <= 11000:
            id -= 10000
        async with aiohttp.request('GET', f'https://www.diving-fish.com/covers/{id:05d}.png', timeout=aiohttp.ClientTimeout(total=60)) as req:
            if req.status == 200:
                return BytesIO(await req.read())
            else:
                return os.path.join(coverdir, '11000.png')
    except:
        return os.path.join(coverdir, '11000.png')


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
            async with aiohttp.request('GET', 'https://www.diving-fish.com/api/maimaidxprober/music_data', timeout=aiohttp.ClientTimeout(total=30)) as obj_data:
                if obj_data.status != 200:
                    log.error('从diving-fish获取maimaiDX曲目数据失败，请检查网络环境。已切换至本地暂存文件')
                    music_data = await openfile(music_file)
                else:
                    music_data = await obj_data.json()
                    await writefile(music_file, music_data)
        except asyncio.exceptions.TimeoutError:
            log.error('从diving-fish获取maimaiDX曲目数据超时，正在使用yuzuapi中转获取曲目数据')
            music_data = await get_music_alias('music')
            if isinstance(music_data, str):
                log.error('从yuzuapi获取maimaiDX曲目数据失败。已切换至本地暂存文件')
                music_data = await openfile(music_file)
            else:
                await writefile(music_file, music_data)
        except Exception:
            log.error(f'Error: {traceback.format_exc()}')
            log.error('maimaiDX曲目数据获取失败，请检查网络环境。已切换至本地暂存文件')
            music_data = await openfile(music_file)
    except FileNotFoundError:
        log.error(f'未找到文件，请自行使用浏览器访问 "https://www.diving-fish.com/api/maimaidxprober/music_data" 将内容保存为 "music_data.json" 存放在 "static" 目录下并重启bot')
    
    # ChartStats
    try:
        try:
            async with aiohttp.request('GET', 'https://www.diving-fish.com/api/maimaidxprober/chart_stats', timeout=aiohttp.ClientTimeout(total=30)) as obj_stats:
                if obj_stats.status != 200:
                    log.error('从diving-fish获取maimaiDX单曲数据获取错误。已切换至本地暂存文件')
                    chart_stats = await openfile(chart_file)
                else:
                    chart_stats = await obj_stats.json()
                    await writefile(chart_file, chart_stats)
        except asyncio.exceptions.TimeoutError:
            log.error('从diving-fish获取maimaiDX数据获取超时，正在使用yuzuapi中转获取单曲数据')
            chart_stats = await get_music_alias('chart')
            if isinstance(chart_stats, str):
                log.error('从yuzuapi获取maimaiDX数据获取失败。已切换至本地暂存文件')
                chart_stats = await openfile(chart_file)
            else:
                await writefile(chart_file, chart_stats)
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
    if os.path.exists(alias_file):
        local_alias_data: Dict[str, Dict[str, Union[str, List[str]]]] = await openfile(alias_file)
    else:
        local_alias_data = {}
    
    alias_data: Dict[str, Dict[str, Union[str, List[str]]]] = await get_music_alias('all')
    if isinstance(alias_data, str):
        log.error('获取所有曲目别名信息错误，请检查网络环境。已切换至本地暂存文件')
        if not local_alias_data:
            log.error('本地暂存别名文件为空，请自行使用浏览器访问 "https://api.yuzuai.xyz/maimaidx/maimaidxalias" 获取别名数据并保存在 "static/all_alias.json" 文件中并重启bot')
    else:
        for id, music in alias_data.items():
            if id in local_alias_data:
                for alias_name in music['Alias']:
                    if alias_name.lower() not in local_alias_data[id]['Alias']:
                        local_alias_data[id]['Alias'].append(alias_name.lower())
            else:
                local_alias_data[id] = {
                    'Name': music['Name'],
                    'Alias': music['Alias']
                }
        await writefile(alias_file, local_alias_data)
    data = local_alias_data
    
    total_alias_list = AliasList(data)
    for _ in range(len(total_alias_list)):
        total_alias_list[_] = Alias(ID=total_alias_list[_], Name=data[total_alias_list[_]]['Name'], Alias=data[total_alias_list[_]]['Alias'])

    return total_alias_list

async def update_local_alias(id: str, alias_name: str):
    try:
        local_alias_data: Dict[str, Dict[str, Union[str, List[str]]]] = await openfile(alias_file)
        
        music_alias = mai.total_alias_list.by_id(id)[0]
        index = mai.total_alias_list.index(music_alias)
        new_list = music_alias.Alias
        new_list.append(alias_name)
        new_alias = {
            'Name': music_alias.Name,
            'Alias': new_list
        }
        mai.total_alias_list[index] = Alias(ID=id, **new_alias)
        local_alias_data[id]['Alias'] = new_list
        await writefile(alias_file, local_alias_data)
        return True
    except Exception as e:
        log.error('添加本地别名失败')
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

    async def start(self):
        """
        开始猜歌
        """
        self.music: Music = random.choice(self.guess_data)
        self.guess_options = [
            f'的 Expert 难度是 {self.music.level[2]}',
            f'的 Master 难度是 {self.music.level[3]}',
            f'的分类是 {self.music.basic_info.genre}',
            f'的版本是 {self.music.basic_info.version}',
            f'的艺术家是 {self.music.basic_info.artist}',
            f'{"不" if self.music.type == "SD" else ""}是 DX 谱面',
            f'{"没" if len(self.music.ds) == 4 else ""}有白谱',
            f'的 BPM 是 {self.music.basic_info.bpm}'
        ]
        music = mai.total_alias_list.by_id(self.music.id)[0]
        self.answer = music.Alias
        self.answer.append(self.music.id)
        self.guess_options = random.sample(self.guess_options, 6)
        img = Image.open(await download_music_pictrue(self.music.id))
        w, h = img.size
        w2, h2 = int(w / 3), int(h / 3)
        l, u = random.randrange(0, int(2 * w / 3)), random.randrange(0, int(2 * h / 3))
        img = img.crop((l, u, l+w2, u+h2))
        self.b64image = image_to_base64(img)
        self.is_end = False

mai = MaiMusic()

class Guess:

    Group: Dict[str, Dict[str, Union[MaiMusic, int]]] = {}

    def __init__(self) -> None:
        """
        猜歌类
        """
        if not os.path.exists(guess_file):
            with open(guess_file, 'w', encoding='utf-8') as f:
                json.dump({'enable': [], 'disable': []}, f)
        self.config: Dict[str, List[int]] = json.load(open(guess_file, 'r', encoding='utf-8'))
    
    def add(self, gid: str):
        """
        新增猜歌群，防止重复指令
        """
        self.Group[gid] = {}
    
    def start(self, gid: str, music: MaiMusic, cycle: int = 0):
        """
        正式开始猜歌
        """
        self.Group[gid] = {
            'object': music,
            'cycle': cycle
        }

    def end(self, gid: str):
        """
        结束猜歌
        """
        del self.Group[gid]

    def guess_change(self, gid: int, set: bool):
        """
        猜歌开关
        """
        if set:
            if gid not in self.config['enable']:
                self.config['enable'].append(gid)
            if gid in self.config['disable']:
                self.config['disable'].remove(gid)
        else:
            if gid not in self.config['disable']:
                self.config['disable'].append(gid)
            if gid in self.config['enable']:
                self.config['enable'].remove(gid)
        try:
            with open(guess_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=True, indent=4)
        except:
            log.error(traceback.format_exc())

guess = Guess()

class GroupAlias:

    def __init__(self) -> None:
        if not os.path.exists(group_alias_file):
            with open(group_alias_file, 'w', encoding='utf-8') as f:
                json.dump({'enable': [], 'disable': [], 'global': True}, f)
        self.config: Dict[str, List[int]] = json.load(open(group_alias_file, 'r', encoding='utf-8'))
        if 'global' not in self.config:
            self.config['global'] = True
            self.alias_save()

    def alias_change(self, gid: int, set: bool):
        """
        别名推送开关
        """
        if set:
            if gid not in self.config['enable']:
                self.config['enable'].append(gid)
            if gid in self.config['disable']:
                self.config['disable'].remove(gid)
        else:
            if gid not in self.config['disable']:
                self.config['disable'].append(gid)
            if gid in self.config['enable']:
                self.config['enable'].remove(gid)
        self.alias_save()

    def alias_global_change(self, set: bool):
        if set:
            self.config['global'] = True
        else:
            self.config['global'] = False
        self.alias_save()

    def alias_save(self):
        try:
            with open(group_alias_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=True, indent=4)
        except:
            log.error(traceback.format_exc())

alias = GroupAlias()
