from typing import Any

from httpx import Response

from ..exceptions import HTTPError


class RequestError(HTTPError):
    def __init__(self, response: Response):
        self.response = response
        data = self.data
        message = (
            data.get("message") or response.text or f"HTTP {response.status_code}"
        )
        super().__init__(message)

    @property
    def data(self) -> dict[str, Any]:
        try:
            data = self.response.json()
        except ValueError:
            data = {}

        if isinstance(data, dict):
            return data

        return {"message": str(data)}
