from collections import defaultdict

from PIL import Image, ImageDraw
from pydantic import BaseModel

from ...config import maiconfig
from ...constants import COMBO_MAP, COMBO_SP, DIFFS, LEVEL_LIST, SYNC_MAP
from ...resources import (
    FOTNEWRODIN,
    TBFONT,
    pic_dir,
    plate_table_dir,
    plate_version_dir,
)
from ..merge.models import PlayedResult, ServiceName, Song, Theme
from ..service import mai
from ..utils.calc import compute_rating
from .assets import AssetsImage
from .tools import (
    DrawText,
    generate_frosted_card,
    image_to_base64,
    song_chart,
    tricolor_gradient_prism_plus,
)

PlateResultMap = dict[str, dict[int, list[PlayedResult | None]]]


class PlateSongProgress(BaseModel):
    song_id: int
    results: list[PlayedResult | None]
    qualified_slots: list[int]
    completed: bool


class PlateChartProgress(BaseModel):
    song_id: int
    level: str
    level_value: float
    result: PlayedResult | None
    qualified: bool


class PlateProgressData(BaseModel):
    total_count: int
    remaster_count: int
    levels: dict[str, list[PlateSongProgress]]
    difficulty_results: dict[int, list[PlateChartProgress]]
    display_levels: list[str]
    slot_counts: list[int]
    completed_count: int


class PlateGridConfig:
    start_x = 180
    """作图 `x` 轴起点"""
    start_y = 490
    """作图 `y` 轴起点"""
    gap = 96
    """`x` 和 `y` 轴间距"""
    row_count = 12
    """每行数量"""


class PlateTable(AssetsImage):
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
        super().__init__()
        self.service = service
        self.result = play_result
        self.plan = plan
        self.version = version
        self.version_name = version_name
        self.page = page
        self.is_wu = version in ["舞", "霸"]

        if self.is_wu:
            self.plate_name = f"舞-{page}"
            self.slot_num = 5
        else:
            self.plate_name = version
            self.slot_num = 4

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

    def _process_plate_table_data(
        self,
    ) -> tuple[int, PlateResultMap, dict[int, Song]]:
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

        return (
            len(plate_id_list),
            played_map,
            {song.song_id: song for song in song_list},
        )

    def _process_plate_table_wu_data(
        self,
    ) -> tuple[int, int, PlateResultMap, dict[int, Song]]:
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

        return (
            len(wu_id_list),
            len(wu_re_id_set),
            played_map,
            {song.song_id: song for song in wu_song_list},
        )

    def process(self) -> PlateProgressData:
        """
        处理所有牌子数据
        """
        plate_wu_total_count = 0
        if self.is_wu:
            plate_total_count, plate_wu_total_count, played_map, songs_by_id = (
                self._process_plate_table_wu_data()
            )

            keys = list(played_map.keys())
            idx = keys.index("13") if "13" in keys else len(keys)
            if self.page == 1:
                display_levels = keys[:idx]
            else:
                display_levels = keys[idx:]
        else:
            plate_total_count, played_map, songs_by_id = (
                self._process_plate_table_data()
            )
            display_levels = list(played_map.keys())

        difficulty_results: dict[int, list[PlateChartProgress]] = {
            index: [] for index in range(self.slot_num)
        }
        finished_songs: set[int] = set()
        levels: dict[str, list[PlateSongProgress]] = {}
        for level, songs_dict in played_map.items():
            level_progress: list[PlateSongProgress] = []
            for song_id, results in songs_dict.items():
                qualified_slots = [
                    idx
                    for idx, play in enumerate(results)
                    if self._is_qualified(play, self.plan)
                ]
                for slot, result in enumerate(results):
                    chart = songs_by_id[song_id].difficulties[slot]
                    difficulty_results[slot].append(
                        PlateChartProgress(
                            song_id=song_id,
                            level=chart.level,
                            level_value=chart.level_value,
                            result=result,
                            qualified=slot in qualified_slots,
                        )
                    )

                completed = len(qualified_slots) == len(results)
                if completed:
                    finished_songs.add(song_id)

                level_progress.append(
                    PlateSongProgress(
                        song_id=song_id,
                        results=results,
                        qualified_slots=qualified_slots,
                        completed=completed,
                    )
                )
            levels[level] = level_progress

        for charts in difficulty_results.values():
            charts.sort(key=lambda chart: chart.level_value, reverse=True)

        return PlateProgressData(
            total_count=plate_total_count,
            remaster_count=plate_wu_total_count,
            levels=levels,
            difficulty_results=difficulty_results,
            display_levels=display_levels,
            slot_counts=[
                sum(chart.qualified for chart in difficulty_results[index])
                for index in range(self.slot_num)
            ],
            completed_count=len(finished_songs),
        )

    def _plate_background(self) -> Image.Image:
        plan = "極" if self.plan == "极" else self.plan
        return Image.open(plate_version_dir / f"{self.version}{plan}.png").convert(
            "RGBA"
        )


class DrawPlateTable(PlateTable):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.is_wu:
            self.progress_bg = self._plate_progress_wu_bg
            self.progress_small = self._plate_progress_small_wu
            self.progress_width = 176
            self.stats_start_x = 292
            self.stats_gap_x = 204
        else:
            self.progress_bg = self._plate_progress_bg
            self.progress_small = self._plate_progress_small
            self.progress_width = 230
            self.stats_start_x = 320
            self.stats_gap_x = 253

    def _get_plate_icon(self, play: PlayedResult, plan: str) -> Image.Image:
        """获取完成表中已达成谱面的图标。"""
        if plan in ["将", "者"]:
            rate = compute_rating(play.level_value, play.achievements, onlyrate=True)
            return self._open_image(
                pic_dir / Theme.PRISM_PLUS.value / f"UI_TTR_Rank_{rate}.png"
            ).resize((80, 36))

        cfg = self.PLAN_CRITERIA.get(plan)
        val = getattr(play, cfg["attr"])

        icon_name = COMBO_MAP.get(val) or SYNC_MAP.get(val) or val
        path = pic_dir / f"{cfg['prefix']}{icon_name}.png"
        return self._open_image(path).resize((60, 60))

    def draw(self) -> str:
        """绘制牌子完成表。"""
        data = self.process()
        im = Image.open(plate_table_dir / f"{self.plate_name}.png")
        draw = ImageDraw.Draw(im)
        fot = DrawText(draw, FOTNEWRODIN)

        im.alpha_composite(self.progress_bg, (175, 20))
        im.alpha_composite(self._plate_background().resize((1000, 161)), (200, 45))

        current_y = PlateGridConfig.start_y
        for level, songs in data.levels.items():
            is_current_page = level in data.display_levels
            rows = (len(songs) - 1) // PlateGridConfig.row_count + 1
            for idx, song in enumerate(songs):
                row, col = divmod(idx, PlateGridConfig.row_count)
                x = PlateGridConfig.start_x + col * PlateGridConfig.gap
                y = current_y + row * PlateGridConfig.gap

                if not is_current_page:
                    continue

                index = len(song.results) - 1
                if index in song.qualified_slots:
                    play = song.results[index]
                    im.alpha_composite(self._plate_complete_bg, (x + 1, y + 1))
                    icon = self._get_plate_icon(play, self.plan)
                    dest = (
                        (x, y + 22) if self.plan in ["将", "者"] else (x + 10, y + 12)
                    )
                    im.alpha_composite(icon, dest)

                for s_idx in song.qualified_slots:
                    if self.is_wu and len(song.results) == 5:
                        im.alpha_composite(
                            self._plate_finished_bg[s_idx].resize((14, 14)),
                            (x + 1 + 16 * s_idx, y + 64),
                        )
                    else:
                        im.alpha_composite(
                            self._plate_finished_bg[s_idx], (x + 4 + 19 * s_idx, y + 63)
                        )

            if is_current_page:
                current_y += rows * PlateGridConfig.gap + 30

        complete_sum = data.completed_count
        if complete_sum == data.total_count:
            text = "COMPLETED!!!"
        else:
            text = f"{complete_sum}/{data.total_count}"

        progress = complete_sum / data.total_count
        if progress != 0:
            bar = self._plate_progress_big.crop((0, 0, int(993 * progress), 92))
            im.alpha_composite(bar, (204, 219))

        fot.draw(
            700,
            240,
            30,
            text,
            self._default_text_color,
            "mm",
            3,
            (255, 255, 255, 255),
        )
        fot.draw(
            1190,
            240,
            30,
            f"{round(progress * 100, 2)}%",
            self._default_text_color,
            "rm",
            3,
            (255, 255, 255, 255),
        )

        stats_start_y = 300

        for _l, complete_sum_group in enumerate(data.slot_counts):
            x = self.stats_start_x + _l * self.stats_gap_x

            if self.is_wu:
                _progress_text_x = 89
                _progress_x = 88
            else:
                _progress_text_x = 115
                _progress_x = 115

            plate_count = data.total_count if _l != 4 else data.remaster_count

            progress_group = complete_sum_group / plate_count
            if progress_group != 0:
                bar_group_rounded = self.progress_small.crop(
                    (0, 0, int(self.progress_width * progress_group), 46)
                )
                im.alpha_composite(bar_group_rounded, (x - _progress_x, 326))

            fot.draw(
                x,
                stats_start_y,
                40,
                complete_sum_group,
                self._id_text_color[_l],
                "mm",
                4,
                (255, 255, 255, 255),
            )
            fot.draw(
                x + _progress_text_x,
                stats_start_y + 20,
                14,
                f"/{plate_count}",
                self._id_text_color[_l],
                "rd",
                3,
                (255, 255, 255, 255),
            )
            fot.draw(
                x + _progress_text_x,
                343,
                20,
                f"{round(progress_group * 100, 2)}%",
                self._default_text_color,
                "rm",
                2,
                (255, 255, 255, 255),
            )

        return image_to_base64(im)


class DrawPlateProgress(PlateTable):
    def _get_display_row_count(self, count: int) -> int:
        if count <= 0:
            return 1
        return min((count - 1) // 13 + 1, 4)

    def _generate_bg(self, height: int, separator_height: int) -> Image.Image:
        """
        生成背景

        Params:
            `height`: 背景高度
            `separator_height`: 分割线高度
        Returns:
            `Image.Image`
        """
        im = tricolor_gradient_prism_plus(1400, height)
        im.alpha_composite(self._aurora_bg)
        im.alpha_composite(self._shines_bg, (11, 6))
        im.alpha_composite(self._rainbow_bg, (318, height - 545))
        im.alpha_composite(self._rainbow_bottom_bg, (122, height - 305))
        for h in range((height // 358) + 1):
            im.alpha_composite(self._pattern_bg, (0, (358 + 7) * h))
        im.alpha_composite(self._separator_bg, (100, separator_height))
        return im

    def draw(self) -> str:
        """绘制牌子进度表。"""
        data = self.process()
        results = {
            index: [
                chart for chart in data.difficulty_results[index] if not chart.qualified
            ]
            for index in reversed(data.difficulty_results)
        }
        total_counts = [
            len(charts) for charts in reversed(data.difficulty_results.values())
        ]
        display_counts = [len(charts) for charts in results.values()]

        current_y = 395
        for count in display_counts:
            current_y += self._get_display_row_count(count) * PlateGridConfig.gap + 100

        height = current_y + 180
        _im = self._generate_bg(height, 305)
        im = generate_frosted_card(_im, (50, 349, 1350, current_y))

        im.alpha_composite(self._plate_progress_2, (175, 20))
        im.alpha_composite(self._plate_background().resize((1000, 161)), (200, 35))

        draw = ImageDraw.Draw(im)
        fot = DrawText(draw, FOTNEWRODIN)
        tb = DrawText(draw, TBFONT)

        START_X = 84
        START_Y = 455
        complete_sum = data.completed_count

        end = None if len(data.slot_counts) == 5 else -1
        new_slot_counts = data.slot_counts[::-1]
        new_color = self._id_text_color[:end][::-1]
        new_diffs = DIFFS[:end][::-1]
        for n, result in enumerate(results.values()):
            im.alpha_composite(self._plate_progress_bottom_bg, (198, START_Y - 85))

            # 进度条
            complete_sum_group = new_slot_counts[n]
            plate_count = total_counts[n]
            progress_group = complete_sum_group / plate_count
            if progress_group != 0:
                _bar = self._plate_progress_big.crop(
                    (0, 0, int(993 * progress_group), 92)
                )
                im.alpha_composite(_bar, (204, START_Y - 79))
            if complete_sum_group == plate_count:
                c_text = "COMPLETED!!!"
            else:
                c_text = f"{complete_sum_group}/{plate_count}"

            fot.draw(
                220,
                START_Y - 57,
                34,
                new_diffs[n],
                new_color[n],
                "lm",
                4,
                (255, 255, 255, 255),
            )
            fot.draw(
                700,
                START_Y - 57,
                36,
                c_text,
                new_color[n],
                "mm",
                4,
                (255, 255, 255, 255),
            )
            fot.draw(
                1190,
                START_Y - 57,
                20,
                f"{round(progress_group * 100, 2)}%",
                new_color[n],
                "rm",
                2,
                (255, 255, 255, 255),
            )

            # 曲绘
            max_row = 0
            for num, song in enumerate(result):
                row, col = divmod(num, 13)
                max_row = max(max_row, row)
                x = START_X + col * PlateGridConfig.gap
                y = START_Y + row * PlateGridConfig.gap

                if num >= 51 and len(result[num:]) != 1:
                    fot.draw(
                        x,
                        y + 35,
                        20,
                        f"余「{len(result[num:])}」\n个未完成",
                        self._default_text_color,
                        "lm",
                        multiline=True,
                    )
                    break
                cover = song_chart(song.song_id)
                im.alpha_composite(Image.open(cover).resize((80, 80)), (x, y))
                im.alpha_composite(self._table_id_bg, (x - 5, y - 5))
                tb.draw(x + 56, y + 4, 16, song.song_id, anchor="mm")
            START_Y += (max_row + 1) * PlateGridConfig.gap + 100

        complete_sum = data.completed_count
        if complete_sum == data.total_count:
            text = "COMPLETED!!!"
        else:
            text = f"{complete_sum}/{data.total_count}"

        progress = complete_sum / data.total_count
        if progress != 0:
            bar = self._plate_progress_big.crop((0, 0, int(993 * progress), 92))
            im.alpha_composite(bar, (204, 219))

        fot.draw(
            700,
            240,
            30,
            text,
            self._default_text_color,
            "mm",
            3,
            (255, 255, 255, 255),
        )
        fot.draw(
            1190,
            240,
            30,
            f"{round(progress * 100, 2)}%",
            self._default_text_color,
            "rm",
            3,
            (255, 255, 255, 255),
        )
        fot.draw(
            700,
            height - 15,
            30,
            f"Designed by Yuri-YuzuChaN & BlueDeer233. Generated by {maiconfig.bot_name} BOT",
            (114, 188, 254, 255),
            "mm",
        )

        return image_to_base64(im)
