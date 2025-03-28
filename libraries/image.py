import base64
from io import BytesIO
from typing import Tuple, Union

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps

from .. import SHANGGUMONO, Path, coverdir


class DrawText:

    def __init__(self, image: ImageDraw.ImageDraw, font: Path) -> None:
        self._img = image
        self._font = str(font)

    def get_box(self, text: str, size: int) -> Tuple[float, float, float, float]:
        return ImageFont.truetype(self._font, size).getbbox(text)

    def draw(
        self,
        pos_x: int,
        pos_y: int,
        size: int,
        text: Union[str, int, float],
        color: Tuple[int, int, int, int] = (255, 255, 255, 255),
        anchor: str = 'lt',
        stroke_width: int = 0,
        stroke_fill: Tuple[int, int, int, int] = (0, 0, 0, 0),
        multiline: bool = False
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
                stroke_fill=stroke_fill
            )
        else:
            self._img.text(
                (pos_x, pos_y), 
                str(text), 
                color, 
                font, 
                anchor, 
                stroke_width=stroke_width, 
                stroke_fill=stroke_fill
            )


def tricolor_gradient(
    width: int, 
    height: int, 
    color1: Tuple[int, int, int] = (124, 129, 255), 
    color2: Tuple[int, int, int] = (193, 247, 225), 
    color3: Tuple[int, int, int] = (255, 255, 255)
) -> Image.Image:
    """绘制渐变色"""
    array = np.zeros((height, width, 3), dtype=np.uint8)
    
    for y in range(height):
        if y < height * 0.4:
            ratio = y / (height * 0.4)
            color = (1 - ratio) * np.array(color1) + ratio * np.array(color2)
        else:
            ratio = (y - height * 0.4) / (height * 0.6)
            color = (1 - ratio) * np.array(color2) + ratio * np.array(color3)
        array[y, :] = np.clip(color, 0, 255)
    
    image = Image.fromarray(array).convert('RGBA')
    return image


def rounded_corners(
    image: Image.Image,
    radius: int, 
    corners: Tuple[bool, bool, bool, bool] = (False, False, False, False)
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
    mask = Image.new('L', image.size, 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle((0, 0, image.size[0], image.size[1]), radius, fill=255, corners=corners)

    new_im = ImageOps.fit(image, mask.size)
    new_im.putalpha(mask)

    return new_im


def music_picture(music_id: Union[int, str]) -> Path:
    """
    获取谱面图片路径
    
    Params:
        `music_id`: 谱面 ID
    Returns:
        `Path`
    """
    music_id = int(music_id)
    if (_path := coverdir / f'{music_id}.png').exists():
        return _path
    if music_id > 100000:
        music_id -= 100000
        if (_path := coverdir / f'{music_id}.png').exists():
            return _path
    if 1000 < music_id < 10000 or 10000 < music_id <= 11000:
        for _id in [music_id + 10000, music_id - 10000]:
            if (_path := coverdir / f'{_id}.png').exists():
                return _path
    return coverdir / '11000.png'


def text_to_image(text: str) -> Image.Image:
    font = ImageFont.truetype(str(SHANGGUMONO), 24)
    padding = 10
    margin = 4
    lines = text.strip().split('\n')
    max_width = 0
    b = 0
    for line in lines:
        l, t, r, b = font.getbbox(line)
        max_width = max(max_width, r)
    wa = max_width + padding * 2
    ha = b * len(lines) + margin * (len(lines) - 1) + padding * 2
    im = Image.new('RGB', (wa, ha), color=(255, 255, 255))
    draw = ImageDraw.Draw(im)
    for index, line in enumerate(lines):
        draw.text((padding, padding + index * (margin + b)), line, font=font, fill=(0, 0, 0))
    return im


def image_to_base64(img: Image.Image, format='PNG') -> str:
    output_buffer = BytesIO()
    img.save(output_buffer, format)
    byte_data = output_buffer.getvalue()
    base64_str = base64.b64encode(byte_data).decode()
    return 'base64://' + base64_str