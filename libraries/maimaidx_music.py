import random
from typing import Dict, List, Optional, Union, Tuple, Any
from copy import deepcopy
from retrying import retry

import requests


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


class Chart(Dict):
    tap: Optional[int] = None
    slide: Optional[int] = None
    hold: Optional[int] = None
    touch: Optional[int] = None
    brk: Optional[int] = None
    charter: Optional[int] = None

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
            if not in_or_equal(music.genre, genre):
                continue
            if not in_or_equal(music.type, type):
                continue
            if not in_or_equal(music.bpm, bpm):
                continue
            if title_search is not Ellipsis and title_search.lower() not in music.title.lower():
                continue
            music.diff = diff2
            new_list.append(music)
        return new_list


@retry(stop_max_attempt_number=3)
def get_music_list():
    obj_data = requests.get('https://www.diving-fish.com/api/maimaidxprober/music_data')
    obj_stats = requests.get('https://www.diving-fish.com/api/maimaidxprober/chart_stats')
    if obj_data.status_code != 200 and obj_stats.status_code != 200:
        raise requests.RequestException('maimaiDX数据获取错误，请检查网络环境')
    data = obj_data.json()
    stats = obj_stats.json()
    _total_list: MusicList = MusicList(data)
    for __i in range(len(_total_list)):
        _total_list[__i] = Music(_total_list[__i])
        _total_list[__i]['stats'] = stats[_total_list[__i].id]
        for __j in range(len(_total_list[__i].charts)):
            _total_list[__i].charts[__j] = Chart(_total_list[__i].charts[__j])
            _total_list[__i].stats[__j] = Stats(_total_list[__i].stats[__j])
    return _total_list


total_list = get_music_list()
