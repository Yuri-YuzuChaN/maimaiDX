import json
import random, aiohttp, os

import aiofiles
from PIL import Image
from typing import Dict, List, Optional, Union, Tuple, Any
from copy import deepcopy
from retrying import retry
from collections import defaultdict

from .image import image_to_base64
from .. import static, aliases_csv

hot_music_ids = ['17', '56', '62', '66', '70', '71', '100', '101', '107', '109', '115', '117', '122', '143', '187', '188', '189', '193', '198', '199', '200', '201', '204', '223', '226', '227', '229', '230', '233', '258', '261', '268', '269', '282', '283', '295', '299', '315', '322', '324', '327', '337', '339', '348', '360', '364', '365', '366', '374', '379', '381', '384', '386', '387', '388', '389', '390', '399', '400', '411', '417', '419', '421', '422', '426', '427', '431', '432', '438', '439', '446', '447', '448', '456', '457', '462', '464', '465', '467', '471', '488', '490', '492', '494', '495', '496', '507', '508', '510', '511', '513', '520', '521', '531', '532', '535', '540', '541', '542', '548', '552', '553', '555', '556', '561', '566', '567', '568', '571', '573', '574', '580', '581', '587', '589', '592', '603', '606', '610', '614', '621', '625', '626', '627', '628', '631', '632', '643', '646', '647', '648', '649', '655', '664', '670', '672', '673', '674', '682', '688', '689', '690', '691', '693', '694', '699', '700', '701', '705', '707', '708', '709', '710', '711', '717', '719', '720', '725', '726', '731', '736', '738', '740', '741', '742', '746', '750', '756', '757', '759', '760', '763', '764', '766', '771', '772', '773', '777', '779', '781', '782', '786', '789', '791', '793', '794', '796', '797', '798', '799', '802', '803', '806', '809', '812', '815', '816', '818', '820', '823', '825', '829', '830', '832', '833', '834', '835', '836', '837', '838', '839', '840', '841', '844', '848', '849', '850', '852', '853', '10363', '11002', '11003', '11004', '11005', '11006', '11007', '11008', '11010', '11014', '11015', '11016', '11017', '11018', '11019', '11020', '11021', '11022', '11023', '11024', '11025', '11026', '11027', '11028', '11029', '11030', '11031', '11032', '11034', '11035', '11036', '11037', '11038', '11043', '11044', '11045', '11046', '11047', '11048', '11049', '11050', '11051', '11052', '11058', '11059', '11060', '11061', '11064', '11065', '11067', '11069', '11070', '11073', '11075', '11078', '11080', '11081', '11083', '11084', '11085', '11086', '11087', '11088', '11089', '11090', '11091', '11092', '11093', '11094', '11095', '11096', '11097', '11098', '11099', '11101', '11102', '11103', '11104', '11105', '11106', '11107', '11109', '11110', '11113', '11114', '11115', '11116', '11121', '11122', '11123', '11124', '11125', '11126', '11127', '11128', '11129', '11131', '11132', '11133', '11134', '11135', '11136', '11137', '11138', '11139', '11140', '11141', '11142', '11143', '11146', '11147', '11148', '11149', '11150', '11151', '11206']
cover_dir = os.path.join(static, 'mai', 'cover')


def cross(checker: List[Any], elem: Optional[Union[Any, List[Any]]], diff):
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
                return True, [_j]
    return ret, diff_ret


def in_or_equal(checker: Any, elem: Optional[Union[Any, List[Any]]]):
    if elem is Ellipsis:
        return True
    if isinstance(elem, List):
        return checker in elem
    elif isinstance(elem, Tuple):
        return elem[0] <= checker <= elem[1]
    else:
        return checker == elem


class Stats(Dict):
    count: Optional[int] = None
    avg: Optional[float] = None
    sss_count: Optional[int] = None
    difficulty: Optional[str] = None
    rank: Optional[int] = None
    total: Optional[int] = None

    def __getattribute__(self, item):
        try:
            if item == 'sss_count':
                return self['sssp_count']
            elif item == 'rank':
                return self['v'] + 1
            elif item == 'total':
                return self['t']
            elif item == 'difficulty':
                return self['tag']
            elif item in self:
                return self[item]
            return super().__getattribute__(item)
        except KeyError:
            return 'Unknown'


class Chart(Dict):
    tap: Optional[int] = None
    slide: Optional[int] = None
    hold: Optional[int] = None
    touch: Optional[int] = None
    brk: Optional[int] = None
    charter: Optional[str] = None

    def __getattribute__(self, item):
        if item == 'tap':
            return self['notes'][0]
        elif item == 'hold':
            return self['notes'][1]
        elif item == 'slide':
            return self['notes'][2]
        elif item == 'touch':
            return self['notes'][3] if len(self['notes']) == 5 else 0
        elif item == 'brk':
            return self['notes'][-1]
        elif item in self:
            return self[item]
        return super().__getattribute__(item)


class Music(Dict):
    id: Optional[str] = None
    title: Optional[str] = None
    ds: Optional[List[float]] = None
    level: Optional[List[str]] = None
    genre: Optional[str] = None
    type: Optional[str] = None
    bpm: Optional[float] = None
    version: Optional[str] = None
    is_new: Optional[bool] = None
    charts: Optional[List[Chart]] = None
    stats: Optional[List[Stats]] = None
    release_date: Optional[str] = None
    artist: Optional[str] = None

    diff: List[int] = []

    def __getattribute__(self, item):
        if item in {'genre', 'artist', 'release_date', 'bpm', 'version', 'is_new'}:
            if item == 'version':
                return self['basic_info']['from']
            return self['basic_info'][item]
        elif item in self:
            return self[item]
        return super().__getattribute__(item)


def search_charts(checker: List[Chart], elem: str, diff):
    ret = False
    diff_ret = []
    if not elem or elem is Ellipsis:
        return True, diff
    for _j in (range(len(checker)) if diff is Ellipsis else diff):
        if elem.lower() in checker[_j].charter.lower():
            diff_ret.append(_j)
            ret = True
    return ret, diff_ret


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
            if not in_or_equal(music.genre, genre):
                continue
            if not in_or_equal(music.type, type):
                continue
            if not in_or_equal(music.bpm, bpm):
                continue
            if title_search is not Ellipsis and title_search.lower() not in music.title.lower():
                continue
            if artist_search is not Ellipsis and artist_search.lower() not in music.artist.lower():
                continue
            music.diff = diff2
            new_list.append(music)
        return new_list

def get_cover_len4_id(mid: str) -> str:
    mid = int(mid)

    if 10001 <= mid:
        mid -= 10000
    
    return f'{mid:04d}'

# @retry(stop_max_attempt_number=3)
async def get_music_list() -> MusicList:
    """
    获取所有数据
    """
    root_path = os.path.dirname(os.path.dirname(__file__))
    async with aiohttp.request("GET", 'https://www.diving-fish.com/api/maimaidxprober/music_data') as obj_data:
        if obj_data.status != 200:
            # raise aiohttp.ClientResponseError('maimaiDX曲目数据获取失败，请检查网络环境')
            print('maimaiDX曲目数据获取失败，请检查网络环境。已切换至本地暂存文件')
            async with aiofiles.open(os.path.join(root_path, 'music_data.json'), 'r', encoding='utf-8') as f:
                data = json.loads(await f.read())
        else:
            data = await obj_data.json()
            async with aiofiles.open(os.path.join(root_path, 'music_data.json'), 'w', encoding='utf-8') as f:
                await f.write(json.dumps(data, ensure_ascii=False, indent=4))
    async with aiohttp.request("GET", 'https://www.diving-fish.com/api/maimaidxprober/chart_stats') as obj_stats:
        if obj_stats.status != 200:
            # raise aiohttp.ClientResponseError('maimaiDX数据获取错误，请检查网络环境')
            print('maimaiDX数据获取错误，请检查网络环境。已切换至本地暂存文件')
            async with aiofiles.open(os.path.join(root_path, 'chart_stats.json'), 'r', encoding='utf-8') as f:
                stats = json.loads(await f.read())
        else:
            stats = await obj_stats.json()
            async with aiofiles.open(os.path.join(root_path, 'chart_stats.json'), 'w', encoding='utf-8') as f:
                await f.write(json.dumps(stats, ensure_ascii=False, indent=4))

    total_list: MusicList = MusicList(data)
    for i in range(len(total_list)):
        total_list[i] = Music(total_list[i])
        total_list[i]['stats'] = stats[total_list[i].id]
        for j in range(len(total_list[i].charts)):
            total_list[i].charts[j] = Chart(total_list[i].charts[j])
            total_list[i].stats[j] = Stats(total_list[i].stats[j])
    return total_list

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

    def aliases(self):
        """
        初始化所有别名数据
        """
        self.music_aliases, self.music_aliases_reverse, self.music_aliases_lines = self.__music_aliases__()

    def __music_aliases__(self):
        _music_aliases = defaultdict(list)
        _music_aliases_reverse = defaultdict(list)
        with open(os.path.join(static, 'aliases.csv'), 'r', encoding='utf-8') as f:
            _music_aliases_lines = [l for l in f.readlines() if l.strip()]
        for l in _music_aliases_lines:
            arr = l.strip().split('\t')
            for i in range(len(arr)):
                if arr[i] != '':
                    _music_aliases[arr[i].lower()].append(arr[0])
                    _music_aliases_reverse[arr[0]].append(arr[i].lower())
        return _music_aliases, _music_aliases_reverse, _music_aliases_lines

    def save_aliases(self, data: str):
        with open(aliases_csv, 'w', encoding='utf-8') as f:
            f.write(data)
        self.aliases()

    def guess(self):
        """
        初始化猜歌数据
        """
        self.guess_data = list(filter(lambda x: x['id'] in hot_music_ids, mai.total_list))

    def start(self):
        """
        开始猜歌
        """
        self.music = Music(random.choice(self.guess_data))
        self.guess_options = [
            f'的 Expert 难度是 {self.music["level"][2]}',
            f'的 Master 难度是 {self.music["level"][3]}',
            f'的分类是 {self.music["basic_info"]["genre"]}',
            f'的版本是 {self.music["basic_info"]["from"]}',
            f'的艺术家是 {self.music["basic_info"]["artist"]}',
            f'{"不" if self.music["type"] == "SD" else ""}是 DX 谱面',
            f'{"没" if len(self.music["ds"]) == 4 else ""}有白谱',
            f'的 BPM 是 {self.music["basic_info"]["bpm"]}'
        ]
        self.guess_options = random.sample(self.guess_options, 6)
        pngPath = os.path.join(cover_dir, f'{get_cover_len4_id(int(self.music["id"]))}.jpg')
        if not os.path.exists(pngPath):
            pngPath = os.path.join(cover_dir, f'{get_cover_len4_id(int(self.music["id"]))}.png')
        if not os.path.exists(pngPath):
            pngPath = os.path.join(cover_dir, '1000.png')
        img = Image.open(pngPath)
        w, h = img.size
        w2, h2 = int(w / 3), int(h / 3)
        l, u = random.randrange(0, int(2 * w / 3)), random.randrange(0, int(2 * h / 3))
        img = img.crop((l, u, l+w2, u+h2))
        self.b64image = image_to_base64(img)
        self.is_end = False

mai = MaiMusic()
