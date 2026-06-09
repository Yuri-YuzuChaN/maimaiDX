from pydantic import BaseModel, field_validator

from .enum import FCType, FSType, LevelIndex, RateType, SongType


class BaseScore(BaseModel):
    id: int
    song_name: str
    level: str
    level_index: LevelIndex
    fc: FCType | None = None
    fs: FSType | None = None
    rate: RateType | None = None
    type: SongType

    @field_validator("fc", "fs", mode="before")
    @classmethod
    def to_none(cls, v: str):
        if not v:
            return None
        return v


class Score(BaseScore):
    achievements: float
    dx_score: int
    dx_star: int
    dx_rating: float | None = None
    play_time: str | None = None
    upload_time: str | None = None
    last_played_time: str | None = None


class RatingTrend(BaseModel):
    total: int
    standard: int
    dx: int
    date: str


class Best50(BaseModel):
    standard_total: int
    dx_total: int
    standard: list[Score]
    dx: list[Score]


class AllPerfect50(Best50): ...
