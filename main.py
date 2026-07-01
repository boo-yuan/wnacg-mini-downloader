import sys
import ctypes
from ui.app import DownloaderApp
from core.logger import logger

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def check_single_instance():
    if sys.platform.startswith('win'):
        import ctypes
        ERROR_ALREADY_EXISTS = 183
        mutex = ctypes.windll.kernel32.CreateMutexW(None, False, "WNACGMiniDownloader_Instance_Mutex")
        if ctypes.windll.kernel32.GetLastError() == ERROR_ALREADY_EXISTS:
            return False, None
        return True, mutex
    else:
        import socket
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.bind(('127.0.0.1', 48593))
            return True, s
        except socket.error:
            return False, None

def main():
    try:
        is_first, _lock = check_single_instance()
        if not is_first:
            if sys.platform.startswith('win'):
                ctypes.windll.user32.MessageBoxW(0, "程序已经在运行中！", "提示", 0x30)
            print("Application is already running.")
            return

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
