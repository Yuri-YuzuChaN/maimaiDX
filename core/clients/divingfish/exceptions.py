from ..exceptions import HTTPError, PlayerDataError, TokenError, UserNotFoundError


class DivingFishUserNotFoundError(UserNotFoundError):
    """水鱼查分器未找到该用户"""


class DivingFishUserDisabledQueryError(PlayerDataError):
    """用户关闭协议"""


class DivingFishTokenDisableError(HTTPError):
    """Token被禁用"""


class DivingFishTokenNotFoundError(HTTPError):
    """Token未找到"""


class DivingFishTokenError(TokenError):
    """Token错误"""


class DivingFishNotAuthorizedError(PlayerDataError):
    """用户未授权BOT访问水鱼查分器数据"""


class DivingFishTooManyRequestsError(HTTPError):
    """请求次数超出配额"""


class DivingFishOAuthError(HTTPError):
    """水鱼查分器 OAuth 请求失败"""


class DivingFishConfirmationCodeError(HTTPError):
    """确认码无效、已过期或已被使用"""


class DivingFishBindingMismatchError(HTTPError):
    """兑换出的授权不属于发起本次绑定的那个 QQ"""
