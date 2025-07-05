import time
import os
import inspect
from datetime import datetime, timezone
from contextlib import asynccontextmanager
import logging
from app.util.config import config

    
COLORS = {
    'DEBUG:': '\033[94m',
    'INFO:': '\033[70m',
    'WARNING:': '\033[33m',
    'ERROR:': '\033[31m',
    'CRITICAL:': '\033[101m',
    'RESET:': '\033[0m'
}

class CustomFormatter(logging.Formatter):
    def format(self, record):
        color = COLORS.get(record.levelname, COLORS['RESET:'])
        log_fmt = f'{color}{record.levelname:<8}{COLORS['RESET:']} {record.filename}:{record.lineno}  →  {record.msg}'
        return log_fmt

console_handler = logging.StreamHandler()
console_handler.setFormatter(CustomFormatter())

logger = logging.getLogger('aigf')
logger.setLevel(logging.DEBUG)
logger.addHandler(console_handler)

uvicorn_logger = logging.getLogger('uvicorn')
uvicorn_logger.setLevel(logging.DEBUG)
uvicorn_logger.addHandler(console_handler)
uvicorn_logger.propagate = False

sqlalchemy_logger = logging.getLogger('sqlalchemy.engine.Engine')
sqlalchemy_logger.setLevel(logging.WARNING)
sqlalchemy_logger.disabled = True


def get_caller_filename():
    first_outer_filepath = next(f.filename for f in inspect.stack() if 'logger.py' not in f.filename)
    filename = os.path.basename(first_outer_filepath)
    return filename


@asynccontextmanager
async def log_time(name='Operation'):
    start = time.perf_counter()
    yield
    end = time.perf_counter()
    logger.info(f' ⏳ MEASURE TIME: {name.capitalize()} took {end - start:.6f} sec')

width = config.LOG_BLOCK_WIDTH

def logger_block_header(right_caption = '', double = False):
    r = right_caption
    l = '═' if double else '─'
    cl = '╔' if double else '┌'
    cr = '╗' if double else '┐'
    clock = ' ' + datetime.now(timezone.utc).strftime("%A • %B %d • %H:%M") + ' utc '
    filling = (width - 10 - len(clock) - len(r)) * l
    return cl + l * 3 + clock + filling + (f' {r} ' if r else l * 2) + l * 3 + cr


def logger_block_body(text: str, extra_indent = 0, double = False): # extra_indent = 1 for 3-digit caller line
    indent = len(get_caller_filename()) + 17 + extra_indent # file.py + 17chars for 2-digit caller line
    l = '║ ' if double else '│ '
    w = width - 4
    glue = '\n' + indent * " " + l
    return l + glue.join([
        glue.join([
            line[i:i+w] for i in range(0, len(line), w)
        ]) for line in text.split('\n')
    ])


def logger_block_footer(right_caption = '', double = False):
    r = right_caption
    l = '═' if double else '─'
    cl = '╚' if double else '└'
    cr = '╝' if double else '┘'
    filling = (width - 7 - len(r)) * l
    return cl + filling + (f' {r} ' if r else l * 2) + l * 3 + cr

