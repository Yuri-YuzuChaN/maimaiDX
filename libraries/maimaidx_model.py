from collections import namedtuple
from typing import List, Optional, Union

from pydantic import BaseModel, Field


##### Music
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

    notes: Union[Notes1, Notes2]
    charter: str = None


class BasicInfo(BaseModel):

    title: str
    artist: str
    genre: str
    bpm: int
    release_date: Optional[str] = ''
    version: str = Field(alias='from')
    is_new: bool


class Music(BaseModel):

    id: str
    title: str
    type: str
    ds: List[float]
    level: List[str]
    cids: List[int]
    charts: List[Chart]
    basic_info: BasicInfo
    stats: Optional[List[Optional[Stats]]] = []
    diff: Optional[List[int]] = []


class RaMusic(BaseModel):
    
    id: str
    ds: float
    lv: str
    lvp: str
    type: str


##### Aliases
class Alias(BaseModel):

    SongID: int
    Name: str
    Alias: List[str]


##### Guess
class GuessData(BaseModel):
    
    music: Music
    img: str
    answer: List[str]
    end: bool = False


class GuessDefaultData(GuessData):
    
    options: List[str]


class GuessPicData(GuessData): ...


##### Best50
class ChartInfo(BaseModel):
    
    achievements: float
    ds: float
    dxScore: int
    fc: Optional[str] = ''
    fs: Optional[str] = ''
    level: str
    level_index: int
    level_label: str
    ra: int
    rate: str
    song_id: int
    title: str
    type: str


class Data(BaseModel):

    sd: Optional[List[ChartInfo]] = None
    dx: Optional[List[ChartInfo]] = None


class UserInfo(BaseModel):

    additional_rating: Optional[int]
    charts: Optional[Data]
    nickname: Optional[str]
    plate: Optional[str] = None
    rating: Optional[int]
    username: Optional[str]
    
    
##### PlayedInfo
class PlayInfo(BaseModel):
    
    achievements: float
    fc: str = ''
    fs: str = ''
    level: str
    level_index: int
    title: str
    type: str
    ds: float = 0
    dxScore: int = 0
    ra: int = 0
    rate: str = ''


class PlayInfoDefault(PlayInfo):
    
    song_id: int = Field(alias='id')


class PlayInfoDev(PlayInfo):
    
    level_label: str
    song_id: int


class TableData(BaseModel):
    
    achievements: float
    fc: str = ''


class PlanInfo(BaseModel):
    
    completed: Union[PlayInfoDefault, PlayInfoDev] = None
    unfinished: Union[PlayInfoDefault, PlayInfoDev] = None