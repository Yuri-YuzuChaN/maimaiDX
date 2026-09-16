"""水鱼查分器 OAuth。

BOT 只保管 `client_id` 与 `client_secret`，不保存任何用户令牌：

1. 用户发送「绑定水鱼」，BOT 带 `handoff=code` 发起绑定，把授权链接发给用户；
2. 用户在水鱼账号页面确认授权，页面给出一串一次性确认码；
3. 用户把确认码发回给 BOT，BOT 凭码兑换一次令牌，绑定即告完成；
4. 之后每次查询，BOT 用应用凭据换取该用户 5 分钟有效的 `access_token`。

**第 3 步不是多余的一道手续。** 发起绑定这个动作不需要任何凭据，谁都能拿
本 BOT 的 `client_id` 造一条绑定链接、填上自己的标识转发给别人；受害者点完
同意，造链接的人就绑上了对方的账号。确认码只出现在点同意那个人的浏览器里，
未经他发回来，绑定就完不成——所以这一步验的是「点同意的人」和「发起绑定的人」
是不是同一个。BOT 这边还要再验一次，见 `handler.complete_divingfish_binding`。

用户标识只以 `sha256("<client_id>:<QQ号>")` 的形式发送，水鱼服务端存的也是
这个摘要，因此 QQ 号不会离开 BOT。
"""

import json
from base64 import urlsafe_b64decode
from hashlib import sha256
from time import monotonic

from httpx import Response

from ....config import dfconfig
from ..http import ApiClient
from .exceptions import (
    DivingFishBindingMismatchError,
    DivingFishConfirmationCodeError,
    DivingFishNotAuthorizedError,
    DivingFishOAuthError,
    DivingFishTokenNotFoundError,
)
from .models import AccessToken, DeviceAuthorization

ON_BEHALF_OF_GRANT = "urn:diving-fish:params:oauth:grant-type:on-behalf-of"
CONFIRMATION_CODE_GRANT = "urn:diving-fish:params:oauth:grant-type:confirmation-code"
REVOKE_URL = "/apps"

#: 提前一点过期，避免令牌在请求途中失效
EXPIRES_MARGIN = 30


def subject_ref(qqid: int) -> str:
    """用户标识摘要，水鱼服务端用它定位授权过的账号"""
    return sha256(f"{dfconfig.divingfish_client_id}:{qqid}".encode()).hexdigest()


def token_subject(access_token: str) -> str | None:
    """读出 access token 里的 `sub`（水鱼用户 ID）。

    **只解不验。** 这串令牌是 BOT 刚从水鱼账号服务取回来的，用它比对
    「兑换出的账号」和「换票换到的账号」是不是同一个，属于自洽性检查，
    不是安全校验——真正的验签由资源服务器做。
    """
    try:
        payload = access_token.split(".")[1]
        padded = payload + "=" * (-len(payload) % 4)
        return json.loads(urlsafe_b64decode(padded)).get("sub")
    except (IndexError, ValueError):
        return None


def binding_label(qqid: int) -> str:
    """展示在授权页面上的绑定身份，用户凭它确认不是在给别人授权"""
    qq = str(qqid)
    if len(qq) <= 4:
        return f"QQ {qq}"
    return f"QQ {qq[:2]}{'*' * (len(qq) - 4)}{qq[-2:]}"


class TokenCache:
    def __init__(self) -> None:
        self._tokens: dict[str, tuple[str, float]] = {}

    def get(self, ref: str) -> str | None:
        cached = self._tokens.get(ref)
        if cached is None:
            return None
        token, expires_at = cached
        if expires_at <= monotonic():
            del self._tokens[ref]
            return None
        return token

    def set(self, ref: str, token: AccessToken) -> None:
        expires_at = monotonic() + max(token.expires_in - EXPIRES_MARGIN, 0)
        self._tokens[ref] = (token.access_token, expires_at)

    def discard(self, ref: str) -> None:
        self._tokens.pop(ref, None)


tokens = TokenCache()


class DivingFishOAuth(ApiClient):
    def __init__(self):
        super().__init__(base_url=dfconfig.divingfish_auth_url.rstrip("/"))
        self.client_id = dfconfig.divingfish_client_id
        self.client_secret = dfconfig.divingfish_client_secret

    async def device_authorization(self, qqid: int) -> DeviceAuthorization:
        """发起绑定，返回给用户点开的授权链接

        顺带丢掉缓存的令牌：绑定到另一个账号后，旧令牌仍会在缓存里存活到过期，
        那段时间查出来的还是上一个账号的成绩
        """
        tokens.discard(subject_ref(qqid))
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "scope": dfconfig.divingfish_oauth_scope,
            "subject_ref": subject_ref(qqid),
            "binding_label": binding_label(qqid),
            # 改由用户回填确认码收尾。带上它之后 device_code 换不到令牌，
            # 这正是它的意义所在，理由见模块开头
            "handoff": "code",
        }
        result = await self._request_data(
            "POST", "/oauth/device_authorization", data=data
        )
        return DeviceAuthorization.model_validate(result)

    async def redeem(self, qqid: int, confirmation_code: str) -> AccessToken:
        """用用户发回来的确认码兑换一次令牌

        一并送上这个 QQ 的标识，让水鱼比对它和发起绑定时提交的是不是同一个，
        也就是「回填这串码的人，是不是发起绑定的那个人」。对不上时水鱼回
        `invalid_grant` 且**不消费这串码**——那种情况多半是用户把别人转发来
        的码当成了自己的，烧掉它等于让码的主人从头再走一遍绑定。
        """
        data = {
            "grant_type": CONFIRMATION_CODE_GRANT,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "confirmation_code": confirmation_code,
            "subject_ref": subject_ref(qqid),
        }
        result = await self._request_data("POST", "/oauth/token", data=data)
        return AccessToken.model_validate(result)

    async def fetch_token(self, qqid: int) -> AccessToken:
        """换取代该用户访问的令牌"""
        data = {
            "grant_type": ON_BEHALF_OF_GRANT,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "subject": f"ref:{subject_ref(qqid)}",
            "scope": dfconfig.divingfish_oauth_scope,
        }
        result = await self._request_data("POST", "/oauth/token", data=data)
        return AccessToken.model_validate(result)

    async def _request_data(self, method: str, endpoint: str, **kwargs) -> dict:
        return await self._request(method, endpoint, **kwargs)

    def _handle_error(self, resp: Response) -> None:
        if resp.status_code == 200:
            return
        if not dfconfig.oauth_enabled:
            raise DivingFishTokenNotFoundError

        error = ""
        try:
            error = resp.json().get("error", "")
        except ValueError:
            pass

        if error == "consent_required":
            raise DivingFishNotAuthorizedError
        if error == "subject_mismatch":
            # 码是真的，但不是发给这个 QQ 的——他多半把别人转发来的码
            # 当成了自己的。水鱼在这种情况下不会消费掉那串码
            raise DivingFishBindingMismatchError
        if error == "invalid_grant":
            # 码不存在、已过期、已用过、出自别的应用，水鱼一律回这一个错，
            # 不作区分。对用户来说下一步动作都一样：重新发起一次绑定
            raise DivingFishConfirmationCodeError
        raise DivingFishOAuthError


async def get_access_token(qqid: int, *, refresh: bool = False) -> str:
    """取该用户的令牌，命中缓存则直接复用

    Params:
        `qqid`: 用户QQ
        `refresh`: 丢弃缓存重新换取
    """
    ref = subject_ref(qqid)
    if refresh:
        tokens.discard(ref)
    elif token := tokens.get(ref):
        return token

    result = await DivingFishOAuth().fetch_token(qqid)
    tokens.set(ref, result)
    return result.access_token
