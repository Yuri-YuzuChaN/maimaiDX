from collections import namedtuple

from pydantic import BaseModel, Field


class Stats(BaseModel):
    cnt: float = 0
    diff: str = ""
    fit_diff: float = 0
    avg: float = 0
    avg_dx: float = 0
    std_dev: float = 0
    dist: list[int] = []
    fc_dist: list[float] = []


Notes1 = namedtuple("Notes", ["tap", "hold", "slide", "brk"])
Notes2 = namedtuple("Notes", ["tap", "hold", "slide", "touch", "brk"])


class Chart(BaseModel):
    notes: Notes1 | Notes2
    charter: str | None = None


class BasicInfo(BaseModel):
    title: str
    artist: str
    genre: str
    bpm: int
    release_date: str = ""
    version: str = Field(alias="from")
    is_new: bool


class Music(BaseModel):
    id: str
    title: str
    type: str
    ds: list[float]
    level: list[str]
    cids: list[int]
    charts: list[Chart]
    basic_info: BasicInfo
    stats: list[Stats] = []
    diff: list[int] = []
