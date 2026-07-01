import os
import tkinter as tk
import customtkinter as ctk

from core.logger import get_app_dir
from core.config_manager import config_manager
from core.event_bus import event_bus
from services.update_service import update_service
from services.download_manager import download_manager
from ui.ui_utils import show_toast
from ui.views.search_panel import SearchPanel
from ui.views.queue_panel import QueuePanel
from ui.views.settings_view import SettingsWindow

def get_resource_path(relative_path):
    import sys
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)

class DownloaderApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.color_bg = ("#F3F4F6", "#000000")
        self.color_frame = ("#FFFFFF", "#1C1C1E")
        self.color_text_primary = ("#0F172A", "#F1F5F9")
        self.color_text_secondary = ("#64748B", "#94A3B8")
        self.color_accent = ("#3B82F6", "#0A84FF")
        self.color_accent_hover = ("#2563EB", "#007AFF")
        self.color_item = ("#F8FAFC", "#2C2C2E")
        self.color_item_selected = ("#EFF6FF", "#3A3A3C")
        
        self.app_colors = {
            'bg': self.color_bg,
            'frame': self.color_frame,
            'text_primary': self.color_text_primary,
            'text_secondary': self.color_text_secondary,
            'accent': self.color_accent,
            'accent_hover': self.color_accent_hover,
            'item': self.color_item,
            'item_selected': self.color_item_selected
        }
        
        self.title("WNACG Mini Downloader")
        self.geometry("1100x750")
        self.configure(fg_color=self.color_bg)
        
        icon_path = get_resource_path('icon.ico')
        if os.path.exists(icon_path):
            try: self.after(200, lambda: self.iconbitmap(icon_path))
            except: pass
            
        self.setup_ui()
        self.bind_events()
        
        # initial tasks
        self.after(500, download_manager.sync_disk_state)
        update_service.check_for_updates()

    def setup_ui(self):
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=3)
        self.grid_columnconfigure(1, weight=2)
        
        # --- Top Bar ---
        self.frame_a = ctk.CTkFrame(self, corner_radius=12, fg_color=self.color_frame)
        self.frame_a.grid(row=0, column=0, columnspan=2, padx=15, pady=(15, 5), sticky="nsew")
        self.frame_a.grid_columnconfigure(0, weight=1)
        
        path_frame = ctk.CTkFrame(self.frame_a, fg_color="transparent")
        path_frame.grid(row=0, column=0, padx=25, pady=15, sticky="w")
        
        ctk.CTkLabel(path_frame, text="下载路径:", font=("Microsoft YaHei", 14, "bold"), text_color=self.color_text_primary).pack(side="left", padx=(0, 10))
        self.path_entry = ctk.CTkEntry(path_frame, width=280, fg_color=self.color_item, border_width=0, corner_radius=6, text_color=self.color_text_primary)
        self.path_entry.pack(side="left", padx=(0, 10))
        self.path_entry.insert(0, config_manager.download_path)
        self.path_entry.bind('<Return>', lambda e: self.manual_path_update())
        
        ctk.CTkButton(path_frame, text="浏览...", width=60, font=("Microsoft YaHei", 12), fg_color=self.color_item, hover_color=self.color_item_selected, text_color=self.color_text_primary, corner_radius=6, command=self.choose_download_path).pack(side="left")
        
        ctk.CTkButton(self.frame_a, text="查看日志", width=90, fg_color=self.color_item, text_color=self.color_text_primary, hover_color=self.color_item_selected, corner_radius=6, command=self.open_log).grid(row=0, column=1, padx=5, pady=15)
        ctk.CTkButton(self.frame_a, text="全局设置", width=90, fg_color=self.color_accent, hover_color=self.color_accent_hover, corner_radius=6, command=self.open_settings).grid(row=0, column=2, padx=20, pady=15)
        
        # --- Main Content ---
        # Left: Search
        self.search_panel = SearchPanel(self, self.app_colors)
        self.search_panel.grid(row=1, column=0, padx=(15, 5), pady=(5, 15), sticky="nsew")
        self.search_panel.configure(fg_color=self.color_frame, corner_radius=15)
        
        # Right: Queue
        right_container = ctk.CTkFrame(self, fg_color="transparent")
        right_container.grid(row=1, column=1, padx=(5, 15), pady=(5, 15), sticky="nsew")
        right_container.grid_rowconfigure(0, weight=1)
        right_container.grid_columnconfigure(0, weight=1)
        
        self.queue_panel = QueuePanel(right_container, self.app_colors)
        self.queue_panel.grid(row=0, column=0, sticky="nsew")
        self.queue_panel.configure(fg_color=self.color_frame, corner_radius=15)
        
    def bind_events(self):
        event_bus.subscribe("TOAST", self.on_toast)

    def on_toast(self, message, type="info"):
        self.after(0, lambda: show_toast(self, message, type))

    def manual_path_update(self):
        new_path = self.path_entry.get().strip()
        if os.path.isdir(new_path) or new_path:
            config_manager.download_path = os.path.normpath(new_path)
            config_manager.save_config()
            event_bus.emit("PATH_CHANGED", config_manager.download_path)
        else:
            self.path_entry.delete(0, 'end')
            self.path_entry.insert(0, config_manager.download_path)

    def choose_download_path(self):
        import tkinter.filedialog as fd
        path = fd.askdirectory(initialdir=config_manager.download_path, title="选择下载保存路径")
        if path:
            path = os.path.normpath(path)
            self.path_entry.delete(0, 'end')
            self.path_entry.insert(0, path)
            self.manual_path_update()

    def open_log(self):
        try:
            import platform
            import subprocess
            from core.logger import LOG_FILE
            if platform.system() == 'Windows':
                os.startfile(LOG_FILE)
            elif sys.platform == "darwin":
                subprocess.call(["open", LOG_FILE])
            else:
                subprocess.call(["xdg-open", LOG_FILE])
        except Exception as e:
            from core.logger import logger
            logger.error(f"Cannot open log file: {e}")

    def open_settings(self):
        SettingsWindow(self)

    def run(self):
        self.mainloop()
