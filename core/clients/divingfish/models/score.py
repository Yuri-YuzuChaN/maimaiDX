from pydantic import BaseModel


class Record(BaseModel):
    achievements: float
    fc: str = ""
    fs: str = ""
    level: str
    level_index: int
    title: str
    type: str
    ds: float = 0
    dxScore: int = 0
    ra: int = 0
    rate: str = ""
    level_label: str
    song_id: int


class Charts(BaseModel):
    sd: list[Record] = []
    dx: list[Record] = []


class BaseUser(BaseModel):
    additional_rating: int | None
    nickname: str | None
    plate: str | None = None
    rating: int | None
    username: str | None


class UserInfo(BaseUser):
    charts: Charts


class RiseScore(BaseModel):
    song_id: int
    title: str
    type: str
    level_index: int
    ds: float
    ra: int
    rate: str
    achievements: float
    oldra: int = 0
    oldrate: str = "D"
    oldachievements: float = 0


class UserAllRecords(BaseUser):
    records: list[Record] = []


class UserRanking(BaseModel):
    username: str
    ra: int
