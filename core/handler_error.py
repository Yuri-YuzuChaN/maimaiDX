import traceback
from functools import wraps
from textwrap import dedent

from hoshino.typing import MessageSegment

from ..config import log
from .clients.divingfish.exceptions import (
    DivingFishTokenDisableError,
    DivingFishTokenError,
    DivingFishTokenNotFoundError,
    DivingFishUserDisabledQueryError,
    DivingFishUserNotFoundError,
)
from .clients.exceptions import (
    MusicNotPlayError,
    NotMusicRecommendationError,
    UserNotExistsError,
)
from .clients.lxns.exceptions import (
    LXNSNotFoundError,
    LXNSOAuthError,
    LXNSParamsError,
    LXNSPermissionDeniedError,
    LXNSTokenError,
    LXNSTooManyRequestsError,
)

NOTFOUNDUSER = dedent("""
    未在水鱼查分器找到此玩家，请确保此玩家的用户名和查分器中的用户名相同。
    如未绑定，请前往查分器官网进行绑定。
    https://www.diving-fish.com/maimaidx/prober/
""").strip()


def handle_errors(func):
    @wraps(func)
    async def wrapper(*args, **kwargs) -> MessageSegment:
        try:
            return await func(*args, **kwargs)

        ### DivingFish
        except DivingFishUserNotFoundError:
            return MessageSegment.text(NOTFOUNDUSER)
        except UserNotExistsError:
            return MessageSegment.text("查询的用户不存在。")
        except DivingFishUserDisabledQueryError:
            return MessageSegment.text("该用户禁止了其他人获取数据或未同意用户协议。")
        except (
            DivingFishTokenDisableError,
            DivingFishTokenNotFoundError,
            DivingFishTokenError,
        ):
            log.error("水鱼开发者Token异常，请自行检查。")
            return MessageSegment.text(
                "请联系BOT管理员检查水鱼查分器相关信息，暂时无法查询。"
            )

        ### LXNS
        except LXNSTokenError:
            return MessageSegment.text("落雪查分器授权错误，请尝试重新绑定授权。")
        except LXNSPermissionDeniedError:
            return MessageSegment.text(
                "使用落雪查分器的权限不足，请联系BOT管理员检查相关信息。"
            )
        except LXNSNotFoundError:
            return MessageSegment.text(
                "未找到落雪查分器相关资源，请联系BOT管理员检查相关信息。"
            )
        except LXNSTooManyRequestsError:
            return MessageSegment.text("使用落雪查分器的请求次数过多，请稍后再试。")
        except LXNSParamsError:
            log.error(f"请求参数错误。\n{traceback.format_exc()}")
            return MessageSegment.text(
                "使用落雪查分器请求时发生错误，请联系BOT管理员检查相关信息。"
            )
        except LXNSOAuthError:
            return MessageSegment.text(
                "落雪查分器授权错误，请重试，依旧错误请重新绑定授权。"
            )

        ### 其它
        except MusicNotPlayError:
            return MessageSegment.text("您未游玩过曲目。")
        except NotMusicRecommendationError:
            return MessageSegment.text("没有乐曲推荐呢。可能是您太强了。")
        except Exception as e:
            log.error(f"发生错误: {traceback.format_exc()}")
            return MessageSegment.text(
                f"发生未知错误：{type(e).__name__}\n请联系BOT管理员。"
            )

    return wrapper
