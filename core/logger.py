import os
import sys
import logging
from logging.handlers import RotatingFileHandler

def get_app_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

LOG_FILE = os.path.join(get_app_dir(), "app.log")
logger = logging.getLogger("wnacg_app")
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(LOG_FILE, encoding='utf-8', delay=True)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s')
handler.setFormatter(formatter)

# Prevent duplicate handlers
if not logger.handlers:
    logger.addHandler(handler)
