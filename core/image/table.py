from collections import defaultdict

from PIL import Image, ImageDraw

from ...constants import (
    ACHIEVEMENT_LIST,
    COMBO_MAP,
    COMBO_SP,
    LEVEL_LIST,
    RANK_MAP,
    RANK_SP,
    SYNC_D_SP,
    SYNC_MAP,
)
from ...resources import (
    FOTNEWRODIN,
    TBFONT,
    pic_dir,
    plate_table_dir,
    plate_version_dir,
    rating_table_dir,
)
from ..merge.models import PlayedResult, RatingTableResult, ServiceName, Song, Theme
from ..service import mai
from ..utils.calc import compute_rating
from .base import ScoreBaseImage
from .tools import DrawText, image_to_base64

PlayedResultMap = defaultdict[int, dict[int, RatingTableResult]]
PlateResultMap = dict[str, dict[int, list[PlayedResult | None]]]


STATISTICS_KEYS = [
    "clear",
    "s",
    "sp",
    "ss",
    "ssp",
    "sss",
    "sssp",
    "sync",
    "fc",
    "fcp",
    "ap",
    "app",
    "fs",
    "fsp",
    "fsd",
    "fsdp",
]


class RatingGridConfig:
    start_x = 140
    """作图 `x` 轴起点"""
    start_y = 450
    """作图 `y` 轴起点"""
    gap = 85
    """间距"""
    row_count = 14
    """`x` 轴数量"""
    stats_first_line_x = 534
    """统计数据第一行 `x` 轴起点"""
    stats_first_line_y = 238
    """统计数据第一行 `y` 轴起点"""
    stats_second_line_x = 292
    """统计数据第二行 `x` 轴起点"""
    stats_second_line_y = 323
    """统计数据第二行 `y` 轴起点"""


class PlateGridConfig:
    start_x = 180
    """作图 `x` 轴起点"""
    start_y = 490
    """作图 `y` 轴起点"""
    gap = 96
    """`x` 和 `y` 轴间距"""
    row_count = 12
    """数量"""


class DrawRatingTable:
    unfinished_bg = Image.open(pic_dir / "unfinished_1.png")
    complete_bg = Image.open(pic_dir / "complete_1.png")

    def __init__(
        self,
        rating: str,
        *,
        service: ServiceName | None = None,
        play_result: list[PlayedResult] | None = None,
        plan: bool = False,
        level_text: bool = False,
    ):
        """
        Params:
            `rating`: 定数
            `service`: 数据源
            `play_result`: 游玩数据列表
            `plan`: 可选，是否指定目标
            `level_text`: 可选，是否只画定数标题，例如：`Level.13+`
        """
        self.rating = rating
        self.service = service
        self.result = play_result
        self.plan = plan
        self.level_text = level_text

        self._rank_cache: dict[str, Image.Image] = {}
        self._fc_cache: dict[str, Image.Image] = {}

    def _get_rank_icon(self, rate: str) -> Image.Image:
        """按需加载并缓存图标"""
        if rate not in self._rank_cache:
            path = pic_dir / Theme.PRISM_PLUS.value / f"UI_TTR_Rank_{rate}.png"
            if path.exists():
                self._rank_cache[rate] = Image.open(path)
        return self._rank_cache.get(rate)

    def _get_fc_icon(self, fc: str) -> Image.Image:
        if fc not in self._fc_cache:
            path = pic_dir / f"UI_MSS_MBase_Icon_{COMBO_MAP[fc]}.png"
            if path.exists():
                self._fc_cache[fc] = Image.open(path).resize((50, 50))
        return self._fc_cache.get(fc)

    def _calc_achievements_fc(
        self, score_list: list[float] | list[str], lvlist_num: int
    ) -> int:
        r = -1
        thresholds = range(4) if self.plan else ACHIEVEMENT_LIST[-6:]
        for _t in thresholds:
            count = sum(1 for s in score_list if s >= _t)
            if count == lvlist_num:
                r += 1
            else:
                break
        return r

    def _process_rating_table_data(self) -> tuple[dict[str, int], PlayedResultMap]:
        """
        处理定数表数据
        """
        statistics = {k: 0 for k in STATISTICS_KEYS}
        played_map: PlayedResultMap = defaultdict(dict)
        rank_sp = RANK_SP[-6:]

        for _d in self.result:
            if _d.level != self.rating:
                continue
            played_map[_d.song_id][_d.level_index] = RatingTableResult(
                achievements=_d.achievements, level=_d.level, fc=_d.fc
            )
            rate = compute_rating(
                _d.level_value, _d.achievements, onlyrate=True
            ).lower()
            if _d.achievements >= 80:
                statistics["clear"] += 1

            if rate in rank_sp:
                for r in rank_sp[: rank_sp.index(rate) + 1]:
                    statistics[r] += 1

            if _d.fc and _d.fc.value in COMBO_SP:
                for f in COMBO_SP[: COMBO_SP.index(_d.fc.value) + 1]:
                    statistics[f] += 1

            if _d.fs:
                if _d.fs.value == "sync":
                    statistics["sync"] += 1
                elif _d.fs.value in SYNC_D_SP:
                    for s in SYNC_D_SP[: SYNC_D_SP.index(_d.fs.value) + 1]:
                        statistics[s] += 1

        return statistics, played_map

    def draw(self) -> str:
        """
        绘制定数表
        """
        im = Image.open(rating_table_dir / f"{self.rating}.png").convert("RGBA")
        dr = ImageDraw.Draw(im)
        tb = DrawText(dr, TBFONT)
        fot = DrawText(dr, FOTNEWRODIN)

        font_color = (114, 188, 254, 255)

        if self.level_text:
            fot.draw(495, 220, 70, "Level.", font_color, "ld", 8, (255, 255, 255, 255))
            fot.draw(
                750, 220, 100, self.rating, font_color, "ld", 8, (255, 255, 255, 255)
            )
            return image_to_base64(im)

        fot.draw(495, 160, 70, "Level.", font_color, "ld", 8, (255, 255, 255, 255))
        fot.draw(750, 160, 100, self.rating, font_color, "ld", 8, (255, 255, 255, 255))

        statistics, played_map = self._process_rating_table_data()

        lv_data = mai.total_level_data.get(self.rating)
        total_songs_count = sum(len(v) for v in lv_data.values())
        achievements_or_fc_list: list[float | int] = []

        im.alpha_composite(
            Image.open(pic_dir / "complete.png").convert("RGBA"), (251, 190)
        )

        tb.draw(
            394,
            RatingGridConfig.stats_first_line_y,
            30,
            f"{statistics['clear']}/{total_songs_count}",
            ScoreBaseImage._default_text_color,
            "mm",
            5,
            (255, 255, 255, 255),
        )

        for n, key in enumerate(STATISTICS_KEYS[1:]):
            if n < 6:
                col = n % 6
                x = RatingGridConfig.stats_first_line_x + col * 102
                y = RatingGridConfig.stats_first_line_y
            else:
                col = (n - 6) % 9
                x = RatingGridConfig.stats_second_line_x + col * 102
                y = RatingGridConfig.stats_second_line_y
            tb.draw(
                x,
                y,
                30,
                statistics[key],
                ScoreBaseImage._default_text_color,
                "mm",
                2,
                (255, 255, 255, 255),
            )

        current_y = RatingGridConfig.start_y
        for ra, songs in lv_data.items():
            for num, song in enumerate(lv_data[ra]):
                row, col = divmod(num, RatingGridConfig.row_count)
                x = RatingGridConfig.start_x + col * RatingGridConfig.gap
                y = current_y + row * RatingGridConfig.gap

                _record = played_map.get(song.song_id)
                if _record is None:
                    continue

                record = _record.get(song.difficulties.level_index)
                if record is None:
                    continue

                if not self.plan:
                    achievements_or_fc_list.append(record.achievements)
                    bg = (
                        self.complete_bg
                        if record.achievements >= 100
                        else self.unfinished_bg
                    )
                    im.alpha_composite(bg, (x + 1, y + 1))

                    rate = compute_rating(
                        song.difficulties.level_value,
                        record.achievements,
                        onlyrate=True,
                    )
                    im.alpha_composite(
                        self._get_rank_icon(rate).resize((78, 35)), (x, y + 20)
                    )
                    continue

                if record.fc:
                    achievements_or_fc_list.append(COMBO_SP.index(record.fc))
                    im.alpha_composite(self.complete_bg, (x + 1, y + 1))
                    im.alpha_composite(self._get_fc_icon(record.fc), (x + 15, y + 13))

            group_rows = (len(songs) - 1) // RatingGridConfig.row_count + 1
            current_y += group_rows * RatingGridConfig.gap + 30

        if len(achievements_or_fc_list) == total_songs_count:
            r = self._calc_achievements_fc(achievements_or_fc_list, total_songs_count)
            if r != -1:
                pic = COMBO_MAP[COMBO_SP[r]] if self.plan else RANK_MAP[RANK_SP[-6:][r]]
                im.alpha_composite(
                    Image.open(pic_dir / f"UI_MSS_Allclear_Icon_{pic}.png"), (40, 40)
                )

        final_im = im.resize(
            (int(im.size[0] * 0.8), int(im.size[1] * 0.8)), Image.Resampling.LANCZOS
        )
        return image_to_base64(final_im)


class DrawPlateTable:
    PLAN_CRITERIA: dict[str, dict[str, str | list[str] | int]] = {
        "者": {"attr": "achievements", "values": 80, "prefix": "RANK"},
        "极": {"attr": "fc", "values": COMBO_SP, "prefix": "UI_CHR_PlayBonus_"},
        "極": {"attr": "fc", "values": COMBO_SP, "prefix": "UI_CHR_PlayBonus_"},
        "将": {"attr": "achievements", "values": 100, "prefix": "RANK"},
        "神": {"attr": "fc", "values": ["ap", "app"], "prefix": "UI_CHR_PlayBonus_"},
        "舞舞": {
            "attr": "fs",
            "values": ["fsd", "fsdp", "fsdpx", "fsdp+"],
            "prefix": "UI_CHR_PlayBonus_",
        },
    }

    finished_bg = [Image.open(pic_dir / f"t_{_}.png") for _ in range(5)]
    unfinished_bg = Image.open(pic_dir / "unfinished_2.png")
    complete_bg = Image.open(pic_dir / "complete_2.png")
    progress_big = Image.open(pic_dir / "progress_big.png")

    _progress_bg = Image.open(pic_dir / "plate_progress.png")
    _progress_wu_bg = Image.open(pic_dir / "plate_progress_wu.png")
    _progress_small = Image.open(pic_dir / "progress_small.png")
    _progress_small_wu = Image.open(pic_dir / "progress_small_wu.png")

    def __init__(
        self,
        service: ServiceName,
        play_result: list[PlayedResult],
        *,
        plan: str | None = None,
        version: str | None = None,
        version_name: str | None = None,
        page: int | None = None,
    ):
        """
        绘制完成表

        Params:
            `service`: 数据源
            `play_result`: 游玩数据列表
            `plan`: 计划
            `version`: 游戏版本
            `version_name`: 版本名称
            `page`: 页数
        """
        self.service = service
        self.result = play_result
        self.plan = plan
        self.version = version
        self.version_name = version_name
        self.page = page
        self.is_wu = version in ["舞", "霸"]

        if self.is_wu:
            self.plate_name = f"{version}-{page}"
            self.slot_num = 5
            self.progress_bg = self._progress_wu_bg
            self.progress_small = self._progress_small_wu
            self.progress_width = 176
            self.stats_start_x = 292
            self.stats_gap_x = 204
        else:
            self.plate_name = version
            self.slot_num = 4
            self.progress_bg = self._progress_bg
            self.progress_small = self._progress_small
            self.progress_width = 230
            self.stats_start_x = 320
            self.stats_gap_x = 253

    def _get_level_dict(self) -> dict[str, list[Song]]:
        return {lv: [] for lv in reversed(LEVEL_LIST)}

    def _is_qualified(self, play: PlayedResult | None, plan: str) -> bool:
        """判定单个谱面是否符合牌子要求"""
        if not play:
            return False
        cfg = self.PLAN_CRITERIA.get(plan)
        if not cfg:
            return False

        val = getattr(play, cfg["attr"])
        if plan == "将":
            return val >= 100
        if plan == "者":
            return val >= 80
        return val in cfg["values"]

    def _get_plate_icon(self, play: PlayedResult, plan: str) -> Image.Image:
        """获取牌子完成时的图标"""
        if plan == "将":
            rate = compute_rating(play.level_value, play.achievements, onlyrate=True)
            return Image.open(
                pic_dir / Theme.PRISM_PLUS.value / f"UI_TTR_Rank_{rate}.png"
            ).resize((80, 36))

        cfg = self.PLAN_CRITERIA.get(plan)
        val = getattr(play, cfg["attr"])

        icon_name = COMBO_MAP.get(val) or SYNC_MAP.get(val) or val
        path = pic_dir / f"{cfg['prefix']}{icon_name}.png"
        return Image.open(path).resize((60, 60))

    def _process_plate_table_data(self) -> tuple[int, PlateResultMap]:
        """
        处理牌子表数据
        """
        plate_id_list = mai.total_plate_id_list[self.version_name]
        song_list = mai.total_list.by_id_list(plate_id_list)

        song_id_to_level = {
            song.song_id: song.difficulties[3].level for song in song_list
        }

        played_map: PlateResultMap = defaultdict(
            lambda: defaultdict(lambda: [None] * 4)
        )

        song_list.sort(key=lambda x: x.difficulties[3].level_value, reverse=True)
        for song in song_list:
            played_map[song.difficulties[3].level][song.song_id]

        for _d in self.result:
            if _d.song_id not in song_id_to_level:
                continue
            if self.slot_num == 4 and _d.level_index == 4:
                continue
            target_level = song_id_to_level[_d.song_id]
            played_map[target_level][_d.song_id][_d.level_index] = _d

        return len(plate_id_list), played_map

    def _process_plate_table_wu_data(self) -> tuple[int, int, PlateResultMap]:
        """
        处理牌子 `舞` 和 `霸者` 的数据
        """
        wu_id_list = mai.total_plate_id_list["舞"]
        wu_re_id_set = set(mai.total_plate_id_list["舞ReMASTER"])
        wu_song_list = mai.total_list.by_id_list(wu_id_list)

        all_level_dict = self._get_level_dict()

        def get_display_level_value(song: Song) -> str:
            if song.song_id in wu_re_id_set and len(song.difficulties) > 4:
                return song.difficulties[4].level_value
            return song.difficulties[3].level_value

        wu_song_list.sort(key=get_display_level_value, reverse=True)

        def get_display_level(song: Song) -> str:
            if song.song_id in wu_re_id_set and len(song.difficulties) > 4:
                return song.difficulties[4].level
            return song.difficulties[3].level

        song_id_to_level = {
            song.song_id: get_display_level(song) for song in wu_song_list
        }

        for song in wu_song_list:
            lv = get_display_level(song)
            if lv in all_level_dict:
                all_level_dict[lv].append(song)

        played_map: PlateResultMap = defaultdict(lambda: defaultdict(list))
        for lv in all_level_dict.keys():
            songs_in_lv = all_level_dict[lv]
            if not songs_in_lv:
                continue

            for song in songs_in_lv:
                sid = song.song_id
                slot_size = 5 if sid in wu_re_id_set else 4
                played_map[lv][sid] = [None] * slot_size

        for _d in self.result:
            if _d.song_id not in song_id_to_level:
                continue
            target_level = song_id_to_level[_d.song_id]

            if _d.song_id in played_map[target_level]:
                current_slots = played_map[target_level][_d.song_id]
                if _d.level_index < len(current_slots):
                    current_slots[_d.level_index] = _d

        return len(wu_id_list), len(wu_re_id_set), played_map

    def draw(self) -> str:
        """
        绘制完成表
        """
        plan = self.plan
        plate_wu_total_count = 0
        if self.is_wu:
            plate_total_count, plate_wu_total_count, played_map = (
                self._process_plate_table_wu_data()
            )
            if self.version == "霸":
                plan = "者" if self.plan == "者" else self.plan

            keys = list(played_map.keys())
            idx = keys.index("13")
            if self.is_wu and self.page == 1:
                lv_key = keys[:idx]
            else:
                lv_key = keys[idx:]
        else:
            plate_total_count, played_map = self._process_plate_table_data()
            lv_key = list(played_map.keys())

        im = Image.open(plate_table_dir / f"{self.plate_name}.png")
        draw = ImageDraw.Draw(im)
        fot = DrawText(draw, FOTNEWRODIN)

        im.alpha_composite(self.progress_bg, (175, 20))

        plate_bg = (
            plate_version_dir / f"{self.version}{'極' if plan == '极' else plan}.png"
        )
        im.alpha_composite(Image.open(plate_bg).resize((1000, 161)), (200, 45))
        lv = [set() for _ in range(self.slot_num)]
        finished_songs = set()

        current_y = PlateGridConfig.start_y
        for _index, songs_dict in played_map.items():
            is_current_page = _index in lv_key
            rows = (len(songs_dict) - 1) // PlateGridConfig.row_count + 1

            for idx, (song_id, result) in enumerate(songs_dict.items()):
                hit_slots: list[int] = []
                song_all_qualified = True
                has_any_play = False
                for _r, play in enumerate(result):
                    if play is None:
                        continue
                    has_any_play = True
                    if self._is_qualified(play, self.plan):
                        hit_slots.append(_r)
                        lv[_r].add(song_id)
                    else:
                        song_all_qualified = False

                if song_all_qualified and has_any_play:
                    finished_songs.add(song_id)

                row, col = divmod(idx, PlateGridConfig.row_count)
                x = PlateGridConfig.start_x + col * PlateGridConfig.gap
                y = current_y + row * PlateGridConfig.gap

                if not is_current_page:
                    continue

                if len(result) == 5:
                    index = 4
                else:
                    index = 3

                if index in hit_slots:
                    play = result[index]
                    im.alpha_composite(self.complete_bg, (x + 1, y + 1))

                    icon = self._get_plate_icon(play, self.plan)
                    dest = (x, y + 22) if self.plan == "将" else (x + 10, y + 12)
                    im.alpha_composite(icon, dest)

                for s_idx in hit_slots:
                    if self.is_wu and len(result) == 5:
                        im.alpha_composite(
                            self.finished_bg[s_idx].resize((14, 14)),
                            (x + 1 + 16 * s_idx, y + 64),
                        )
                    else:
                        im.alpha_composite(
                            self.finished_bg[s_idx], (x + 4 + 19 * s_idx, y + 63)
                        )

            if is_current_page:
                current_y += rows * PlateGridConfig.gap + 30

        complete_sum = len(finished_songs)
        if complete_sum == plate_total_count:
            text = "COMPLETED!!!"
        else:
            text = f"{complete_sum}/{plate_total_count}"

        progress = complete_sum / plate_total_count
        if progress != 0:
            bar = self.progress_big.crop((0, 0, int(993 * progress), 92))
            im.alpha_composite(bar, (204, 219))

        fot.draw(
            700,
            240,
            30,
            text,
            ScoreBaseImage._default_text_color,
            "mm",
            3,
            (255, 255, 255, 255),
        )
        fot.draw(
            1190,
            240,
            30,
            f"{round(progress * 100, 2)}%",
            ScoreBaseImage._default_text_color,
            "rm",
            3,
            (255, 255, 255, 255),
        )

        stats_start_y = 300

        for _l in range(len(lv)):
            x = self.stats_start_x + _l * self.stats_gap_x

            complete_sum_group = len(lv[_l])

            if self.is_wu:
                _progress_text_x = 89
                _progress_x = 88
            else:
                _progress_text_x = 115
                _progress_x = 115

            plate_count = plate_total_count if _l != 4 else plate_wu_total_count

            progress_group = complete_sum_group / plate_count
            if progress_group != 0:
                bar_group_rounded = self.progress_small.crop(
                    (0, 0, int(self.progress_width * progress_group), 46)
                )
                im.alpha_composite(bar_group_rounded, (x - _progress_x, 326))

            if complete_sum_group == plate_count:
                fot.draw(
                    x,
                    stats_start_y,
                    24,
                    "COMPLETED!!!",
                    ScoreBaseImage._id_text_color[_l],
                    "mm",
                    4,
                    (255, 255, 255, 255),
                )

            fot.draw(
                x,
                stats_start_y,
                40,
                complete_sum_group,
                ScoreBaseImage._id_text_color[_l],
                "mm",
                4,
                (255, 255, 255, 255),
            )
            fot.draw(
                x + _progress_text_x,
                stats_start_y + 20,
                14,
                f"/{plate_count}",
                ScoreBaseImage._id_text_color[_l],
                "rd",
                3,
                (255, 255, 255, 255),
            )
            fot.draw(
                x + _progress_text_x,
                343,
                20,
                f"{round(progress_group * 100, 2)}%",
                ScoreBaseImage._default_text_color,
                "rm",
                2,
                (255, 255, 255, 255),
            )

        return image_to_base64(im)
