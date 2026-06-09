from pydantic import BaseModel, ConfigDict, Field

from .enum import LevelIndex, SongType


class Notes(BaseModel):
    total: int
    tap: int
    hold: int
    slide: int
    touch: int
    brk: int = Field(alias="break")

    model_config = ConfigDict(populate_by_name=True)


class BuddyNotes(BaseModel):
    left: Notes
    right: Notes


class SongDifficulty(BaseModel):
    type: SongType
    difficulty: LevelIndex
    level: str
    level_value: float
    note_designer: str
    version: int
    notes: Notes


class SongDifficultyUtage(SongDifficulty):
    kanji: str
    description: str
    is_buddy: bool
    notes: Notes | BuddyNotes


class SongDifficulties(BaseModel):
    standard: list[SongDifficulty] = []
    dx: list[SongDifficulty] = []
    utage: list[SongDifficultyUtage] = []


class Song(BaseModel):
    id: int
    title: str
    artist: str
    genre: str
    bpm: int
    map: str | None = None
    version: int
    rights: str | None = None
    locked: bool | None = False
    disabled: bool | None = False
    difficulties: SongDifficulties


class Genre(BaseModel):
    id: int
    title: str
    genre: str


class Version(BaseModel):
    id: int
    title: str
    version: int


class Songs(BaseModel):
    songs: list[Song]
    genres: list[Genre]
    versions: list[Version]


class Alias(BaseModel):
    song_id: int
    aliases: list[str] = []


class Aliases(BaseModel):
    aliases: list[Alias]
