import math
from typing import overload

from ...constants import ACHIEVEMENT_LIST, BASE_RA_SPP


def get_base_ra(achievements: float) -> float:
    for i, threshold in enumerate(ACHIEVEMENT_LIST):
        if achievements < threshold:
            return BASE_RA_SPP[i]
    return BASE_RA_SPP[-1]


def calc_ds(rating: float, achievements: float) -> float:
    """
    计算谱面定数

    Params:
        `rating`: 底分
        `achievements`: 成绩
    Returns:
        `float`: 谱面定数
    """
    a = min(100.5, achievements) / 100
    return round(rating / (a * get_base_ra(achievements)), 1)


def dx_score(dx: int) -> int:
    """
    获取DX评分星星数量

    Params:
        `dx`: dx百分比
    Returns:
        `int` 返回星星数量
    """
    if dx <= 85:
        result = 0
    elif dx <= 90:
        result = 1
    elif dx <= 93:
        result = 2
    elif dx <= 95:
        result = 3
    elif dx <= 97:
        result = 4
    else:
        result = 5
    return result


@overload
def compute_rating(ds: float, achievement: float) -> int:
    """
    计算底分

    Params:
        `ds`: 定数
        `achievement`: 成绩
    Returns:
        返回底分
    """


@overload
def compute_rating(ds: float, achievement: float, *, onlyrate: bool = False) -> str:
    """
    计算底分

    Params:
        `ds`: 定数
        `achievement`: 成绩
        `onlyrate`: 是否只返回评价
    Returns:
        返回评价
    """


@overload
def compute_rating(
    ds: float, achievement: float, *, israte: bool = False
) -> tuple[int, str]:
    """
    计算底分

    Params:
        `ds`: 定数
        `achievement`: 成绩
        `israte`: 是否返回所有数据
    Returns:
        (底分, 评价)
    """


def compute_rating(
    ds: float, achievement: float, *, onlyrate: bool = False, israte: bool = False
) -> int | tuple[int, str]:
    if achievement < 50:
        base_rating = 7.0
        rate = "D"
    elif achievement < 60:
        base_rating = 8.0
        rate = "C"
    elif achievement < 70:
        base_rating = 9.6
        rate = "B"
    elif achievement < 75:
        base_rating = 11.2
        rate = "BB"
    elif achievement < 80:
        base_rating = 12.0
        rate = "BBB"
    elif achievement < 90:
        base_rating = 13.6
        rate = "A"
    elif achievement < 94:
        base_rating = 15.2
        rate = "AA"
    elif achievement < 97:
        base_rating = 16.8
        rate = "AAA"
    elif achievement < 98:
        base_rating = 20.0
        rate = "S"
    elif achievement < 99:
        base_rating = 20.3
        rate = "Sp"
    elif achievement < 99.5:
        base_rating = 20.8
        rate = "SS"
    elif achievement < 100:
        base_rating = 21.1
        rate = "SSp"
    elif achievement < 100.5:
        base_rating = 21.6
        rate = "SSS"
    else:
        base_rating = 22.4
        rate = "SSSp"

    if israte:
        data = (math.floor(ds * (min(100.5, achievement) / 100) * base_rating), rate)
    elif onlyrate:
        data = rate
    else:
        data = math.floor(ds * (min(100.5, achievement) / 100) * base_rating)

    return data
