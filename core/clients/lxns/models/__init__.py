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
    "CollectionRequiredSong",
    "CollectionRequired",
    "Collection",
    "FCType",
    "FSType",
    "LevelIndex",
    "RateType",
    "SongType",
    "TrophyColor",
    "Alias",
    "Aliases",
    "BuddyNotes",
    "Genre",
    "Notes",
    "SongDifficulty",
    "SongDifficultyUtage",
    "SongDifficulties",
    "Song",
    "Songs",
    "Version",
    "BaseToken",
    "OAuth2Token",
    "Player",
    "AllPerfect50",
    "BaseScore",
    "Best50",
    "RatingTrend",
    "Score",
]
