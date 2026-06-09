from pydantic import BaseModel, field_validator

from .enum import FCType, FSType, LevelIndex, RateType, SongType, TrophyColor


class CollectionRequiredSong(BaseModel):
    id: int
    title: str
    type: SongType
    completed: bool | None = None
    completed_difficulties: list[LevelIndex]


class CollectionRequired(BaseModel):
    difficulties: list[LevelIndex] | None = None
    rate: RateType | None = None
    fc: FCType | None = None
    fs: FSType | None = None
    songs: list[CollectionRequiredSong] | None = None
    completed: bool | None = None

    @field_validator("fc", "fs", mode="before")
    @classmethod
    def to_none(cls, v: str):
        if v == "":
            return None
        return v


class Collection(BaseModel):
    id: int
    name: str
    color: TrophyColor | None = None
    description: str | None = None
    genre: str | None = None
    required: list[CollectionRequired] | None = None
