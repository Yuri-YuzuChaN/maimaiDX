import math
import random
import time

from hoshino.typing import MessageSegment

from ..constants import (
    ACHIEVEMENT_LIST,
    ALL_VERSION,
    COMBO_PLUS,
    COMBO_SP,
    DX_CN_VERSION,
    LEVEL_INDEX_MAP,
    RANK_PLUS,
    SYNC_D_SP,
    SYNC_PLUS,
    SYNC_SP,
    VERSION_MAP,
)
from .clients.divingfish.client import DivingFishAPI
from .clients.exceptions import MusicNotPlayError, NotMusicRecommendationError
from .clients.lxns.client import LxnsAPI, OAuth2
from .clients.lxns.models import BaseToken, OAuth2Token, SongType
from .database.qq import User, update_user
from .handler_error import handle_errors
from .image import (
    DrawPlateProgress,
    DrawPlateTable,
    DrawRatingTable,
    DrawScore,
    PlayerBest50,
    image_to_base64,
    song_chart_banquet_info,
    song_chart_info,
    song_global_data,
    song_list,
    song_play_data,
    text_to_image,
    tricolor_gradient_prism_plus,
)
from .merge.models import (
    Best50,
    Category,
    NotPlayedResult,
    PlayedResult,
    Player,
    RiseResult,
    ServiceName,
    Song,
    Theme,
)
from .merge.play_result import df_to_playresult, lxns_to_playresult
from .merge.player import df_to_best50, df_to_player, lxns_to_best50
from .service import mai
from .utils.calc import compute_rating

MESSAGE = "可使用「主题」指令更换主题，「数据源」指令更换指定查分器。"

PLAN_MAP: dict[str, tuple[int, int | float]] = {
    **{p: (0, ACHIEVEMENT_LIST[i - 1]) for i, p in enumerate(RANK_PLUS)},
    **{p: (1, i) for i, p in enumerate(COMBO_PLUS)},
    **{p: (2, i) for i, p in enumerate(SYNC_PLUS)},
}
RISE_ACHIEVEMENT_LIST = ACHIEVEMENT_LIST[-4:]


def get_rows(count: int, row_size: int) -> int:
    if count == 0:
        return 0
    return (count + row_size - 1) // row_size


def get_token(user: User) -> BaseToken:
    """
    获取用户 token

    Params:
        `user`: 用户 `User` 模型
    Returns:
        `BaseToken`
    """
    return BaseToken(access_token=user.access_token, refresh_token=user.refresh_token)


async def get_friend_code(
    qqid: int,
    token: OAuth2Token | BaseToken,
) -> int:
    """
    获取好友码

    Params:
        `qqid`: 用户QQ
        `token`: 用户 `token`
    Returns:
        `int`
    """
    api = LxnsAPI(qqid, token=token)
    player = await api.player()
    return player.friend_code


async def bind_lxns(user: User, code: str) -> str:
    """
    绑定落雪查分器

    Params:
        `user`: 用户 `User` 模型
        `code`: 授权码
    Returns:
        `str`
    """
    oauth = OAuth2()
    token = await oauth.fetch_token(code)
    friend_code = await get_friend_code(user.qqid, token)
    update = await update_user(user.qqid, friend_code=friend_code, token=token)
    if update is None:
        result = "数据库错误。"
    else:
        result = "授权完成。"
    return result


async def get_best50(
    user: User, *, username: str | None = None, all_perfect: bool = False
) -> tuple[Player, Best50]:
    """
    获取用户 Best50 数据

    Params:
        `user`: 用户 `User` 模型
        `username`: 用户名（仅Diving-Fish）
        `all_perfect`: 绘制AP（仅LXNS）
    Returns:
        `tuple[Player, Best50]`
    """

    if username or user.service == ServiceName.DIVINGFISH:
        api = DivingFishAPI(user.qqid, username)
        userinfo = await api.query_user_b50()
        player = df_to_player(userinfo)
        best50 = df_to_best50(userinfo)
    elif user.service == ServiceName.LXNS:
        token = get_token(user)
        api = LxnsAPI(user.qqid, token)
        player = await api.player()
        if all_perfect:
            obj = await api.ap50(player.friend_code)
        else:
            obj = await api.best50()
        best50 = lxns_to_best50(obj)
    else:
        raise ValueError

    return player, best50


async def get_player_result(
    user: User, version: list[str] | None = None
) -> list[PlayedResult]:
    """
    获取游玩成绩

    Params:
        `user`: 用户 `User` 模型
        `version`: 版本列表（仅DivingFish）
    Returns:
        `list[PlayedResult]`
    """
    if user.service == ServiceName.DIVINGFISH:
        api = DivingFishAPI(qqid=user.qqid)
        if version is not None:
            data = await api.query_user_plate(version)
        else:
            result = await api.query_user_get_dev()
            data = result.records
        play_result = df_to_playresult(data)
    elif user.service == ServiceName.LXNS:
        token = get_token(user)
        api = LxnsAPI(user.qqid, token)
        data = await api.all_best()
        play_result = lxns_to_playresult(data)
    else:
        raise ValueError
    return play_result


def get_rise_score_list(
    old_records: dict[tuple[int, int], PlayedResult],
    type: SongType,
    play_result: list[PlayedResult],
    level: str | None = None,
    score: int | None = None,
) -> tuple[list[RiseResult], int]:
    """
    随机获取加分曲目

    Params:
        `type`: 版本
        `info`: 游玩成绩列表
        `level`: 等级
        `score`: 分数
    Returns:
        `Tuple[List[RiseScore], int]`
    """
    if not play_result:
        return [], 0

    lowest_ra = play_result[-1].rating
    lowest_level = play_result[-1].level

    lowest_level_index = LEVEL_INDEX_MAP[lowest_level]
    new_level_index = LEVEL_INDEX_MAP[level] if level else lowest_level_index

    if lowest_level_index > new_level_index:
        return [], 0

    target_rise = score or 1

    ignored_song_ids = {p.song_id for p in play_result if p.achievements >= 100.5}

    max_ra_coefficient = ACHIEVEMENT_LIST[-1] / 100 * 22.4
    min_ds = math.ceil((lowest_ra + target_rise) / max_ra_coefficient * 10) / 10
    ds = None if level is not None else (min_ds, min_ds + 1)

    new_version = list(DX_CN_VERSION.values())[-1][-1]

    version = (
        new_version
        if type == SongType.DX
        else ALL_VERSION[: ALL_VERSION.index(new_version)]
    )

    songs = mai.total_list.filter(
        level=level, level_value=ds, version_str=version, all_diff=False
    )
    rise_result: list[RiseResult] = []

    for song in songs:
        song_id = song.song_id
        if song_id >= 100000 or song_id in ignored_song_ids:
            continue
        for diff in song.difficulties:
            if level and LEVEL_INDEX_MAP[diff.level] > new_level_index:
                continue

            old_result = old_records.get((song_id, diff.level_index))
            old_ra = max(old_result.rating, lowest_ra) if old_result else 0

            for achievements in RISE_ACHIEVEMENT_LIST:
                new_ra, new_rate = compute_rating(
                    diff.level_value, achievements, israte=True
                )

                if old_result is None:
                    if new_ra <= lowest_ra:
                        continue
                    rise = RiseResult(
                        song_id=song_id,
                        song_name=song.song_name,
                        level_index=diff.level_index,
                        type=song.type,
                        rating=new_ra,
                        achievements=achievements,
                        rate=new_rate.lower(),
                        level_value=diff.level_value,
                    )
                    rise_result.append(rise)
                    break

                if new_ra - old_ra < target_rise:
                    continue

                rise = RiseResult(
                    song_id=song_id,
                    song_name=song.song_name,
                    level_index=diff.level_index,
                    type=song.type,
                    rating=new_ra,
                    achievements=achievements,
                    rate=new_rate.lower(),
                    level_value=diff.level_value,
                    old_rating=old_result.rating,
                    old_achievements=old_result.achievements,
                    old_rate=old_result.rate.value if old_result.rate else "D",
                )
                rise_result.append(rise)
                break

    sampled = random.sample(rise_result, min(len(rise_result), 5))
    sampled.sort(key=lambda x: x.level_value, reverse=True)

    return sampled, lowest_ra


async def draw_song_galobal_data(song: Song, level_index: int) -> MessageSegment:
    """
    绘制谱面数据

    Params:
        `song`: 曲目
        `level_index`: 等级索引
    Returns:
        `MessageSegment`
    """
    image = await song_global_data(song, level_index)
    return MessageSegment.image(image)


def draw_rating_table_text(rating: str) -> MessageSegment:
    """
    绘制只有等级文本的定数表

    Params:
        `rating`: 定数
    Returns:
        `MessageSegment`
    """
    table = DrawRatingTable(rating, level_text=True)
    image = table.draw()
    return MessageSegment.image(image)


def draw_song_list(songs: list[Song], page: int) -> MessageSegment:
    """
    绘制曲目列表

    Params:
        `songs`: 曲目列表
    Returns:
        `MessageSegment`
    """
    image = song_list(songs, page)
    return MessageSegment.image(image)


@handle_errors
async def draw_best50(
    user: User,
    *,
    username: str | None = None,
    icon: str | None = None,
    all_perfect: bool = False,
) -> MessageSegment:
    """
    绘制best50

    Params:
        `user`: 用户 `User` 模型
        `username`: 用户名
        `icon`: 头像
        `all_perfect`: 绘制AP（仅LXNS）
    Returns:
        `MessageSegment`
    """
    player, best50 = await get_best50(user, username=username, all_perfect=all_perfect)
    b50 = PlayerBest50(user, player=player, best50=best50, is_username=bool(username))
    return MessageSegment.image(await b50.draw()) + MessageSegment.text(MESSAGE)


@handle_errors
async def draw_play_data(user: User, song: Song) -> MessageSegment:
    """
    绘制单曲游玩成绩

    Params:
        `user`: 用户 `User` 模型
        `song`: 曲目
        `service`: 数据源
    Returns:
        `MessageSegment`
    """
    if user.service == ServiceName.DIVINGFISH:
        api = DivingFishAPI(qqid=user.qqid)
        data = await api.query_user_post_dev(song_id=song.song_id)
        if not data:
            raise MusicNotPlayError

        play_result = df_to_playresult(data, song=song)
    elif user.service == ServiceName.LXNS:
        token = get_token(user)
        api = LxnsAPI(user.qqid, token)
        if song.song_id < 10000:
            song_type = SongType.STANDARD
        elif song.song_id < 100000:
            song_type = SongType.DX
        else:
            song_type = SongType.UTAGE
        song_id = song.song_id % 10000

        data = await api.song_bests(song_id, song_type)
        if not data:
            raise MusicNotPlayError

        play_result = lxns_to_playresult(data, song=song)
    else:
        raise ValueError

    image = song_play_data(user.service, user.theme, song=song, play_result=play_result)
    return MessageSegment.image(image) + MessageSegment.text(MESSAGE)


@handle_errors
async def get_mai_what(user: User) -> Song | None:
    """"""
    player, best50 = await get_best50(user)
    r = random.randint(0, 1)
    _ra = 0
    ignore = []
    if r == 0:
        if sd := best50.sd:
            ignore = [m.song_id for m in sd if m.achievements < 100.5]
            _ra = sd[-1].rating
    else:
        if dx := best50.dx:
            ignore = [m.song_id for m in dx if m.achievements < 100.5]
            _ra = dx[-1].rating
    if _ra != 0:
        ds = round(_ra / 22.4, 1)
        music_list = mai.total_list.filter(level_value=(ds, ds + 1))
        music_list = [m for m in music_list if int(m.song_id) not in ignore]
        if not music_list:
            return None
        return random.choice(music_list)
    return None


@handle_errors
async def draw_chart_info(song: Song, user: User | None = None) -> MessageSegment:
    """
    绘制谱面信息

    Params:
        `song`: 曲目
        `user`: 用户 `User` 模型
    Returns:
        `MessageSegment`
    """
    if song.song_id < 100000:
        calc = False
        is_full = False
        best_list = []
        if user is not None:
            theme = user.theme
            try:
                if user.service == ServiceName.DIVINGFISH:
                    api = DivingFishAPI(qqid=user.qqid)
                    userinfo = await api.query_user_b50()
                    best50 = df_to_best50(userinfo)
                    calc = True
                elif user.service == ServiceName.LXNS:
                    token = get_token(user)
                    api = LxnsAPI(user.qqid, token)
                    best50 = lxns_to_best50(await api.best50())
                    calc = True
                else:
                    raise ValueError

                if calc:
                    if song.isnew:
                        best_list = best50.dx
                        is_full = bool(len(best_list) == 15)
                    else:
                        best_list = best50.sd
                        is_full = bool(len(best_list) == 35)
            except Exception:
                calc = False
        else:
            theme = Theme.PRISM_PLUS

        image = song_chart_info(song, calc, is_full, best_list, theme)
    else:
        image = song_chart_banquet_info(song)
    return MessageSegment.image(image) + MessageSegment.text(MESSAGE)


@handle_errors
async def draw_rating_table(
    user: User, rating: str, plan: bool = False
) -> MessageSegment:
    """
    绘制定数表

    Params:
        `user`: 用户 `User` 模型
        `rating`: 定数
        `plan`: 指定计划
    Returns:
        `MessageSegment`
    """
    play_result = await get_player_result(user)
    table = DrawRatingTable(
        rating, service=user.service, play_result=play_result, plan=plan
    )
    image = table.draw()
    return MessageSegment.image(image)


@handle_errors
async def draw_plate_table(
    user: User,
    version: str,
    plan: str,
    page: int,
) -> MessageSegment:
    """
    绘制完成表

    Params:
        `user`: 用户 `User` 模型
        `version`: 版本
        `plan`: 指定计划
        `page`: 页数
    Returns:
        `MessageSegment`
    """
    _version, version_name = VERSION_MAP.get(version)
    play_result = await get_player_result(user, _version)
    table = DrawPlateTable(
        user.service,
        play_result,
        plan=plan,
        version=version,
        version_name=version_name,
        page=page,
    )
    image = table.draw()
    return MessageSegment.image(image)


@handle_errors
async def draw_plate_progress(
    user: User,
    version: str,
    plan: str,
    page: int,
) -> MessageSegment:
    """
    绘制牌子完成进度

    Params:
        `user`: 用户 `User` 模型
        `version`: 版本
        `plan`: 指定计划
        `page`: 页数
    Returns:
        `MessageSegment`
    """
    _version, version_name = VERSION_MAP.get(version)
    play_result = await get_player_result(user, _version)
    table = DrawPlateProgress(
        user.service,
        play_result,
        plan=plan,
        version=version,
        version_name=version_name,
        page=page,
    )
    image = table.draw()
    return MessageSegment.image(image)


@handle_errors
async def draw_rise_score_list(
    user: User,
    level: str | None = None,
    score: int | None = None,
) -> MessageSegment:
    """
    绘制上分推荐表

    Params:
        `user`: 用户 `User` 模型
        `username`: 查分器用户名
        `level`: 定数
        `score`: 分数
    Returns:
        `MessageSegment`
    """
    player, best50 = await get_best50(user)
    play_result = await get_player_result(user)

    old_records = {(v.song_id, v.level_index): v for v in play_result}

    sd, sd_low_score = get_rise_score_list(
        old_records, SongType.STANDARD, best50.sd, level, score
    )
    dx, dx_low_score = get_rise_score_list(
        old_records, SongType.DX, best50.dx, level, score
    )

    if not sd and not dx:
        raise NotMusicRecommendationError

    background_bg = tricolor_gradient_prism_plus(1400, 960)
    ds = DrawScore(user.service, background_bg)

    image = ds.draw_rise(sd, sd_low_score, dx, dx_low_score, 960)

    return MessageSegment.image(image)


@handle_errors
async def draw_level_progress(
    user: User, level: str, plan: str, category: Category, page: int = 1
) -> MessageSegment:
    """
    绘制谱面等级进度

    Params:
        `user`: 用户 `User` 模型
        `level`: 定数
        `plan`: 评价等级
        `category`: 指定进度
        `page`: 页数
    Returns:
        `MessageSegment`
    """
    play_result = await get_player_result(user)
    played_map: dict[tuple[int, int], PlayedResult] = {
        (r.song_id, r.level_index): r for r in play_result if r.level == level
    }
    plan_type, plan_value = PLAN_MAP[plan]

    def check_status(res: PlayedResult) -> bool:
        if plan_type == 0:  # Achievement
            return res.achievements >= plan_value
        if plan_type == 1:  # Combo
            return bool(res.fc and COMBO_SP.index(res.fc) >= plan_value)
        if plan_type == 2:  # Sync
            if not res.fs:
                return False
            if res.fs in SYNC_D_SP:
                return SYNC_D_SP.index(res.fs) >= plan_value
            if res.fs in SYNC_SP:
                return SYNC_SP.index(res.fs) >= plan_value
            return False
        return False

    completed: list[PlayedResult] = []
    unfinished: list[PlayedResult] = []
    notplayed: list[NotPlayedResult] = []

    music_list = mai.total_list.by_plan(level)
    for song_id, difficulties in music_list.items():
        for _d in difficulties:
            res = played_map.get((song_id, _d.level_index))
            if res:
                if check_status(res):
                    completed.append(res)
                else:
                    unfinished.append(res)
            else:
                notplayed.append(
                    NotPlayedResult(
                        level_value=_d.level_value,
                        song_id=song_id,
                        level_index=_d.level_index,
                    )
                )

    sort_key = {0: "achievements", 1: "fc", 2: "fs"}.get(plan_type, "achievements")
    sort_default = 0 if plan_type == 0 else ""

    def _sort_value(res: PlayedResult):
        value = getattr(res, sort_key)
        return value if value is not None else sort_default

    completed.sort(key=_sort_value, reverse=True)
    unfinished.sort(key=_sort_value, reverse=True)
    notplayed.sort(key=lambda x: x.level_value, reverse=True)

    def get_played_rows(count: int) -> int:
        return max(4, get_rows(count, 5))

    def get_notplayed_rows(count: int) -> int:
        return max(4, get_rows(count, 20))

    if category == Category.DEFAULT:
        comp_limit = 60 if not unfinished and not notplayed else 30
        c_row = len(completed[:comp_limit])
        c_y = get_played_rows(c_row) * 109 + 140
        u_row = len(unfinished[:30])
        u_y = get_played_rows(u_row) * 109 + 140
        n_row = len(notplayed[:100])
        n_y = get_notplayed_rows(n_row) * 65 + 140

        background_bg = tricolor_gradient_prism_plus(1400, 150 + c_y + u_y + n_y)
        ds = DrawScore(user.service, background_bg)
        image = ds.draw_plan(
            level, completed, c_y, unfinished, u_y, notplayed, plan, comp_limit
        )
    elif category in [Category.COMPLETED, Category.UNFINISHED]:
        data = completed if category == Category.COMPLETED else unfinished
        per_page = 80
        total_page = max(1, (len(data) - 1) // per_page + 1)
        page = max(1, min(page, total_page))

        display_data = data[(page - 1) * per_page : page * per_page]
        y_size = get_played_rows(len(display_data)) * 109
        background_bg = tricolor_gradient_prism_plus(1400, 240 + y_size + 120)
        ds = DrawScore(user.service, background_bg)
        image = ds.draw_category(category, data, page, total_page)

    else:
        y_size = get_notplayed_rows(len(notplayed)) * 65
        height = 240 + y_size + 120
        if height < 600:
            height = 600
        background_bg = tricolor_gradient_prism_plus(1400, height)
        ds = DrawScore(user.service, background_bg)
        image = ds.draw_category(category, notplayed)

    return MessageSegment.image(image)


@handle_errors
async def draw_level_score_list(
    user: User,
    rating: str | float,
    page: int = 1,
) -> MessageSegment:
    """
    绘制分数列表

    Params:
        `rating`: 等级或定数
        `user`: 用户 `User` 模型
        `page`: 页数
    Returns:
        `MessageSegment`
    """
    play_result = await get_player_result(user)
    new_play_result = sorted(
        filter(
            (lambda x: x.level == rating)
            if isinstance(rating, str)
            else (lambda x: x.level_value == rating),
            play_result,
        ),
        key=lambda y: y.achievements,
        reverse=True,
    )

    result_sum = len(new_play_result)
    end_page = max(1, (result_sum + 79) // 80)
    page = max(1, min(page, end_page))

    to_page = 80 if page < end_page else (result_sum % 80 or 80)
    line = (to_page + 4) // 5
    if page < end_page:
        plc = line * 109 + 130 * 4
    else:
        multiplier = (to_page + 19) // 20
        actual_line = 4 if to_page <= 20 else line
        plc = actual_line * 109 + 130 * multiplier

    background_bg = tricolor_gradient_prism_plus(1400, 280 + plc)

    score = DrawScore(user.service, background_bg)
    image = score.draw_score_list(rating, new_play_result, page, end_page)
    return MessageSegment.image(image)


@handle_errors
async def draw_rating_ranking(name: str, page: int) -> MessageSegment:
    """
    查看查分器排行榜（仅Diving-Fish）

    Params:
        `name`: 查分器用户名
        `page`: 页数
    Returns:
        `MessageSegment`
    """
    api = DivingFishAPI()
    rank_data = await api.rating_ranking()
    user_rows = len(rank_data)
    current_time = time.strftime("%Y-%m-%d %H:%M:%S")

    if name:
        found_data = next(
            (
                (idx + 1, r.username)
                for idx, r in enumerate(rank_data)
                if r.username.lower() == name
            ),
            None,
        )
        if found_data:
            rank_index, nickname = found_data
            data = (
                f"截止至「{current_time}」玩家「{nickname}」\n"
                f"在查分器已注册用户 RA 排行第「{rank_index}」位"
            )
        else:
            data = f"未在查分器排行榜前「{user_rows}」名中找到玩家「{name}」"
        return data

    per_page = 50
    total_pages = (user_rows + per_page - 1) // per_page

    page = max(1, min(page, total_pages))
    start_idx = (page - 1) * per_page
    end_idx = min(start_idx + per_page, user_rows)

    header = f"截止至「{current_time}」，查分器已注册用户 RA 排行：\n"
    lines = [
        f"No.{i:02d}.「{r.ra}」 {r.username}"
        for i, r in enumerate(rank_data[start_idx:end_idx], start=start_idx + 1)
    ]
    footer = f"\n第「{page} / {total_pages}」页，共「{user_rows}」名玩家"

    full_msg = header + "\n".join(lines) + footer
    return MessageSegment.image(image_to_base64(text_to_image(full_msg)))
