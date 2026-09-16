from httpx import Response

from ....config import dfconfig
from ..exceptions import UnknownError, UserNotExistsError
from ..http import ApiClient
from .exceptions import (
    DivingFishNotAuthorizedError,
    DivingFishTokenDisableError,
    DivingFishTokenError,
    DivingFishTokenNotFoundError,
    DivingFishTooManyRequestsError,
    DivingFishUserDisabledQueryError,
    DivingFishUserNotFoundError,
)
from .models import PlayInfoDefault, PlayInfoDev, UserInfo, UserInfoDev, UserRanking
from .oauth import get_access_token


class DivingFishAPI(ApiClient):
    proxy_url = "https://proxy.yuzuchan.site"
    base_url = "https://maimai.diving-fish.com/api/maimaidxprober"

    def __init__(self, qqid: int | None = None, username: str | None = None):
        #: 授权模式下查谁由令牌决定，请求里不再携带 `qq`，也不需要开发者 token
        self.oauth = dfconfig.oauth_enabled and qqid is not None and not username
        super().__init__(
            base_url=self.base_url,
            headers=None
            if self.oauth or not dfconfig.divingfish_token
            else {"developer-token": dfconfig.divingfish_token},
        )
        self.qqid = qqid
        self._retried = False
        self.json = {}
        if qqid:
            self.json["qq"] = qqid
        if username:
            self.json["username"] = username
            self.json.pop("qq", None)

    def _handle_error(self, resp: Response):
        if resp.status_code == 200:
            return
        if resp.status_code == 400:
            self._handle_400(resp.json())
        elif resp.status_code == 401:
            raise DivingFishTokenError
        elif resp.status_code == 403:
            if self.oauth:
                raise DivingFishNotAuthorizedError
            raise DivingFishUserDisabledQueryError
        elif resp.status_code == 429:
            raise DivingFishTooManyRequestsError
        else:
            raise UnknownError

    def _handle_400(self, error: dict):
        msg = error.get("message") or error.get("msg")

        if msg is not None:
            match msg:
                case "no such user":
                    raise DivingFishUserNotFoundError
                case "user not exists":
                    raise UserNotExistsError
                case "开发者token有误":
                    raise DivingFishTokenError
                case "开发者token被禁用":
                    raise DivingFishTokenDisableError
                case "请先联系水鱼申请开发者token":
                    raise DivingFishTokenNotFoundError
                case _:
                    raise UnknownError

    async def _request_data(self, method: str, endpoint: str, **kwargs) -> dict | list:
        return await self._request(method, endpoint, **kwargs)

    async def _request_oauth(self, method: str, endpoint: str, **kwargs) -> dict | list:
        """代用户请求，令牌由水鱼账号按用户的授权范围签发"""
        self.headers["Authorization"] = f"Bearer {await get_access_token(self.qqid)}"
        return await self._request(method, endpoint, **kwargs)

    async def _on_unauthorized(self) -> bool:
        """令牌过期，重新换取一次"""
        if not self.oauth or self._retried:
            return False
        self._retried = True
        self.headers["Authorization"] = (
            f"Bearer {await get_access_token(self.qqid, refresh=True)}"
        )
        return True

    @classmethod
    def set_proxy(cls) -> None:
        cls.base_url = cls.proxy_url + "/maimaidxprober"

    async def music_data(self) -> list:
        """获取曲目数据"""
        return await self._request_data("GET", "/music_data")

    async def chart_stats(self) -> dict[str, dict[str, list[dict]]]:
        """获取单曲数据"""
        return await self._request_data("GET", "/chart_stats")

    async def query_user_b50(self) -> UserInfo:
        """
        获取玩家B50

        Returns:
            `UserInfo` b50数据模型
        """
        self.json["b50"] = True
        result = await self._request_data("POST", "/query/player", json=self.json)
        return UserInfo.model_validate(result)

    async def query_user_plate(self, version: list[str]) -> list[PlayInfoDefault]:
        """
        请求用户数据

        Params:
            `version`: 版本
        Returns:
            `List[PlayInfoDefault]` 数据列表
        """
        if self.oauth:
            result = await self._request_oauth(
                "POST", "/player/plate", json={"version": version}
            )
        else:
            self.json["version"] = version
            result = await self._request_data("POST", "/query/plate", json=self.json)

        return [PlayInfoDefault.model_validate(d) for d in result["verlist"]]

    async def query_user_records(self) -> UserInfoDev:
        """
        获取用户所有成绩

        Returns:
            `UserInfoDev` 用户信息
        """
        if self.oauth:
            result = await self._request_oauth("GET", "/player/records")
        else:
            result = await self._request_data(
                "GET", "/dev/player/records", params=self.json
            )
        return UserInfoDev.model_validate(result)

    async def query_user_record(
        self, *, song_id: str | int | list[str | int]
    ) -> list[PlayInfoDev]:
        """
        获取用户指定曲目成绩

        Params:
            `song_id`: 曲目id，可以为单个ID或者列表
        Returns:
            `List[PlayInfoDev]` 成绩列表
        """
        if not isinstance(song_id, list):
            song_id = [song_id]

        if self.oauth:
            result = await self._request_oauth(
                "POST", "/player/record", json={"music_id": song_id}
            )
        else:
            self.json["music_id"] = song_id
            result = await self._request_data(
                "POST", "/dev/player/record", json=self.json
            )
        if result == {}:
            return []

        return [PlayInfoDev.model_validate(d) for k, v in result.items() for d in v]

    async def rating_ranking(self) -> list[UserRanking]:
        """
        获取查分器排行榜

        Returns:
            `List[UserRanking]` 按`ra`从高到低排序后的查分器排行模型列表
        """
        result = await self._request_data("GET", "/rating_ranking")
        return sorted(
            [UserRanking.model_validate(u) for u in result],
            key=lambda x: x.ra,
            reverse=True,
        )
