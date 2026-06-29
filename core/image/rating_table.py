from collections import defaultdict

from PIL import Image, ImageDraw

from ...constants import (
    ACHIEVEMENT_LIST,
    COMBO_MAP,
    COMBO_SP,
    RANK_MAP,
    RANK_SP,
    STATISTICS_KEYS,
    SYNC_D_SP,
)
from ...resources import (
    FOTNEWRODIN,
    TBFONT,
    pic_dir,
    rating_table_dir,
)
from ..merge.models import PlayedResult, RatingTableResult, ServiceName, Theme
from ..service import mai
from ..utils.calc import compute_rating
from .assets import AssetsImage
from .tools import (
    DrawText,
    image_to_base64,
)

PlayedResultMap = defaultdict[int, dict[int, RatingTableResult]]


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


class DrawRatingTable(AssetsImage):
    _font_color = (114, 188, 254, 255)

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
        super().__init__()
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
                self._rank_cache[rate] = self._open_image(path)
        return self._rank_cache.get(rate)

    def _get_fc_icon(self, fc: str) -> Image.Image:
        if fc not in self._fc_cache:
            path = pic_dir / f"UI_MSS_MBase_Icon_{COMBO_MAP[fc]}.png"
            if path.exists():
                self._fc_cache[fc] = self._open_image(path).resize((50, 50))
        return self._fc_cache.get(fc)

    def _get_big_fc_icon(self, fc: str) -> Image.Image:
        if fc not in self._fc_cache:
            path = pic_dir / f"UI_CHR_PlayBonus_{COMBO_MAP[fc]}.png"
            if path.exists():
                self._fc_cache[fc] = self._open_image(path).resize((200, 200))
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

        Returns:
            `base64 str`
        """
        im = Image.open(rating_table_dir / f"{self.rating}.png").convert("RGBA")
        dr = ImageDraw.Draw(im)
        tb = DrawText(dr, TBFONT)
        fot = DrawText(dr, FOTNEWRODIN)

        if self.level_text:
            fot.draw(
                495, 220, 70, "Level.", self._font_color, "ld", 8, (255, 255, 255, 255)
            )
            fot.draw(
                750,
                220,
                100,
                self.rating,
                self._font_color,
                "ld",
                8,
                (255, 255, 255, 255),
            )
            return image_to_base64(im)

        fot.draw(
            495, 160, 70, "Level.", self._font_color, "ld", 8, (255, 255, 255, 255)
        )
        fot.draw(
            750, 160, 100, self.rating, self._font_color, "ld", 8, (255, 255, 255, 255)
        )

        statistics, played_map = self._process_rating_table_data()

        lv_data = mai.total_level_data.get(self.rating)
        total_songs_count = sum(len(v) for v in lv_data.values())
        achievements_or_fc_list: list[float | int] = []

        im.alpha_composite(self._table_complete_bg, (251, 190))

        tb.draw(
            394,
            RatingGridConfig.stats_first_line_y,
            30,
            f"{statistics['clear']}/{total_songs_count}",
            self._default_text_color,
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
                self._default_text_color,
                "mm",
                2,
                (255, 255, 255, 255),
            )

        if self.rating == "15":
            for num, song in enumerate(lv_data["15.0"]):
                row, col = divmod(num, 3)
                x = 100 + col * 425
                y = 500 + row * 450

                _record = played_map.get(song.song_id)
                if _record is None:
                    continue

                record = _record.get(song.difficulties.level_index)
                if record is None:
                    continue

                if not self.plan:
                    achievements_or_fc_list.append(record.achievements)

                    rate = compute_rating(
                        song.difficulties.level_value,
                        record.achievements,
                        onlyrate=True,
                    )
                    im.alpha_composite(self._get_rank_icon(rate), (x + 55, y + 115))
                    continue

                if record.fc:
                    achievements_or_fc_list.append(COMBO_SP.index(record.fc))
                    im.alpha_composite(
                        self._get_big_fc_icon(record.fc), (x + 75, y + 80)
                    )

        else:
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
                            self._rating_complete_bg
                            if record.achievements >= 100
                            else self._rating_unfinished_bg
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
                        im.alpha_composite(self._rating_complete_bg, (x + 1, y + 1))
                        im.alpha_composite(
                            self._get_fc_icon(record.fc), (x + 15, y + 13)
                        )

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
