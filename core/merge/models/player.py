from pydantic import BaseModel

from ...clients.lxns.models import Collection


class LxnsPlayer(BaseModel):
    friend_code: int = 0
    class_rank: int = 0
    star: int | None = None
    trophy: Collection | None = None
    icon: Collection | None = None
    frame: Collection | None = None
    upload_time: str | None = None


class Player(LxnsPlayer):
    name: str
    """name / nickname"""
    rating: int
    """rating"""
    course_rank: int = 0
    """course rank / additional rating"""
    name_plate: Collection | str | None = None
    """name plate / plate"""
