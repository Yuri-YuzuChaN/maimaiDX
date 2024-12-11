import asyncio
import random
import traceback
from collections import Counter
from copy import deepcopy
from typing import Tuple, overload

from PIL import Image
import numpy as np

from .. import *
from .image import image_to_base64
from .maimaidx_api_data import maiApi
from .maimaidx_error import *
from .maimaidx_model import *
from .tool import openfile, writefile


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


class MusicList(List[Music]):
    
    def by_id(self, music_id: Union[str, int]) -> Optional[Music]:
        for music in self:
            if music.id == str(music_id):
                return music
        return None

    def by_title(self, music_title: str) -> Optional[Music]:
        for music in self:
            if music.title == music_title:
                return music
        return None

    @overload
    def by_level(self, level: str, byid: bool = False) -> Optional[List[Music]]: ...
    @overload
    def by_level(self, level: List[str], byid: bool = False) -> Optional[List[str]]: ...
    def by_level(self, level: Union[str, List[str]], byid: bool = False) -> Optional[Union[List[Music], List[str]]]:
        if isinstance(level, str):
            levelList = [music.id if byid else music for music in self if level in music.level]
        else:
            levelList = [music.id if byid else music for music in self for lv in level if lv in music.level]
        return levelList
    
    def by_plan(self, level: str) -> Dict[str, Union[PlanInfo, RaMusic, Dict[int, Union[PlanInfo, RaMusic]]]]:
        lv = {}
        for music in self.by_level(level):
            if level in music.level:
                count = Counter(music.level)
                if count.get(level) > 1:
                    lv[music.id] = { n: RaMusic(id=music.id, ds=music.ds[n], lv=str(n), lvp=music.level[n], type=music.type) for n, l in enumerate(music.level) if l == level }
                else:
                    index = music.level.index(level)
                    lv[music.id] = RaMusic(id=music.id, ds=music.ds[index], lv=str(index), lvp=music.level[index], type=music.type)
        return lv

    @overload
    def lvList(self) -> Dict[str, Dict[str, List[Music]]]: ...
    @overload
    def lvList(self, *, rating: Optional[bool] = False) -> Dict[str, Dict[str, List[RaMusic]]]: ...
    @overload
    def lvList(self, *, level: Optional[List[str]] = None, rating: Optional[bool] = False) -> Dict[str, Dict[str, List[RaMusic]]]: ...
    def lvList(self, *, level: Optional[List[str]] = None, rating: Optional[bool] = False) -> Dict[str, Dict[str, Union[List[Music], List[RaMusic]]]]:
        _level = {}
        if isinstance(level, List):
            _l = level
        else:
            _l = levelList
        for lv in _l:
            if lv == '15':
                r = range(1)
            elif lv in levelList[:6]:
                r = range(9, -1, -1)
            elif '+' in lv:
                r = range(9, 6, -1)
            else:
                r = range(6, -1, -1)
            levellist = {f'{lv if "+" not in lv else lv[:-1]}.{_}': [] for _ in r}
            musiclist = self.by_level(lv)
            for music in musiclist:
                for diff, ds in enumerate(music.ds):
                    if str(ds) in levellist:
                        if rating:
                            levellist[str(ds)].append(RaMusic(id=music.id, ds=ds, lv=str(diff), lvp=music.level[diff], type=music.type))
                        else:
                            levellist[str(ds)].append(music)
            _level[lv] = levellist
        return  _level

    def by_version(self, version: Union[str, List[str]]) -> Optional[List[Music]]:
        versionList = []
        if isinstance(version, str):
            for music in self:
                if music.id in ignore_music or int(music.id) > 100000: continue
                if version == music.basic_info.version:
                    versionList.append(music)
        else:
            for music in self:
                if music.id in ignore_music or int(music.id) > 100000: continue
                if music.basic_info.version in version:
                    versionList.append(music)
        return versionList

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


class AliasList(List[Alias]):

    def by_id(self, music_id: Union[str, int]) -> Optional[List[Alias]]:
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


async def get_music_list() -> MusicList:
    """获取所有数据"""
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
        raise
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
        raise

    total_list: MusicList = MusicList()
    for music in music_data:
        if music['id'] in chart_stats['charts']:
            _stats = [_data if _data else None for _data in chart_stats['charts'][music['id']]] if {} in chart_stats['charts'][music['id']] else chart_stats['charts'][music['id']]
        else:
            _stats = None
        total_list.append(Music(stats=_stats, **music))

    return total_list

async def get_music_alias_list() -> AliasList:
    """获取所有别名"""
    if local_alias_file.exists():
        local_alias_data: Dict[str, Dict[str, Union[str, List[str]]]] = await openfile(local_alias_file)
    else:
        local_alias_data = {}
    alias_data: List[Dict[str, Union[int, str, List[str]]]] = []
    try:
        alias_data = await maiApi.get_alias()
        await writefile(alias_file, alias_data)
    except asyncio.exceptions.TimeoutError:
        log.error('获取别名超时。已切换至本地暂存文件')
        alias_data = await openfile(alias_file)
        if not alias_data:
            log.error('本地暂存别名文件为空，请自行使用浏览器访问 "https://api.yuzuchan.moe/maimaidx/maimaidxalias" 获取别名数据并保存在 "static/music_alias.json" 文件中并重启bot')
            raise ValueError
    except ServerError as e:
        log.error(e)
        alias_data = await openfile(alias_file)
    except UnknownError:
        log.error('获取所有曲目别名信息错误，请检查网络环境。已切换至本地暂存文件')
        alias_data = await openfile(alias_file)
        if not alias_data:
            log.error('本地暂存别名文件为空，请自行使用浏览器访问 "https://api.yuzuchan.moe/maimaidx/maimaidxalias" 获取别名数据并保存在 "static/music_alias.json" 文件中并重启bot')
            raise ValueError

    total_alias_list = AliasList()
    for _a in filter(lambda x: mai.total_list.by_id(x['SongID']), alias_data):
        if (song_id := str(_a['SongID'])) in local_alias_data:
            _a['Alias'].extend(local_alias_data[song_id])
        total_alias_list.append(Alias(**_a))

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

    total_list: MusicList
    total_alias_list: AliasList
    hot_music_ids: List = []
    guess_data: List[Music]

    def __init__(self) -> None:
        """封装所有曲目信息以及猜歌数据，便于更新"""

    async def get_music(self) -> None:
        """获取所有曲目数据"""
        self.total_list = await get_music_list()

    async def get_music_alias(self) -> None:
        """获取所有曲目别名"""
        self.total_alias_list = await get_music_alias_list()

    def guess(self):
        """初始化猜歌数据"""
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


class Guess:

    Group: Dict[str, Union[GuessDefaultData, GuessPicData]] = {}

    def __init__(self) -> None:
        """猜歌类"""
        self.config: Dict[str, List[int]] = json.load(open(guess_file, 'r', encoding='utf-8'))
    
    async def start(self, gid: str):
        """开始猜歌"""
        self.Group[gid] = await self.guessData()

    async def startpic(self, gid: str):
        """开始猜曲绘"""
        self.Group[gid] = await self.guesspicdata()
        
    def calculate_frequency_weights(self, image: Image.Image) -> np.ndarray:
        gray_image = np.array(image.convert('L'))
        freq = np.fft.fft2(gray_image)
        freq_shift = np.fft.fftshift(freq)
        magnitude = np.abs(freq_shift)
        normalized_magnitude = magnitude / magnitude.max()
        weights = normalized_magnitude ** 2
        return weights
    
    def select_crop_region(weights: np.ndarray, crop_width: int, crop_height: int, top_p: int) -> Tuple[int, int]:
        h, w = weights.shape
        valid_regions = weights[:h - crop_height + 1, :w - crop_width + 1]
        flattened_weights = valid_regions.flatten()
        threshold = np.percentile(flattened_weights, top_p)
        valid_indices = np.where(flattened_weights >= threshold)[0]
        probabilities = flattened_weights[valid_indices]
        probabilities /= probabilities.sum()
        chosen_index = np.random.choice(valid_indices, p=probabilities)
        top_left_y = chosen_index // valid_regions.shape[1]
        top_left_x = chosen_index % valid_regions.shape[1]
        return top_left_x, top_left_y

    async def pic(self, music: Music) -> Image.Image:
        """裁切曲绘"""
        im = Image.open(await maiApi.download_music_pictrue(music.id))
        w, h = im.size
        weights = self.calculate_frequency_weights(im)
        scale = random.uniform(0.15, 0.4)  # 裁剪尺寸范围 可在此修改
        w2, h2 = int(w * scale), int(h * scale)
        top_p = min(1.3 - np.power(scale, 0.4), 0.95) * 100
        x, y = self.select_crop_region(weights, w2, h2, top_p)
        im = im.crop((x, y, x + w2, y + h2))
        return im

    async def guesspicdata(self) -> GuessPicData:
        """猜曲绘数据"""
        music = random.choice(mai.guess_data)
        pic = await self.pic(music)
        answer = mai.total_alias_list.by_id(music.id)[0].Alias
        answer.append(music.id)
        return GuessPicData(music=music, img=image_to_base64(pic), answer=answer, end=False)

    async def guessData(self) -> GuessDefaultData:
        """猜歌数据"""
        music = random.choice(mai.guess_data)
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
        pic = await self.pic(music)
        return GuessDefaultData(music=music, img=image_to_base64(pic), answer=answer, end=False, options=guess_options)

    def end(self, gid: str):
        """结束猜歌"""
        del self.Group[gid]

    async def on(self, gid: int) -> str:
        """开启猜歌"""
        if gid not in self.config['enable']:
            self.config['enable'].append(gid)
        if gid in self.config['disable']:
            self.config['disable'].remove(gid)
        await writefile(guess_file, self.config)
        return '群猜歌功能已开启'

    async def off(self, gid: int) -> str:
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

    config: Dict[str, Union[List[int], bool]]

    def __init__(self) -> None:
        """别名推送类"""
        self.config = json.load(open(group_alias_file, 'r', encoding='utf-8'))

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
