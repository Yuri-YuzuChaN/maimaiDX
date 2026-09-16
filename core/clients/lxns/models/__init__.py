from .base import APIResult
from .collection import Collection, CollectionRequired, CollectionRequiredSong
from .enum import FCType, FSType, LevelIndex, RateType, SongType, TrophyColor
from .music import (
    Alias,
    Aliases,
    BuddyNotes,
    Genre,
    Notes,
    Song,
    SongDifficulties,
    SongDifficulty,
    SongDifficultyUtage,
    Songs,
    Version,
)
from .oauth import BaseToken, OAuth2Token
from .player import Player
from .score import AllPerfect50, BaseScore, Best50, RatingTrend, Score

__all__ = [
    "APIResult",
    "Alias",
    "Aliases",
    "AllPerfect50",
    "BaseScore",
    "BaseToken",
    "Best50",
    "BuddyNotes",
    "Collection",
    "CollectionRequired",
    "CollectionRequiredSong",
    "FCType",
    "FSType",
    "Genre",
    "LevelIndex",
    "Notes",
    "OAuth2Token",
    "Player",
    "RateType",
    "RatingTrend",
    "Score",
    "Song",
    "SongDifficulties",
    "SongDifficulty",
    "SongDifficultyUtage",
    "SongType",
    "Songs",
    "TrophyColor",
    "Version",
]
