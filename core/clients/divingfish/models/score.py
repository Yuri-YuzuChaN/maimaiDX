from pydantic import BaseModel, Field


class RaMusic(BaseModel):
    id: str
    ds: float
    lv: str
    lvp: str
    type: str


class PlayInfo(BaseModel):
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


class ChartInfo(PlayInfo):
    level_label: str
    song_id: int


class Charts(BaseModel):
    sd: list[ChartInfo] = []
    dx: list[ChartInfo] = []


class _UserInfo(BaseModel):
    additional_rating: int | None
    nickname: str | None
    plate: str | None = None
    rating: int | None
    username: str | None


class UserInfo(_UserInfo):
    charts: Charts


class PlayInfoDefault(PlayInfo):
    song_id: int = Field(alias="id")
    table_level: list[int] = []


class PlayInfoDev(ChartInfo): ...


class PlanInfo(BaseModel):
    completed: PlayInfoDefault | PlayInfoDev = None
    unfinished: PlayInfoDefault | PlayInfoDev = None


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


##### Dev
class UserInfoDev(_UserInfo):
    records: list[PlayInfoDev] = []


##### Rank
class UserRanking(BaseModel):
    username: str
    ra: int
