import time
import aiofiles
from pathlib import Path
import base64


def hash(qq: int):
    days = int(time.strftime("%d", time.localtime(time.time()))) + 31 * int(
        time.strftime("%m", time.localtime(time.time()))) + 77
    return (days * qq) >> 8


def render_forward_msg(msg_list: list, uid: int=10001, name: str='maimaiDX'):
    forward_msg = []
    for msg in msg_list:
        forward_msg.append({
            "type": "node",
            "data": {
                "name": str(name),
                "uin": str(uid),
                "content": msg
            }
        })
    return forward_msg


async def read_image(file: Path) -> str:
    async with aiofiles.open(file, 'rb') as f:
        _bytes = await f.read()
    base64_str = base64.b64encode(_bytes).decode()
    return 'base64://' + base64_str