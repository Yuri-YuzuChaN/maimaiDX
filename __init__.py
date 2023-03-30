import os
from loguru import logger as log
BOTNAME = 'mokabot'

static = os.path.join(os.path.dirname(__file__), 'static')

__all__ = ['maimai', 'web']

from . import *
