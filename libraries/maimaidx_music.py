import json
import os
import random
from collections import namedtuple
from copy import deepcopy
from io import BytesIO
from typing import Optional, Tuple

import aiofiles
from PIL import Image
from pydantic import BaseModel, Field

from .image import image_to_base64, image_to_bytesio
from .maimaidx_api_data import *
from .. import static

cover_dir = os.path.join(static, 'mai', 'cover')


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
    is_new: Optional[str]


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
    stats: Optional[List[Stats]] = []
    diff: Optional[List[int]] = []


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

    ID: Optional[int] = None
    Name: Optional[str] = None
    Alias: Optional[List[str]] = None


class AliasList(List[Alias]):

    def by_id(self, music_id: int) -> Optional[List[Alias]]:
        alias_list = []
        for music in self:
            if music.ID == int(music_id):
                alias_list.append(music)
        return alias_list
    
    def by_alias(self, music_alias: str) -> Optional[List[Alias]]:
        alias_list = []
        for music in self:
            if music_alias in music.Alias:
                alias_list.append(music)
        return alias_list


async def download_music_pictrue(id: Union[int, str]) -> Union[str, BytesIO]:
    try:
        if os.path.exists(file := os.path.join(static, 'mai', 'cover', f'{id}.png')):
            return file
        async with httpx.AsyncClient(timeout=60) as client:
            req = await client.get(f'https://www.diving-fish.com/covers/{id}.png')
            if req.status_code == 200:
                return BytesIO(await req.read())
            else:
                return os.path.join(static, 'mai', 'cover', '11000.png')
    except:
        return os.path.join(static, 'mai', 'cover', '11000.png')


async def get_music_list() -> MusicList:
    """
    获取所有数据
    """
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            obj_data = await client.get('https://www.diving-fish.com/api/maimaidxprober/music_data')
            obj_data.raise_for_status()
            data = obj_data.json()
            async with aiofiles.open(os.path.join(static, 'music_data.json'), 'w', encoding='utf-8') as f:
                await f.write(json.dumps(data, ensure_ascii=False, indent=4))
    except:  # noqa
        log.error('maimaiDX曲目数据获取失败，请检查网络环境。已切换至本地暂存文件')
        async with aiofiles.open(os.path.join(static, 'music_data.json'), 'r', encoding='utf-8') as f:
            data = json.loads(await f.read())
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            obj_stats = await client.get('https://www.diving-fish.com/api/maimaidxprober/chart_stats')
            obj_stats.raise_for_status()
            stats = obj_stats.json()
            async with aiofiles.open(os.path.join(static, 'chart_stats.json'), 'w', encoding='utf-8') as f:
                await f.write(json.dumps(stats, ensure_ascii=False, indent=4))
    except:  # noqa
        log.error('maimaiDX数据获取错误，请检查网络环境。已切换至本地暂存文件')
        async with aiofiles.open(os.path.join(static, 'chart_stats.json'), 'r', encoding='utf-8') as f:
            stats = json.loads(await f.read())

    total_list: MusicList = MusicList(data)
    for num, music in enumerate(total_list):
        if music['id'] in stats['charts']:
            _stats = stats['charts'][music['id']]
        else:
            _stats = None
        total_list[num] = Music(stats=_stats, **total_list[num])

    return total_list

async def get_music_alias_list() -> AliasList:
    """
    获取所有别名
    """
    data = await get_music_alias('all')
    if isinstance(data, str):
        log.info('获取所有曲目别名信息错误，请检查网络环境。已切换至本地暂存文件')
        async with aiofiles.open(os.path.join(static, 'all_alias.json'), 'r', encoding='utf-8') as f:
            data = json.loads(await f.read())
    else:
        async with aiofiles.open(os.path.join(static, 'all_alias.json'), 'w', encoding='utf-8') as f:
            await f.write(json.dumps(data, ensure_ascii=False, indent=4))
    total_alias_list = AliasList(data)
    for _ in range(len(total_alias_list)):
        total_alias_list[_] = Alias(ID=total_alias_list[_], Name=data[total_alias_list[_]]['Name'], Alias=data[total_alias_list[_]]['Alias'])

    return total_alias_list

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
                    count += stats.cnt if stats.cnt else 0
                if count > 10000:
                    self.hot_music_ids.append(music.id)  # 游玩次数超过1w次加入猜歌库
        self.guess_data = list(filter(lambda x: x.id in self.hot_music_ids, self.total_list))

    async def start(self):
        """
        开始猜歌
        """
        self.music = Music(random.choice(self.guess_data))
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
        music = mai.total_alias_list.by_id(self.music.id)
        self.answer = music[0].Alias
        self.answer.append(self.music.id)
        self.guess_options = random.sample(self.guess_options, 6)
        img = Image.open(await download_music_pictrue(self.music.id))
        w, h = img.size
        w2, h2 = int(w / 3), int(h / 3)
        l, u = random.randrange(0, int(2 * w / 3)), random.randrange(0, int(2 * h / 3))
        img = img.crop((l, u, l+w2, u+h2))
        self.b64image = image_to_base64(img)
        self.image = image_to_bytesio(img)
        self.is_end = False

mai = MaiMusic()

class Guess:

    Group: Dict[int, Dict[str, Union[MaiMusic, int]]] = {}

    def __init__(self) -> None:
        """
        猜歌类
        """
        
        self.config_json = os.path.join(static, 'guess_config.json')
        if not os.path.exists(self.config_json):
            with open(self.config_json, 'w', encoding='utf-8') as f:
                json.dump({'enable': [], 'disable': []}, f)
        self.config: Dict[str, List[int]] = json.load(open(self.config_json, 'r', encoding='utf-8'))
    
    def add(self, gid: int):
        """
        新增猜歌群，防止重复指令
        """
        self.Group[gid] = {}

    def start(self, gid: int, music: MaiMusic, cycle: int = 0):
        """
        正式开始猜歌
        """
        self.Group[gid] = {
            'object': music,
            'cycle': cycle
        }

    def end(self, gid: int):
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
            with open(self.config_json, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=True, indent=4)
        except:
            log.error(traceback.format_exc())

guess = Guess()

class GroupAlias:

    def __init__(self) -> None:
        self.group_alias = os.path.join(static, 'group_alias.json')
        if not os.path.exists(self.group_alias):
            with open(self.group_alias, 'w', encoding='utf-8') as f:
                json.dump({'enable': [], 'disable': [], 'global': True}, f)
        self.config: Dict[str, List[int]] = json.load(open(self.group_alias, 'r', encoding='utf-8'))
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
            with open(self.group_alias, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=True, indent=4)
        except:
            log.error(traceback.format_exc())

alias = GroupAlias()