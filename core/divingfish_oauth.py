"""水鱼绑定里用户回填的那串确认码。

它长得和落雪的授权码一样（`XXXX-XXXX-XXXX`），靠格式区分不开两家，所以
「这串码该交给谁处理」由待回填会话记的服务决定，见 `pending_binding`。
"""

import re

#: 水鱼的确认码只用这 20 个字母：去掉了 A/E/I/O/U（避免随机拼出脏词）
#: 和形近的 0/1/L。用户要在聊天窗口里转发它，认错一个字符就白跑一趟
CONFIRMATION_ALPHABET = "BCDFGHJKLMNPQRSTVWXZ"
CONFIRMATION_CODE_LENGTH = 12
_BODY_PATTERN = re.compile(
    rf"^[{CONFIRMATION_ALPHABET}]{{{CONFIRMATION_CODE_LENGTH}}}$"
)
_PREFIX_PATTERN = re.compile(r"^(?:确认码|授权码)\s*[:：]?\s*(\S+)$")


def extract_confirmation_code(text: str) -> str | None:
    """从用户发来的整条消息里认出确认码，归一化成 `XXXX-XXXX-XXXX`

    用户会怎么发就怎么容错：小写、连字符丢了、复制时带上「确认码：」前缀
    或首尾空白。水鱼那边也做同一套归一化，这里再做一遍是为了在发请求之前
    先把明显不是码的消息挡掉——这条规则要过每一条群消息。

    只认「整条消息就是一串码」，不从一句话里抠。抠的话，一条正常聊天里
    恰好凑出十二个字母就会被当成码送去兑换。
    """
    value = (text or "").strip()
    prefixed = _PREFIX_PATTERN.fullmatch(value)
    if prefixed:
        value = prefixed.group(1)

    body = re.sub(r"[\s\-—_]", "", value).upper()
    if not _BODY_PATTERN.fullmatch(body):
        return None
    return "-".join(
        body[i:i + 4] for i in range(0, CONFIRMATION_CODE_LENGTH, 4)
    )
