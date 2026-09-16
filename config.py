from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from hoshino import priv
from hoshino.config import NICKNAME
from hoshino.service import Service

from .core.clients.divingfish.models.oauth import (
    DIVINGFISH_SCOPE_NAMES,
    DIVINGFISH_SCOPE_VALUES,
    DivingFishScope,
)
from .log import logger as log  # noqa: F401

SV_HELP = "请使用 帮助maimaiDX 查看帮助"
sv = Service("maimaiDX", manage_priv=priv.ADMIN, enable_on_default=True, help_=SV_HELP)


Root = Path(__file__).parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Root / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


class BaseConfig(Settings):
    maimaidx_path: str
    maimaidx_alias_proxy: bool = False
    maimaidx_alias_push: bool = True
    save_in_memory: bool | None = True
    assets_online: bool | None = True
    bot_name: str = (
        NICKNAME
        if isinstance(NICKNAME, str)
        else (list(NICKNAME)[0] if NICKNAME else "Sakura")
    )


class DivingFishConfig(Settings):
    divingfish_prober_proxy: bool = False
    divingfish_token: str | None = None
    divingfish_client_id: str | None = None
    divingfish_client_secret: str | None = None
    divingfish_auth_url: str = "https://auth.diving-fish.com"
    divingfish_scope: DivingFishScope = DivingFishScope.PROBER_RECORDS_READ

    @field_validator("divingfish_scope", mode="before")
    @classmethod
    def validate_divingfish_scope(cls, value: str) -> DivingFishScope:
        if isinstance(value, DivingFishScope):
            return value

        if isinstance(value, int):
            return DivingFishScope(value)

        if not isinstance(value, str):
            raise TypeError("divingfish_scope 必须是字符串或整数")

        value = value.strip()
        if not value:
            raise ValueError("divingfish_scope 不能为空")

        result = DivingFishScope(0)

        for name in value.split():
            scope = DIVINGFISH_SCOPE_VALUES.get(name)
            if scope is None:
                valid_names = ", ".join(DIVINGFISH_SCOPE_VALUES)
                raise ValueError(
                    f"未知的 DivingFish scope: {name!r}；可选值：{valid_names}"
                )
            result |= scope

        return result

    @property
    def divingfish_oauth_scope(self) -> str:
        return " ".join(
            name
            for scope, name in DIVINGFISH_SCOPE_NAMES.items()
            if self.divingfish_scope & scope
        )

    @property
    def oauth_enabled(self) -> bool:
        return bool(self.divingfish_client_id and self.divingfish_client_secret)


class LxnsConfig(Settings):
    lxns_dev_token: str | None = None
    lx_client_id: str | None = None
    lx_client_secret: str | None = None
    redirect_uri: str | None = None


maiconfig = BaseConfig()
dfconfig = DivingFishConfig()
lxnsconfig = LxnsConfig()
