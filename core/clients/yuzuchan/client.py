from typing import Any, overload

from httpx import Response

from ....config import maiconfig
from ....constants import UUID
from ..exceptions import ServerError, UnknownError
from ..http import ApiClient
from .exceptions import RequestError
from .models import Alias, AliasStatus, MessageResult, Songs, StatusEnum

DOMAIN_NAME = "cn" if maiconfig.maimaidx_alias_proxy else "moe"
BASE_URL = f"https://www.yuzuchan.{DOMAIN_NAME}/api/v2"
JSONData = dict[str, Any] | list[Any]


class YuzuChaNAPI(ApiClient):
    def __init__(self):
        super().__init__(base_url=BASE_URL)
        self.music_endpoint = "/maimaidx/music"
        self.aliases_endpoint = "/aliases/maimaidx"

    def _handle_error(self, resp: Response) -> None:
        if 200 <= resp.status_code < 300:
            return
        if 400 <= resp.status_code < 500:
            raise RequestError(resp)
        if 500 <= resp.status_code < 600:
            raise ServerError()

        raise UnknownError()

    async def _request_data(
        self, method: str, endpoint: str, *, accept_message: bool = False, **kwargs
    ) -> JSONData:
        try:
            return await self._request(method, endpoint, **kwargs)
        except RequestError as e:
            if accept_message:
                return e.data
            raise

    @staticmethod
    def _is_message_result(data: JSONData) -> bool:
        return isinstance(data, dict) and "message" in data

    async def get_plate_json(self) -> dict[str, list[int]]:
        """获取所有版本牌子完成需求"""
        return await self._request_data("GET", self.music_endpoint + "/get_plate")

    @overload
    async def get_aliases(self) -> list[Alias]: ...
    @overload
    async def get_aliases(self, *, name: str) -> Alias | MessageResult: ...
    @overload
    async def get_aliases(self, *, song_id: int) -> Alias | MessageResult: ...

    async def get_aliases(
        self, *, name: str | None = None, song_id: int | None = None
    ) -> list[Alias] | Alias | MessageResult:
        if name is not None:
            result = await self._request_data(
                "GET",
                self.aliases_endpoint + "/aliases",
                accept_message=True,
                params={"name": name},
            )
        elif song_id is not None:
            result = await self._request_data(
                "GET",
                self.aliases_endpoint + "/aliases",
                accept_message=True,
                params={"song_id": song_id},
            )
        else:
            result = await self._request_data("GET", self.aliases_endpoint + "/aliases")

        if self._is_message_result(result):
            return MessageResult.model_validate(result)

        return (
            [Alias.model_validate(r) for r in result]
            if isinstance(result, list)
            else Alias.model_validate(result)
        )

    async def get_songs(self, name: str) -> Songs | MessageResult:
        result = await self._request_data(
            "GET",
            self.aliases_endpoint + "/songs",
            accept_message=True,
            params={"name": name},
        )
        if self._is_message_result(result):
            return MessageResult.model_validate(result)

        return Songs.model_validate(result)

    async def get_status(self) -> list[AliasStatus]:
        result = await self._request_data(
            "GET",
            self.aliases_endpoint + "/votes",
            params={"status": StatusEnum.ONGOING.value},
        )
        return [AliasStatus.model_validate(r) for r in result]

    async def post_alias(
        self, song_id: int, alias_name: str, user_id: int, group_id: int
    ) -> MessageResult:
        """
        提交别名申请

        Params:
            `id`: 曲目 `id`
            `alias_name`: 别名
            `user_id`: 提交的用户
        Returns:
            `MessageResult`
        """
        json = {
            "song_id": song_id,
            "apply_alias": alias_name,
            "apply_uid": user_id,
            "group_id": group_id,
            "ws_uuid": str(UUID),
        }
        result = await self._request_data(
            "POST",
            self.aliases_endpoint + "/apply",
            accept_message=True,
            json=json,
        )
        return MessageResult.model_validate(result)

    async def post_agree_user(self, tag: str, user_id: int) -> MessageResult:
        """
        提交同意投票

        Params:
            `tag`: 标签
            `user_id`: 同意投票的用户
        Returns:
            `MessageResult`
        """
        json = {"tag": tag, "agree_user": user_id}
        result = await self._request_data(
            "POST",
            self.aliases_endpoint + "/votes",
            accept_message=True,
            json=json,
        )
        return MessageResult.model_validate(result)
