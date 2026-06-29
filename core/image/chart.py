import pyecharts.options as opts
from PIL import Image, ImageDraw
from pyecharts.charts import Pie

from ...config import maiconfig
from ...constants import ACHIEVEMENT_LIST, COMBO_PLUS, DIFFS, RANK_PLUS
from ...resources import FOTNEWRODIN, SIYUAN, pic_dir, pie_html_file
from ..merge.models import PlayedResult, Song, Theme
from ..tool import run_chrome_to_base64
from ..utils.calc import compute_rating
from .base import change_column_width, coloum_width
from .tools import (
    DrawText,
    image_to_base64,
    song_chart,
)

NOTE_FIELDS = ["total", "tap", "hold", "slide", "touch", "brk"]


async def song_global_data(song: Song, level_index: int) -> str:
    """
    绘制曲目游玩详情

    Params:
        `song`: 曲目 `Song`
        `level_index`: 难度
    Returns:
        `base64 str`
    """
    stats = song.difficulties[level_index].stats
    fc_data_pair = [
        list(_)
        for _ in zip(
            [c.upper() if c else "Not FC" for c in [""] + COMBO_PLUS], stats.fc_dist
        )
    ]
    acc_data_pair = [list(_) for _ in zip([s.upper() for s in RANK_PLUS], stats.dist)]

    rich = (
        {
            "a": {"color": "#999", "lineHeight": 22, "align": "center"},
            "abg": {
                "backgroundColor": "#e3e3e3",
                "width": "100%",
                "align": "right",
                "height": 22,
                "borderRadius": [4, 4, 0, 0],
            },
            "hr": {
                "borderColor": "#aaa",
                "width": "100%",
                "borderWidth": 0.5,
                "height": 0,
            },
            "b": {"fontSize": 16, "lineHeight": 33},
            "per": {
                "color": "#eee",
                "backgroundColor": "#334455",
                "padding": [2, 4],
                "borderRadius": 2,
            },
        },
    )

    initopts = opts.InitOpts(
        width="1000px", height="800px", bg_color="#fff", js_host="./"
    )
    labelopts = opts.LabelOpts(
        position="outside",
        formatter="{a|{a}}{abg|}\n{hr|}\n {b|{b}: }{c}  {per|{d}%}  ",
        background_color="#eee",
        border_color="#aaa",
        border_width=1,
        border_radius=4,
        rich=rich,
    )
    titleopts = opts.TitleOpts(
        title=f"{song.song_id} {song.song_name} 「{DIFFS[level_index]}」",
        pos_left="center",
        pos_top="20",
        title_textstyle_opts=opts.TextStyleOpts(color="#2c343c"),
    )
    legendopts = opts.LegendOpts(pos_left=15, pos_top=10, orient="vertical")
    tooltipopts = opts.TooltipOpts(trigger="item", formatter="{a} <br/>{b}: {c} ({d}%)")

    pie = Pie(initopts)
    pie.add("全连等级", fc_data_pair, radius=[0, "30%"], label_opts=labelopts)
    pie.add(
        "达成率等级",
        acc_data_pair,
        radius=["50%", "70%"],
        is_clockwise=True,
        label_opts=labelopts,
    )
    pie.set_global_opts(title_opts=titleopts, legend_opts=legendopts)
    pie.set_series_opts(tooltip_opts=tooltipopts)
    pie.render(str(pie_html_file))
    base64 = await run_chrome_to_base64()

    return base64


def get_best_rating(rating: float) -> list[int]:
    last_item = ACHIEVEMENT_LIST[-1]
    ra = [compute_rating(rating, r) for r in ACHIEVEMENT_LIST[-6:]]
    ra.append(compute_rating(rating, last_item) + 1)
    ra.sort(reverse=True)
    return ra


def new_best_score(
    song_id: int, level_index: int, value: int, bestlist: list[PlayedResult]
) -> int:
    for v in bestlist:
        if song_id == v.song_id and level_index == v.level_index:
            if value >= v.rating:
                return value - v.rating
            else:
                return 0
    return value - bestlist[-1].rating


def song_chart_info(
    song: Song, calc: bool, is_full: bool, best_list: list[PlayedResult], theme: Theme
) -> str:
    """
    绘制谱面信息

    Params:
        `song`: 曲目模型
        `qqid`: qqid
        `user`: 用户模型
    Returns:
        `base64 str`
    """
    im = Image.open(pic_dir / theme.value / "chart_info.png").convert("RGBA")
    dr = ImageDraw.Draw(im)
    mr = DrawText(dr, SIYUAN)
    fn = DrawText(dr, FOTNEWRODIN)

    if theme == Theme.CIRCLE:
        text_color = (249, 62, 172, 255)
    else:
        text_color = (124, 129, 255, 255)

    # logo
    im.alpha_composite(
        Image.open(pic_dir / theme.value / "logo.png").resize((249, 120)), (65, 25)
    )

    # new
    if song.isnew:
        im.alpha_composite(
            Image.open(pic_dir / "UI_CMN_TabTitle_NewSong.png").resize((249, 120)),
            (842, 100),
        )

    # cover
    im.alpha_composite(
        Image.open(song_chart(song.song_id)).resize((242, 242)), (133, 197)
    )
    # version
    im.alpha_composite(
        Image.open(pic_dir / f"{song.version_str}.png").resize((182, 90)), (800, 370)
    )
    # type
    im.alpha_composite(
        Image.open(pic_dir / f"{song.type}.png").resize((80, 30)), (295, 410)
    )

    # title
    title = song.song_name
    if coloum_width(title) > 40:
        title = change_column_width(title, 39) + "..."
    fn.draw(405, 220, 28, title, text_color, "lm")

    # artist
    artist = song.artist
    if coloum_width(artist) > 50:
        artist = change_column_width(artist, 49) + "..."
    fn.draw(407, 265, 20, artist, text_color, "lm")
    # bpm
    fn.draw(460, 345, 24, song.bpm, text_color, "lm")
    # id
    fn.draw(405, 435, 22, f"ID {song.song_id}", text_color, "lm")
    # genre
    mr.draw(665, 435, 24, song.genre, text_color, "mm")

    for index, v in enumerate(song.difficulties):
        if index == 4:
            color = (255, 255, 255, 255)
        else:
            color = (255, 255, 255, 255)
        # 间距
        spacing = 70 * index
        # 定数
        fn.draw(120, 590 + spacing, 22, f"{v.level}({v.level_value})", color, "mm")
        # 拟合
        fitting = f"擬 - {round(v.stats.fit_diff, 2)}" if v.stats else "-"
        fn.draw(120, 613 + spacing, 15, fitting, color, "mm")
        # 谱师
        designer = v.note_designer
        if coloum_width(designer) > 19:
            designer = change_column_width(designer, 18) + "..."
        mr.draw(310, 590 + spacing, 20, designer, text_color, "mm")
        # notes
        for n, field in enumerate(NOTE_FIELDS):
            n_value = getattr(v.notes, field)
            fn.draw(480 + 122 * n, 590 + spacing, 25, n_value, text_color, "mm")

        if index > 1:
            ra = get_best_rating(v.level_value)
            for _n, value in enumerate(ra):
                size = 22
                if not calc:
                    rating = value
                elif not is_full:
                    size = 17
                    rating = f"{value}(↑{value})"
                elif value > best_list[-1].rating:
                    new = new_best_score(song.song_id, index, value, best_list)
                    if new == 0:
                        rating = value
                    else:
                        size = 17
                        rating = f"{value}(↑{new})"
                else:
                    rating = value
                fn.draw(
                    295 + 125 * _n,
                    1017 + 46 * (index - 2),
                    size,
                    rating,
                    text_color,
                    "mm",
                )
    mr.draw(295, 985, 12, "*未实装", anchor="mm")
    fn.draw(
        600,
        1220,
        25,
        f"Designed by Yuri-YuzuChaN & BlueDeer233. Generated by {maiconfig.bot_name} BOT",
        text_color,
        "mm",
        3,
        (255, 255, 255, 255),
    )
    return image_to_base64(im)


def song_chart_banquet_info(song: Song) -> str:
    """
    绘制宴会场谱面信息

    Params:
        `song`: 曲目模型
    Returns:
        `base64 str`
    """

    im = Image.open(pic_dir / "chart_info_enkaijou.png")
    dr = ImageDraw.Draw(im)
    fn = DrawText(dr, FOTNEWRODIN)

    stroke_color = (210, 57, 174, 255)
    kanji_bg = Image.open(pic_dir / "utg_kanji.png")

    im.alpha_composite(kanji_bg, (140, 660 if song.is_buddy else 730))
    # kanji
    if song.is_buddy:
        player_path = pic_dir / "utg_2p.png"
        p_y = 715
        base_y = 820
        step_y = 100
        im.alpha_composite(Image.open(pic_dir / "utg_buddy.png"), (255, 660))
    else:
        player_path = pic_dir / "utg_1p.png"
        p_y = 785
        base_y = 890
        step_y = 0

    im.alpha_composite(Image.open(player_path).convert("RGBA"), (98, p_y))

    # logo
    im.alpha_composite(
        Image.open(pic_dir / Theme.PRISM_PLUS.value / "logo.png").resize((249, 120)),
        (10, 35),
    )
    # new
    if song.isnew:
        im.alpha_composite(
            Image.open(pic_dir / "UI_CMN_TabTitle_NewSong.png").resize((249, 120)),
            (950, 165),
        )
    # cover
    im.alpha_composite(
        Image.open(song_chart(song.song_id)).resize((242, 242)), (133, 246)
    )
    # version
    im.alpha_composite(
        Image.open(pic_dir / f"{song.version_str}.png").resize((182, 90)), (800, 415)
    )

    fn.draw(216, p_y - 28, 18, song.kanji, anchor="mm")
    # title
    title = song.song_name
    if coloum_width(title) > 36:
        title = change_column_width(title, 35) + "..."
    fn.draw(405, 265, 28, title, anchor="lm", stroke_width=3, stroke_fill=stroke_color)
    # artist
    artist = song.artist
    if coloum_width(artist) > 50:
        artist = change_column_width(artist, 49) + "..."
    fn.draw(407, 320, 20, artist, anchor="lm", stroke_width=3, stroke_fill=stroke_color)
    # bpm
    fn.draw(
        460, 393, 24, song.bpm, anchor="lm", stroke_width=3, stroke_fill=stroke_color
    )
    # id
    fn.draw(
        405,
        475,
        22,
        f"ID {song.song_id}",
        anchor="lm",
        stroke_width=3,
        stroke_fill=stroke_color,
    )
    # genre
    fn.draw(
        680, 475, 22, song.genre, anchor="mm", stroke_width=3, stroke_fill=stroke_color
    )
    # description
    fn.draw(595, 595, 25, song.description, anchor="mm")
    # level
    fn.draw(
        180,
        p_y + 28,
        24,
        f"Lv. {song.difficulties[0].level}",
        anchor="mm",
        stroke_width=3,
        stroke_fill=stroke_color,
    )
    # notes
    for index, v in enumerate(song.difficulties):
        for n, field in enumerate(NOTE_FIELDS):
            n_value = getattr(v.notes, field)
            fn.draw(
                330 + 140 * n,
                base_y + step_y * index,
                25,
                n_value,
                anchor="mm",
                stroke_width=3,
                stroke_fill=stroke_color,
            )
    fn.draw(
        600,
        1100,
        30,
        f"Designed by Yuri-YuzuChaN & BlueDeer233. Generated by {maiconfig.bot_name} BOT",
        stroke_color,
        "mm",
        5,
        (255, 255, 255, 255),
    )

    return image_to_base64(im)
