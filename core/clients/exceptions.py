class HTTPError(Exception):
    """有关HTTP请求的基类异常"""


class TokenError(HTTPError):
    """Token错误或失效"""


class ServerError(HTTPError):
    """服务器错误"""


######
class PlayerDataError(Exception):
    """有关玩家数据的基类异常"""


class UserNotFoundError(PlayerDataError):
    """未找到用户"""


class MusicNotPlayError(PlayerDataError):
    """未游玩曲目"""


class NotMusicRecommendationError(PlayerDataError):
    """没有乐曲推荐"""


class UserNotExistsError(PlayerDataError):
    """用户不存在"""


######
class UnknownError(Exception):
    """通用异常，未知错误"""


class UserNotBindError(PlayerDataError):
    """用户未绑定"""
