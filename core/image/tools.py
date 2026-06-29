import base64
from io import BytesIO
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

from ...resources import SHANGGUMONO, cover_dir


class DrawText:
    def __init__(self, image: ImageDraw.ImageDraw, font: Path) -> None:
        self._img = image
        self._font = str(font)

    def get_box(self, text: str, size: int) -> tuple[float, float, float, float]:
        return ImageFont.truetype(self._font, size).getbbox(text)

    def draw(
        self,
        pos_x: int,
        pos_y: int,
        size: int,
        text: str | int | float,
        color: tuple[int, int, int, int] = (255, 255, 255, 255),
        anchor: str = "lt",
        stroke_width: int = 0,
        stroke_fill: tuple[int, int, int, int] = (0, 0, 0, 0),
        multiline: bool = False,
    ) -> None:
        font = ImageFont.truetype(self._font, size)
        if multiline:
            self._img.multiline_text(
                (pos_x, pos_y),
                str(text),
                color,
                font,
                anchor,
                stroke_width=stroke_width,
                stroke_fill=stroke_fill,
            )
        else:
            self._img.text(
                (pos_x, pos_y),
                str(text),
                color,
                font,
                anchor,
                stroke_width=stroke_width,
                stroke_fill=stroke_fill,
            )


def hex_to_rgb(hex_str: str) -> tuple[int, ...]:
    hex_str = hex_str.lstrip("#")
    return tuple(int(hex_str[i : i + 2], 16) for i in (0, 2, 4))


def tricolor_gradient_prism_plus(width: int, height: int) -> Image.Image:
    """
    垂直绘制 PRiSM PLUS 渐变背景

    Params:
        `width`: 宽度
        `height`: 高度
    Returns:
        `Image.Image`
    """
    colors_list = [
        (0.0, hex_to_rgb("#ffffff")),
        (0.14, hex_to_rgb("#ffffff")),
        (0.24, hex_to_rgb("#ffd5cf")),
        (0.46, hex_to_rgb("#ffd5cf")),
        (0.56, hex_to_rgb("#ffc5d5")),
        (0.67, hex_to_rgb("#eaabff")),
        (0.85, hex_to_rgb("#72bcfe")),
        (0.95, hex_to_rgb("#65f2df")),
        (1.0, hex_to_rgb("#65f2df")),
    ]
    line = Image.new("RGBA", (1, height))

    for y in range(height):
        t = 1.0 - (y / (height - 1)) if height > 1 else 0

        for i in range(len(colors_list) - 1):
            p1, c1 = colors_list[i]
            p2, c2 = colors_list[i + 1]
            if p1 <= t <= p2:
                rel_t = (t - p1) / (p2 - p1)
                rgb = tuple(int(c1[j] + (c2[j] - c1[j]) * rel_t) for j in range(3))
                line.putpixel((0, y), rgb)
                break

    return line.resize((width, height), resample=Image.Resampling.BICUBIC)


def radial_gradient(
    width: int,
    height: int,
    colors: list[tuple[int, int, int]] = [
        (255, 223, 233),
        (255, 162, 198),
        (255, 12, 235),
    ],
    positions: list[float] = [0, 0.5, 1],
) -> Image.Image:
    """
    绘制径向渐变色

    Params:
        `width`: 宽度
        `height`: 高度
        `colors`: 颜色
        `positions`: 透明度
    Returns:
        `Image.Image`
    """
    y, x = np.ogrid[:height, :width]
    cx, cy = (width / 2, height / 2)

    dist = np.sqrt((x - cx) ** 2 + (y - cy) ** 2)

    max_radius = (height / 2) * 1.3

    dist = dist / max_radius
    dist = np.clip(dist, 0, 1)
    img = np.zeros((height, width, 3), dtype=np.float32)

    for i in range(len(colors) - 1):
        c1 = np.array(colors[i])
        c2 = np.array(colors[i + 1])
        p1 = positions[i]
        p2 = positions[i + 1]

        mask = (dist >= p1) & (dist <= p2)
        if p2 > p1:
            t = (dist[mask] - p1) / (p2 - p1)
        else:
            t = 0

        img[mask] = c1 * (1 - t[:, None]) + c2 * t[:, None]

    return Image.fromarray(img.astype(np.uint8), mode="RGB")


def generate_frosted_card(
    im: Image.Image,
    box: tuple[int, int, int, int],
    shadow_offset: tuple[int, int] = (10, 10),
    alpha: float = 0.4,
) -> Image.Image:
    """
    绘制毛玻璃

    Params:
        `im`: `Image` 图像
        `box`: 方形毛玻璃的坐标
        `shadow_offset`: 投影像素
        `alpha`: 透明度，按百分比 0-1
    Returns:
        `Image.Image`
    """
    if alpha < 0 or alpha > 1:
        raise ValueError
    roi = im.crop(box)
    roi_w, roi_h = roi.size

    frosted = roi.filter(ImageFilter.GaussianBlur(4))
    white_layer = Image.new("RGBA", (roi_w, roi_h), (255, 255, 255, int(255 * alpha)))
    card = Image.alpha_composite(frosted, white_layer)

    mask = Image.new("L", (roi_w, roi_h), 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle((0, 0, roi_w, roi_h), radius=25, fill=255)

    # 投影
    shadow_w = roi_w + 5 * 2 + abs(shadow_offset[0])
    shadow_h = roi_h + 5 * 2 + abs(shadow_offset[1])
    shadow = Image.new("RGBA", (shadow_w, shadow_h), (0, 0, 0, 0))

    draw_shadow = ImageDraw.Draw(shadow)
    draw_shadow.rounded_rectangle(
        (15, 15, 15 + roi_w, 15 + roi_h), radius=25, fill=(0, 0, 0, 50)
    )
    shadow_layer = shadow.filter(ImageFilter.GaussianBlur(3))

    temp_layer = Image.new("RGBA", im.size, (0, 0, 0, 0))
    shadow_pos = (box[0] + shadow_offset[0] - 15, box[1] + shadow_offset[1] - 15)
    temp_layer.paste(shadow_layer, shadow_pos)
    temp_layer.paste(card, (box[0], box[1]), mask=mask)

    new_im = Image.alpha_composite(im, temp_layer)
    return new_im


def rounded_corners(
    image: Image.Image,
    radius: int,
    corners: tuple[bool, bool, bool, bool] = (False, False, False, False),
) -> Image.Image:
    """
    绘制圆角

    Params:
        `image`: `PIL.Image.Image`
        `radius`: 圆角半径
        `corners`: 四个角是否绘制圆角，分别是左上、右上、右下、左下
    Returns:
        `PIL.Image.Image`
    """
    mask = Image.new("L", image.size, 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle(
        (0, 0, image.size[0], image.size[1]), radius, fill=255, corners=corners
    )

    new_im = ImageOps.fit(image, mask.size)
    new_im.putalpha(mask)

    return new_im


def song_chart(song_id: int | str) -> Path:
    """
    获取谱面图片路径

    Params:
        `song_id`: 谱面 ID
    Returns:
        `Path`
    """
    song_id = int(song_id) % 10000
    _path = cover_dir / f"{song_id}.png"

    return _path if _path.exists() else cover_dir / "0.png"


def text_to_image(text: str) -> Image.Image:
    font = ImageFont.truetype(str(SHANGGUMONO), 24)
    padding = 10
    margin = 4
    lines = text.strip().split("\n")
    max_width = 0
    b = 0
    for line in lines:
        l, t, r, b = font.getbbox(line)  # noqa: E741
        max_width = max(max_width, r)
    wa = max_width + padding * 2
    ha = b * len(lines) + margin * (len(lines) - 1) + padding * 2
    im = Image.new("RGB", (wa, ha), color=(255, 255, 255))
    draw = ImageDraw.Draw(im)
    for index, line in enumerate(lines):
        draw.text(
            (padding, padding + index * (margin + b)), line, font=font, fill=(0, 0, 0)
        )
    return im


def text_to_bytes_io(text: str) -> BytesIO:
    bio = BytesIO()
    text_to_image(text).save(bio, format="PNG")
    bio.seek(0)
    return bio


def base64_to_bytesio(base64_str: str) -> BytesIO:
    if base64_str.startswith("base64://"):
        base64_str = base64_str[len("base64://") :]
    byte_data = base64.b64decode(base64_str)
    return BytesIO(byte_data)


def image_to_base64(img: Image.Image, format="PNG") -> str:
    output_buffer = BytesIO()
    img.save(output_buffer, format)
    byte_data = output_buffer.getvalue()
    base64_str = base64.b64encode(byte_data).decode()
    return "base64://" + base64_str
