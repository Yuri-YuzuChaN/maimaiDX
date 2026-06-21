from httpx import Response

from ....config import lxnsconfig
from ...database.qq import update_user
from ..exceptions import UnknownError
from ..http import ApiClient
from .exceptions import (
    LXNSNotFoundError,
    LXNSOAuthError,
    LXNSParamsError,
    LXNSPermissionDeniedError,
    LXNSTokenError,
    LXNSTooManyRequestsError,
)
from .models import (
    Aliases,
    APIResult,
    BaseToken,
    Best50,
    Collection,
    LevelIndex,
    OAuth2Token,
    Player,
    RatingTrend,
    Score,
    Song,
    Songs,
    SongType,
)


class OAuth2(ApiClient):
    def __init__(self):
        super().__init__(
            base_url="https://maimai.lxns.net",
        )
        self.client_id = lxnsconfig.lx_client_id
        self.client_secret = lxnsconfig.lx_client_secret
        self.redirect_uri = lxnsconfig.redirect_uri
        self.token: OAuth2Token | BaseToken | None = None

    async def fetch_token(self, code: str) -> OAuth2Token:
        """通过授权码获取 `access_token`"""
        json = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.redirect_uri,
        }
        result = await self._request_data("POST", "/api/v0/oauth/token", json=json)
        self.token = OAuth2Token.model_validate(result)
        return self.token

    async def refresh_token(self) -> OAuth2Token:
        if not self.token:
            raise LXNSTokenError

        json = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "refresh_token",
            "refresh_token": self.token.refresh_token,
        }
        result = await self._request_data("POST", "/api/v0/oauth/token", json=json)
        self.token = OAuth2Token.model_validate(result)
        return self.token

    async def _request_data(self, method: str, endpoint: str, **kwargs) -> dict:
        return await self._request(method, endpoint, **kwargs)

    def _handle_error(self, resp: Response) -> None:
        if resp.status_code == 200:
            return
        elif resp.status_code == 401:
            raise LXNSTokenError
        else:
            raise LXNSOAuthError


class LxnsClient(ApiClient):
    def __init__(
        self,
        *,
        base_url: str,
        headers: dict[str, str],
        user_id: str,
        token: OAuth2Token | BaseToken | None = None,
    ):
        super().__init__(base_url=base_url, headers=headers)
        self.user_id = user_id
        self._token = token
        self._friend_code: int | None = None

    async def _on_unauthorized(self) -> bool:
        """
        刷新 token
        """
        if not self._token:
            return False

        oauth = OAuth2()
        oauth.token = self._token

        try:
            new_token = await oauth.refresh_token()
            await update_user(self.user_id, token=new_token)
        except Exception:
            self._token = None
            return False

        self._token = new_token
        self.headers["Authorization"] = (
            f"{new_token.token_type} {new_token.access_token}"
        )

        self._friend_code = None

        return True

    def _handle_error(self, resp: Response):
        match resp.status_code:
            case 200:
                return
            case 400:
                raise LXNSParamsError
            case 401:
                self._friend_code = None
                raise LXNSOAuthError
            case 403:
                raise LXNSPermissionDeniedError
            case 404:
                raise LXNSNotFoundError
            case 429:
                raise LXNSTooManyRequestsError
            case _:
                raise UnknownError

    async def _request_data(self, method: str, endpoint: str, **kwargs) -> APIResult:
        data = await self._request(method, endpoint, **kwargs)
        return APIResult.model_validate(data)

    async def _request_base_data(self, method: str, endpoint: str, **kwargs) -> dict:
        return await self._request(method, endpoint, **kwargs)


class LxnsAPI:
    def __init__(
        self, user_id: str | None = None, token: OAuth2Token | BaseToken | None = None
    ):
        self._oauth_client = (
            LxnsClient(
                base_url="https://maimai.lxns.net/api/v0/user/maimai/player",
                headers={"Authorization": f"Bearer {token.access_token}"},
                user_id=user_id,
                token=token,
            )
            if token
            else None
        )

        self._dev_client = LxnsClient(
            base_url="https://maimai.lxns.net/api/v0/maimai",
            headers={"Authorization": lxnsconfig.lxns_dev_token},
            user_id=user_id,
            token=None,
        )

    async def music_data(self) -> Songs:
        """获取曲目数据"""
        result = await self._dev_client._request_base_data(
            "GET", "/song/list", params={"notes": True}
        )
        return Songs.model_validate(result)

    async def single_music_data(self, song_id: str) -> Song:
        """获取单个曲目数据"""
        result = await self._dev_client._request_base_data("GET", f"/song/{song_id}")
        return Song.model_validate(result)

    async def music_alias_data(self) -> Aliases:
        """获取别名列表"""
        result = await self._dev_client._request_base_data("GET", "/alias/list")
        return Aliases.model_validate(result)

    async def player(
        self, *, friend_code: int | None = None, qq: int | None = None
    ) -> Player:
        """获取玩家信息"""

        if friend_code is not None:
            result = await self._dev_client._request_data(
                "GET", f"/player/{friend_code}"
            )
        elif qq is not None:
            result = await self._dev_client._request_data("GET", f"/player/qq/{qq}")
        else:
            result = await self._oauth_client._request_data("GET", "")

        return Player.model_validate(result.data)

    async def single_best(
        self, song_id: int, level_index: LevelIndex, song_type: SongType
    ) -> Score:
        """
        获取曲目指定难度成绩
        """
        params = {
            "song_id": song_id,
            "level_index": level_index.value,
            "song_type": song_type.value,
        }
        result = await self._oauth_client._request_data("GET", "/best", params=params)
        return Score.model_validate(result.data)

    async def best50(self) -> Best50:
        """
        获取 `b50`
        """
        result = await self._oauth_client._request_data("GET", "/bests")
        return Best50.model_validate(result.data)

    async def ap50(self, friend_code: int) -> Best50:
        """
        获取 `ap50`
        """
        result = await self._dev_client._request_data(
            "GET", f"/player/{friend_code}/bests/ap"
        )
        return Best50.model_validate(result.data)

    async def song_bests(self, song_id: int, song_type: SongType) -> list[Score]:
        """
        获取指定曲目所有难度成绩
        """
        params = {"song_id": song_id, "song_type": song_type.value}
        result = await self._oauth_client._request_data("GET", "/bests", params=params)
        return [Score.model_validate(s) for s in result.data]

    async def recent50(self) -> list[Score]:
        """
        获取最近游玩的 50 个成绩
        """
        result = await self._oauth_client._request_data("GET", "/recents")
        return [Score.model_validate(s) for s in result.data]

    async def all_best(self) -> list[Score]:
        """
        获取所有成绩
        """
        result = await self._oauth_client._request_data("GET", "/scores")
        return [Score.model_validate(s) for s in result.data]

    async def heatmap(self) -> dict[str, int]:
        """
        获取玩家上传热力图
        """
        result = await self._oauth_client._request_data("GET", "/heatmap")
        return result.data

    async def trend(self, version: int) -> list[RatingTrend]:
        """
        获取玩家 DX Rating 趋势
        """
        params = {"version": version}
        result = await self._oauth_client._request_data("GET", "/trend", params=params)
        return [RatingTrend.model_validate(s) for s in result.data]

    async def history(
        self, song_id: int, song_type: SongType, level_index: LevelIndex
    ) -> list[Score]:
        """
        获取玩家成绩游玩历史记录
        """
        params = {
            "song_id": song_id,
            "song_type": song_type.value,
            "level_index": level_index.value,
        }
        result = await self._oauth_client._request_data(
            "GET", "/score/history", params=params
        )
        return [Score.model_validate(s) for s in result.data]

    async def collection(self, collection_type: str, collection_id: int) -> Collection:
        """
        获取玩家收藏品进度
        """
        result = await self._oauth_client._request_data(
            "GET", f"/{collection_type}/{collection_id}"
        )
        return Collection.model_validate(result.data)
