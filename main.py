import sys
import os

# 确保在导入其他模块之前，工作目录是正确的
if getattr(sys, 'frozen', False):
    sys.path.append(os.path.dirname(sys.executable))
else:
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from gui import ModernApp
from utils import logger

if __name__ == "__main__":
    try:
        app = ModernApp()
        app.mainloop()
    except Exception as e:
        logger.exception("Application crashed: %s", e)
