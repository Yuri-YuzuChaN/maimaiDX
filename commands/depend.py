from re import Match

from nonebot import NoneBot

from hoshino.typing import CQEvent

from ..config import maiconfig
from ..core.clients.exceptions import UserNotBindError
from ..core.database.qq import User, get_user, update_user
from ..core.merge.models import ServiceName, Song
from ..core.service import mai

AUTHORIZE_ERROR = (
    f"您尚未授权「{maiconfig.bot_name} BOT」"
    "访问您的落雪查分器数据，请先使用「lxbind」指令进行绑定。"
)


class GetUserModel:
    def __init__(
        self,
        auto_create: bool = True,
        check_auth: bool = False,
        check_skip: bool = False,
    ):
        """
        依赖注入类

        Params:
            `auto_create`: 自动创建用户数据
            `check_auth`: 是否检查落雪查分器 Token
            `check_skip`: 跳过是否存在用户检测
        """
        self.auto_create = auto_create
        self.check_auth = check_auth
        self.check_skip = check_skip

    async def __call__(self, bot: NoneBot, ev: CQEvent) -> User | None:
        user_id = ev.user_id
        user = None
        is_exist = False
        try:
            user = await get_user(user_id)
        except UserNotBindError:
            if self.auto_create:
                user = await update_user(user_id)

        if self.check_auth and user:
            if (
                user.service == ServiceName.LXNS
                and user.access_token is None
                and user.refresh_token is None
            ):
                if self.check_skip:
                    return None
                await bot.finish(ev, AUTHORIZE_ERROR, reply_message=True)
            is_exist = True

        if self.check_skip:
            if not is_exist:
                return None

        return user


GetOrCreateUser = GetUserModel(auto_create=True)
"""获取用户数据，不检查授权，若不存在直接创建"""
GetUserOrNone = GetUserModel(auto_create=False, check_skip=True)
"""获取用户数据，如不存在则返回`None`"""
GetUserAndAuth = GetUserModel(auto_create=True, check_auth=True)
"""获取用户数据，并检查是否授权，未授权则提示授权"""
GetUserAndAuthOrNone = GetUserModel(auto_create=True, check_auth=True, check_skip=True)
"""获取用户数据，如不存在则创建，并检查是否授权，未授权则返回`None`"""



async def process_regex(bot: NoneBot, ev: CQEvent) -> tuple[list[Song], int]:
    """
    查歌指令依赖注入函数，返回曲目列表以及页数

    Returns:
        `tuple[list[Song], int]`
    """
    match: Match[str] = ev["match"]
    raw_cmd = match.group(1)
    cmd = raw_cmd.lower() if raw_cmd is not None else None
    args = match.group(2)
    a_list = args.split() if args else []
    page = 1
    match cmd:
        case None:
            match a_list:
                case [name]:
                    title = name
                case [name, p_raw]:
                    title, page = name, int(p_raw)
                case _:
                    await bot.finish(
                        ev, 
                        "没有找到这样的乐曲。\n※ 如果是别名请使用「XXX是什么歌」指令进行查询哦。",
                        reply_message=True,
                    )
            result = mai.total_list.filter(title=title)
        case "定数":
            match a_list:
                case [ds]:
                    ds1 = ds2 = float(ds)
                case [ds1_raw, ds2_raw]:
                    ds1, ds2 = float(ds1_raw), float(ds2_raw)
                case [ds1_raw, ds2_raw, p_raw]:
                    ds1, ds2, page = float(ds1_raw), float(ds2_raw), int(p_raw)
                case _:
                    await bot.finish(
                        ev, 
                        (
                            "定数查歌参数错误，请输入正确格式，页数为可选：\n"
                            "定数查歌「定数」「页数」\n"
                            "定数查歌「最小定数」「最大定数」「页数」\n"
                        ),
                        reply_message=True,
                    )
            result = mai.total_list.filter(level_value=(ds1, ds2))
        case "bpm":
            match a_list:
                case [bpm_raw]:
                    result = mai.total_list.filter(bpm=float(bpm_raw))
                case [b1, b2]:
                    if float(b1) > float(b2):
                        page = int(b2)
                        result = mai.total_list.filter(bpm=float(b1))
                    else:
                        result = mai.total_list.filter(bpm=(float(b1), float(b2)))
                case [b1, b2, p_raw]:
                    result = mai.total_list.filter(bpm=(float(b1), float(b2)))
                    page = int(p_raw)
                case _:
                    await bot.finish(
                        ev, 
                        (
                            "bpm查歌参数错误，请输入正确格式，页数为可选：\n"
                            "bpm查歌「bpm」「页数」\n"
                            "bpm查歌「最小bpm」「最大bpm」「页数」\n"
                        ),
                        reply_message=True,
                    )
        case "曲师" | "谱师":
            match a_list:
                case [name]:
                    pass
                case [name, p_raw] if p_raw.isdigit():
                    page = int(p_raw)
                case _:
                    await bot.finish(
                        ev, 
                        (
                            f"{cmd}查歌参数错误，请输入正确格式，页数为可选：\n"
                            f"{cmd}查歌「{cmd}」「页数」"
                        ),
                        reply_message=True,
                    )
            if cmd == "曲师":
                result = mai.total_list.filter(artist=name)
            else:
                result = mai.total_list.filter(charter=name)
        case _:
            await bot.finish(ev, "指令错误", reply_message=True)

    return result, page
