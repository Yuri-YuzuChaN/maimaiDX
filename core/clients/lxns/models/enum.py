from enum import Enum, IntEnum


class LevelIndex(IntEnum):
    BASIC = 0
    ADVANCED = 1
    EXPERT = 2
    MASTER = 3
    RE_MASTER = 4


class FCType(str, Enum):
    APP = "app"
    AP = "ap"
    FCP = "fcp"
    FC = "fc"


class FSType(str, Enum):
    FSDP = "fsdp"
    FSD = "fsd"
    FSP = "fsp"
    FS = "fs"
    SYNC = "sync"


class RateType(str, Enum):
    SSSP = "sssp"
    SSS = "sss"
    SSP = "ssp"
    SS = "ss"
    SP = "sp"
    S = "s"
    AAA = "aaa"
    AA = "aa"
    A = "a"
    BBB = "bbb"
    BB = "bb"
    B = "b"
    C = "c"
    D = "d"


class SongType(str, Enum):
    STANDARD = "standard"
    DX = "dx"
    UTAGE = "utage"


class TrophyColor(str, Enum):
    NORMAL = "Normal"
    BRONZE = "Bronze"
    SILVER = "Silver"
    GOLD = "Gold"
    RAINBOW = "Rainbow"
