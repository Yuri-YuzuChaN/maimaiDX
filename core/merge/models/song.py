from typing import Literal

from pydantic import BaseModel

from ...clients.divingfish.models import Stats
from ...clients.lxns.models import LevelIndex, Notes


class Difficulties(BaseModel):
    level_index: LevelIndex
    level: str
    level_value: float
    note_designer: str
    notes: Notes
    dx_score: int
    stats: Stats | None = None


class SimpleSong(BaseModel):
    song_id: int
    version_str: str
    version_int: int = 0
    type: Literal["SD", "DX"]
    difficulties: Difficulties


class Song(BaseModel):
    song_id: int
    song_name: str
    artist: str
    genre: str
    bpm: float
    version_str: str
    version_int: int = 0
    type: Literal["SD", "DX"]
    isnew: bool = False
    difficulties: list[Difficulties] = []
    # 宴
    kanji: str | None = None
    description: str | None = None
    is_buddy: bool | None = None
