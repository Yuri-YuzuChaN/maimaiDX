import sys
from pathlib import Path

from loguru import logger

LOG_PATH = Path(__file__).parent / "logs"
LOG_PATH.mkdir(exist_ok=True)

logger.remove()

logger.add(
    sys.stdout,
    level="INFO",
    colorize=True,
    format=(
        "<green>{time:HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>maimai</cyan> - "
        "<level>{message}</level>"
    ),
)

logger.add(
    LOG_PATH / "maimai_{time:YYYY-MM-DD}.log",
    level="INFO",
    rotation="10 MB",
    retention="7 days",
    encoding="utf-8",
    enqueue=True,
)

logger.opt(colors=True).info(
    "maimaiDX插件加载成功。<r>该插件使用独立的log和logs文件夹。</r>"
)
