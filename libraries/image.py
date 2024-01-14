import base64
from io import BytesIO
from typing import Tuple

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from .. import SIYUAN


class DrawText:

    def __init__(self, image: ImageDraw.ImageDraw, font: str) -> None:
        self._img = image
        self._font = str(font)

    def get_box(self, text: str, size: int):
        return ImageFont.truetype(self._font, size).getbbox(text)

    def draw(self,
            pos_x: int,
            pos_y: int,
            size: int,
            text: str,
            color: Tuple[int, int, int, int] = (255, 255, 255, 255),
            anchor: str = 'lt',
            stroke_width: int = 0,
            stroke_fill: Tuple[int, int, int, int] = (0, 0, 0, 0),
            multiline: bool = False):

        font = ImageFont.truetype(self._font, size)
        if multiline:
            self._img.multiline_text((pos_x, pos_y), str(text), color, font, anchor, stroke_width=stroke_width, stroke_fill=stroke_fill)
        else:
            self._img.text((pos_x, pos_y), str(text), color, font, anchor, stroke_width=stroke_width, stroke_fill=stroke_fill)
    
    def draw_partial_opacity(self,
            pos_x: int,
            pos_y: int,
            size: int,
            text: str,
            po: int = 2,
            color: Tuple[int, int, int, int] = (255, 255, 255, 255),
            anchor: str = 'lt',
            stroke_width: int = 0,
            stroke_fill: Tuple[int, int, int, int] = (0, 0, 0, 0)):

        font = ImageFont.truetype(self._font, size)
        self._img.text((pos_x + po, pos_y + po), str(text), (0, 0, 0, 128), font, anchor, stroke_width=stroke_width, stroke_fill=stroke_fill)
        self._img.text((pos_x, pos_y), str(text), color, font, anchor, stroke_width=stroke_width, stroke_fill=stroke_fill)


def draw_gradient(width: int, 
        height: int, 
        rgb_start: Tuple[int, int, int] = (203, 162, 253), 
        rgb_stop: Tuple[int, int, int] = (251, 244, 127), 
        horizontal: Tuple[bool, bool, bool] = (False, False, False)
    ) -> Image.Image:
    result = np.zeros((height, width, 3), dtype=np.uint8)
    for i, (start, stop, is_ho) in enumerate(zip(rgb_start, rgb_stop, horizontal)):
        if is_ho:
            result[:, :, i] = np.tile(np.linspace(start, stop, width), (height, 1))
        else:
            result[:, :, i] = np.tile(np.linspace(start, stop, height), (width, 1)).T

    return Image.fromarray(result).convert('RGBA')


def draw_text(img_pil: Image.Image, text: str, offset_x: float):
    draw = ImageDraw.Draw(img_pil)
    font = ImageFont.truetype(str(SIYUAN), 48)
    width, height = draw.textsize(text, font)
    x = 5
    if width > 390:
        font = ImageFont.truetype(str(SIYUAN), int(390 * 48 / width))
        width, height = draw.textsize(text, font)
    else:
        x = int((400 - width) / 2)
    draw.rectangle((x + offset_x - 2, 360, x + 2 + width + offset_x, 360 + height * 1.2), fill=(0, 0, 0, 255))
    draw.text((x + offset_x, 360), text, font=font, fill=(255, 255, 255, 255))


def text_to_image(text: str) -> Image.Image:
    font = ImageFont.truetype(str(SIYUAN), 24)
    padding = 10
    margin = 4
    text_list = text.split('\n')
    max_width = 0
    for text in text_list:
        l, t, r, b = font.getbbox(text)
        max_width = max(max_width, r)
    wa = max_width + padding * 2
    ha = b * len(text_list) + margin * (len(text_list) - 1) + padding * 2
    i = Image.new('RGB', (wa, ha), color=(255, 255, 255))
    draw = ImageDraw.Draw(i)
    for j in range(len(text_list)):
        text = text_list[j]
        draw.text((padding, padding + j * (margin + b)), text, font=font, fill=(0, 0, 0))
    return i


def image_to_base64(img: Image.Image, format='PNG') -> str:
    output_buffer = BytesIO()
    img.save(output_buffer, format)
    byte_data = output_buffer.getvalue()
    base64_str = base64.b64encode(byte_data).decode()
    return 'base64://' + base64_str
