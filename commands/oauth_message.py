from textwrap import dedent

from ..config import lxnsconfig, maiconfig
from ..core.lxns_oauth import (
    build_authorize_url,
)

# lxns
LXNS_AUTHORIZE_URL = build_authorize_url(
    lxnsconfig.lx_client_id or "", lxnsconfig.redirect_uri or ""
)
LXNS_AUTHORIZE_MSG = dedent(f"""
    请完成落雪查分器授权：

    1. 打开以下链接并允许「{maiconfig.bot_name} BOT」访问您的落雪查分器数据
    =======================
    {LXNS_AUTHORIZE_URL}
    =======================
    2. 授权完成后，复制页面显示的授权码
    3. 回到 QQ，直接发送授权码或完整回调链接

    本次绑定有效期为 10 分钟，授权码只能使用一次；
    超时或失效后请重新发送「lxbind」获取授权链接
    =======================
    请注意！！您必须在落雪查分器的
    「账号设置 -> 常规设置」中的
    「隐私设置」开启允许读取成绩，否
    则BOT将无法查询您的成绩
""").strip()

LXNS_ERROR = "BOT管理员尚未配置落雪查分器相关信息"
GROUP_BIND_GUIDE = (
    "BOT 管理员已将落雪绑定设置为仅私聊。\n"
    "请添加 Bot 为好友后，在私聊中发送「lxbind」开始绑定。\n"
    "部分 OneBot 实现无法接收陌生人的私聊消息；若没有响应，请先确认好友关系。"
)
INVALID_CODE_MSG = (
    "未识别到有效的落雪授权码。\n"
    "请发送授权页面显示的完整授权码，或直接粘贴完整回调链接。"
)
OAUTH_FAILED_MSG = (
    "落雪绑定失败：授权码可能已使用、已过期，或授权未成功。\n"
    "当前绑定会话仍有效，您可以发送新的授权码；"
    "如需重新授权，请再次发送「lxbind」。"
)
BINDING_TEMPORARY_FAILED_MSG = (
    "落雪绑定暂时失败：网络、响应数据或本地数据库出现异常。\n"
    "当前绑定会话仍有效，您可以稍后重新发送授权码；"
    "如果授权码已经使用，请再次发送「lxbind」重新授权。"
)

# diving-fish
DIVINGFISH_AUTHORIZE_MSG = dedent("""
    请完成水鱼查分器授权：

    1. 打开以下链接并登录水鱼账号，授权「{bot_name} BOT」访问您的水鱼查分器数据
    =======================
    {url}
    =======================
    2. 确认页面显示的绑定身份为「{label}」后点击「同意授权」
    3. 复制页面给出的确认码，回到 QQ 发送给 BOT

    本次绑定 {minutes} 分钟内有效，确认码只能使用一次；
    超时或失效后请重新发送「绑定水鱼」。
    =======================
    请注意！！链接与确认码都仅供您本人使用，请勿转发他人。
    确认码建议在与 BOT 的私聊中发送，避免被他人看到。
    如需取消授权，请前往 {revoke}
""").strip()
DIVINGFISH_OAUTH_ERROR = "BOT管理员尚未配置水鱼查分器 OAuth 应用，无法进行绑定授权。"
DIVINGFISH_BIND_FAILED_MSG = (
    "发起水鱼授权失败：水鱼账号服务可能暂时不可用，请稍后再试。"
)
DIVINGFISH_NO_SESSION_MSG = "请先发送「绑定水鱼」获取授权链接，完成授权后再发送确认码。"
DIVINGFISH_INVALID_CODE_MSG = (
    "未识别到有效的水鱼确认码。\n"
    "请发送授权完成页面显示的完整确认码，形如 BCDF-GHJK-LMNP。"
)
DIVINGFISH_CODE_FAILED_MSG = (
    "水鱼绑定失败：确认码可能已使用、已过期，或不是本次绑定的确认码。\n"
    "当前绑定会话仍有效，您可以发送新的确认码；"
    "如需重新授权，请再次发送「绑定水鱼」。"
)
DIVINGFISH_MISMATCH_MSG = (
    "水鱼绑定失败：这串确认码对应的授权不属于您的账号。\n"
    "确认码只能由发起绑定的本人使用，请勿使用他人转发给您的确认码。\n"
    "如需绑定自己的账号，请发送「绑定水鱼」重新走一遍授权。"
)
DIVINGFISH_BIND_SUCCESS_MSG = "水鱼查分器授权完成，现在可以直接使用查询指令了。"
DIVINGFISH_SESSION_TTL = 20 * 60
DIVINGFISH_CODE_TEMPORARY_FAILED_MSG = (
    "水鱼绑定暂时失败：水鱼账号服务或网络出现异常。\n"
    "当前绑定会话仍有效，您可以稍后重新发送确认码；"
    "如果确认码已经使用，请再次发送「绑定水鱼」重新授权。"
)
