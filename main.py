import sys
import ctypes
from ui.app import DownloaderApp
from core.logger import logger

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def main():
    try:
        if sys.platform.startswith('win'):
            try: ctypes.windll.shcore.SetProcessDpiAwareness(1)
            except: pass
            
        app = DownloaderApp()
        app.run()
    except Exception as e:
        logger.error(f"Application error: {e}", exc_info=True)
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
