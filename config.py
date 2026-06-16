from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

from hoshino import priv
from hoshino.config import NICKNAME
from hoshino.service import Service

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


class LxnsConfig(Settings):
    lxns_dev_token: str | None = None
    lx_client_id: str | None = None
    lx_client_secret: str | None = None
    redirect_uri: str | None = None


maiconfig = BaseConfig()
dfconfig = DivingFishConfig()
lxnsconfig = LxnsConfig()
