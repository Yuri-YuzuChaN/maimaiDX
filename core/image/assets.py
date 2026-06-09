from pathlib import Path
from typing import ClassVar

from PIL import Image

from ...config import maiconfig
from ...resources import pic_dir
from ..merge.models import Theme


class AssetsImage:
    _default_text_color = (124, 129, 255, 255)
    _diff_text_color = [
        (255, 255, 255, 255),
        (255, 255, 255, 255),
        (255, 255, 255, 255),
        (255, 255, 255, 255),
        (138, 0, 226, 255),
    ]
    _id_text_color = [
        (129, 217, 85, 255),
        (245, 189, 21, 255),
        (255, 129, 141, 255),
        (159, 81, 220, 255),
        (138, 0, 226, 255),
    ]
    _bg_color = [
        (111, 212, 61, 255),
        (248, 183, 9, 255),
        (255, 129, 141, 255),
        (159, 81, 220, 255),
        (219, 170, 255, 255),
    ]

    _id_diff_im = [Image.new("RGBA", (55, 10), color) for color in _bg_color]

    _images_loaded: ClassVar[bool] = False
    _themed_images: ClassVar[dict[tuple[Theme, str], Image.Image]] = {}

    _dx_star_bg: list[Image.Image] = []
    _diff_bg: list[Image.Image] = []
    _rise_bg: list[Image.Image] = []
    _diff_pg_bg: list[Image.Image] = []

    # 定数表、完成表图
    _table_type_bg: dict[str, Image.Image] = {}
    _table_dx_small_bg: Image.Image | None = None
    _table_complete_bg: Image.Image | None = None
    _rating_unfinished_bg: Image.Image | None = None
    _rating_complete_bg: Image.Image | None = None
    _plate_finished_bg: list[Image.Image] = []
    _plate_complete_bg: Image.Image | None = None
    _plate_progress_bottom_bg: Image.Image | None = None
    _plate_progress_big: Image.Image | None = None
    _plate_progress_bg: Image.Image | None = None
    _plate_progress_2: Image.Image | None = None
    _plate_progress_wu_bg: Image.Image | None = None
    _plate_progress_small: Image.Image | None = None
    _plate_progress_small_wu: Image.Image | None = None
    _table_id_bg: Image.Image | None = None
    _table_wu_rms_id_bg: Image.Image | None = None
    _table_diff_bg: list[Image.Image] = []
    _separator_bg: Image.Image | None = None
    _chart_white_bg: Image.Image | None = None

    # 曲目列表
    _sl_diff_bg: Image.Image | None = None
    _sl_diff_utg: Image.Image | None = None
    _card_bg: Image.Image | None = None

    # 背景图
    _rainbow_bg: Image.Image | None = None
    _rainbow_bottom_bg: Image.Image | None = None
    _aurora_bg: Image.Image | None = None
    _shines_bg: Image.Image | None = None
    _pattern_bg: Image.Image | None = None
    _moon_bg: Image.Image | None = None

    def __init__(self) -> None:
        """静态资源类"""
        if not maiconfig.save_in_memory:
            self._load_image()

    @staticmethod
    def _open_image(path: Path) -> Image.Image:
        with Image.open(path) as image:
            return image.convert("RGBA")

    @classmethod
    def _create_images(
        cls,
    ) -> dict[str, Image.Image | list[Image.Image] | dict[str, Image.Image]]:
        table_type_bg = {
            "SD": cls._open_image(pic_dir / "SD.png"),
            "DX": cls._open_image(pic_dir / "DX.png"),
        }
        return {
            "_dx_star_bg": [
                cls._open_image(pic_dir / f"UI_GAM_Gauge_DXScoreIcon_0{num}.png")
                for num in range(1, 6)
            ],
            "_diff_bg": [
                cls._open_image(pic_dir / "b50_score_basic.png"),
                cls._open_image(pic_dir / "b50_score_advanced.png"),
                cls._open_image(pic_dir / "b50_score_expert.png"),
                cls._open_image(pic_dir / "b50_score_master.png"),
                cls._open_image(pic_dir / "b50_score_remaster.png"),
            ],
            "_rise_bg": [
                cls._open_image(pic_dir / "rise_score_basic.png"),
                cls._open_image(pic_dir / "rise_score_advanced.png"),
                cls._open_image(pic_dir / "rise_score_expert.png"),
                cls._open_image(pic_dir / "rise_score_master.png"),
                cls._open_image(pic_dir / "rise_score_remaster.png"),
            ],
            "_diff_pg_bg": [
                cls._open_image(pic_dir / "border_progress_basic.png"),
                cls._open_image(pic_dir / "border_progress_advanced.png"),
                cls._open_image(pic_dir / "border_progress_expert.png"),
                cls._open_image(pic_dir / "border_progress_master.png"),
                cls._open_image(pic_dir / "border_progress_remaster.png"),
            ],
            # 定数表、完成表图
            "_table_type_bg": table_type_bg,
            "_table_dx_small_bg": table_type_bg["DX"].resize((44, 16)),
            "_table_complete_bg": cls._open_image(pic_dir / "complete.png"),
            "_rating_unfinished_bg": cls._open_image(pic_dir / "unfinished_1.png"),
            "_rating_complete_bg": cls._open_image(pic_dir / "complete_1.png"),
            "_plate_finished_bg": [
                cls._open_image(pic_dir / f"t_{index}.png") for index in range(5)
            ],
            "_plate_complete_bg": cls._open_image(pic_dir / "complete_2.png"),
            "_plate_progress_bottom_bg": cls._open_image(pic_dir / "progress_bg.png"),
            "_plate_progress_big": cls._open_image(pic_dir / "progress_big.png"),
            "_plate_progress_bg": cls._open_image(pic_dir / "plate_progress.png"),
            "_plate_progress_2": cls._open_image(pic_dir / "plate_progress_2.png"),
            "_plate_progress_wu_bg": cls._open_image(pic_dir / "plate_progress_wu.png"),
            "_plate_progress_small": cls._open_image(pic_dir / "progress_small.png"),
            "_plate_progress_small_wu": cls._open_image(
                pic_dir / "progress_small_wu.png"
            ),
            "_table_id_bg": cls._open_image(pic_dir / "border_table_base.png"),
            "_table_wu_rms_id_bg": cls._open_image(
                pic_dir / "border_table_remaster.png"
            ),
            "_table_diff_bg": [
                cls._open_image(pic_dir / "border_basic.png"),
                cls._open_image(pic_dir / "border_advanced.png"),
                cls._open_image(pic_dir / "border_expert.png"),
                cls._open_image(pic_dir / "border_master.png"),
                cls._open_image(pic_dir / "border_remaster.png"),
            ],
            "_separator_bg": cls._open_image(pic_dir / "separator.png"),
            "_chart_white_bg": cls._open_image(pic_dir / "chart_white.png"),
            # 曲目列表图
            "_sl_diff_bg": cls._open_image(pic_dir / "sl_diff.png"),
            "_sl_diff_utg": cls._open_image(pic_dir / "sl_diff_utg.png"),
            "_card_bg": cls._open_image(pic_dir / "song_card.png"),
            # 背景图
            "_rainbow_bg": cls._open_image(pic_dir / "rainbow.png"),
            "_rainbow_bottom_bg": cls._open_image(pic_dir / "rainbow_bottom.png"),
            "_aurora_bg": cls._open_image(pic_dir / "aurora.png"),
            "_shines_bg": cls._open_image(pic_dir / "bg_shines.png"),
            "_pattern_bg": cls._open_image(pic_dir / "pattern.png"),
            "_moon_bg": cls._open_image(pic_dir / "moon.png"),
        }

    @classmethod
    def _load_image(cls) -> None:
        """将图片缓存在内存"""
        if cls._images_loaded:
            return
        for name, image in cls._create_images().items():
            setattr(cls, name, image)
        cls._images_loaded = True

    def _themed_image(self, theme: Theme, name: str) -> Image.Image:
        """
        根据主题选择图片

        Params:
            `theme`: 主题
            `name`: 文件名
        Returns:
            `Image.Image`
        """
        key = (theme, name)
        if maiconfig.save_in_memory:
            image = self._themed_images.get(key)
            if image is None:
                image = self._open_image(pic_dir / theme.value / name)
                self._themed_images[key] = image
            return image
        return self._open_image(pic_dir / theme.value / name)
