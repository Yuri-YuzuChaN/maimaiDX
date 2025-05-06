import asyncio
import json
import time
from pathlib import Path
from typing import Any, Union

import aiofiles
from playwright.async_api import async_playwright

from .. import SNAPSHOT_JS, pie_html_file


def qqhash(qq: int):
    days = int(time.strftime("%d", time.localtime(time.time()))) + 31 * int(
        time.strftime("%m", time.localtime(time.time()))) + 77
    return (days * qq) >> 8


async def openfile(file: Path) -> Union[dict, list]:
    async with aiofiles.open(file, 'r', encoding='utf-8') as f:
        data = json.loads(await f.read())
    return data


async def writefile(file: Path, data: Any) -> bool:
    async with aiofiles.open(file, 'w', encoding='utf-8') as f:
        await f.write(json.dumps(data, ensure_ascii=False, indent=4))
    return True

async def run_chrome_to_base64() -> str:
    async with async_playwright() as p:
        browers = await p.chromium.launch(headless=True)
        page = await browers.new_page(java_script_enabled=True)
        await page.goto('file://' + str(pie_html_file))
        await asyncio.sleep(2)
        
        content: str = await page.evaluate(SNAPSHOT_JS)
        await browers.close()
        
    content_array = content.split(',')
    if len(content_array) != 2:
        raise OSError(content_array)

    return 'base64://' + content_array[-1]