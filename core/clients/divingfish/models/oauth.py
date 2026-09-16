from enum import IntFlag

from pydantic import BaseModel


class DivingFishScope(IntFlag):
    PROFILE = 1 << 0
    PROBER_PROFILE_READ = 1 << 1
    PROBER_RECORDS_READ = 1 << 2
    PROBER_RECORDS_WRITE = 1 << 3
    CHUNITHM_RECORDS_READ = 1 << 4
    CHUNITHM_RECORDS_WRITE = 1 << 5


DIVINGFISH_SCOPE_NAMES = {
    DivingFishScope.PROFILE: "profile",
    DivingFishScope.PROBER_PROFILE_READ: "prober.profile.read",
    DivingFishScope.PROBER_RECORDS_READ: "prober.records.read",
    DivingFishScope.PROBER_RECORDS_WRITE: "prober.records.write",
    DivingFishScope.CHUNITHM_RECORDS_READ: "chunithm.records.read",
    DivingFishScope.CHUNITHM_RECORDS_WRITE: "chunithm.records.write",
}

DIVINGFISH_SCOPE_VALUES = {
    name: scope for scope, name in DIVINGFISH_SCOPE_NAMES.items()
}


class DeviceAuthorization(BaseModel):
    """发起绑定后水鱼账号返回的授权信息"""

    device_code: str
    user_code: str
    verification_uri: str
    verification_uri_complete: str
    expires_in: int
    interval: int = 5


class AccessToken(BaseModel):
    """代用户访问的令牌，没有 `refresh_token`，过期后重新换取"""

    access_token: str
    token_type: str
    expires_in: int
    scope: str
    sub: str | None = None
