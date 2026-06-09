from pydantic import BaseModel

from .song import Song


class GuessBase(BaseModel):
    song: Song
    img: str
    answer: list[str]
    end: bool = False


class GuessDefaultData(GuessBase):
    options: list[str]


class GuessPicData(GuessBase): ...


class Switch(BaseModel):
    enable: list[int] = []
    disable: list[int] = []


class GuessSwitch(Switch): ...
