from ..exceptions import HTTPError, TokenError, UserNotFoundError


class LXNSParamsError(HTTPError):
    """参数错误"""


class LXNSPermissionDeniedError(HTTPError):
    """权限不足"""


class LXNSNotFoundError(HTTPError):
    """未找到资源"""


class LXNSTooManyRequestsError(HTTPError):
    """过多的请求"""


class LXNSOAuthError(HTTPError):
    """OAuth2错误"""


class LXNSTokenError(TokenError):
    """用户Token错误"""


class LXNSUserNotFoundError(UserNotFoundError):
    """未找到用户"""
