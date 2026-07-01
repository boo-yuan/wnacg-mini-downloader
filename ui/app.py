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
        
        # Color System
        self.app_colors = {
            'bg': ("#F3F4F6", "#000000"),
            'frame': ("#FFFFFF", "#1C1C1E"),
            'item_default': ("#F1F5F9", "#2C2C2E"),
            'item_selected': ("#DBEAFE", "#1E3A8A"),
            'item_border_selected': ("#2563EB", "#3B82F6"),
            'btn_primary': ("#3B82F6", "#0A84FF"),
            'btn_primary_hover': ("#2563EB", "#007AFF"),
            'btn_secondary': ("#D1D5DB", "#3A3A3C"),
            'btn_secondary_hover': ("#9CA3AF", "#4C4C50"),
            'btn_warning': ("#F59E0B", "#D97706"),
            'btn_disabled': ("#E5E5EA", "#3A3A3C"),
            'text_primary': ("#0F172A", "#F1F5F9"),
            'text_secondary': ("#64748B", "#94A3B8"),
            'text_on_primary': ("#FFFFFF", "#FFFFFF")
        }

        # Typography System
        self.app_fonts = {
            'h1': ("Microsoft YaHei", 24, "bold"),
            'h2': ("Microsoft YaHei", 16, "bold"),
            'body_bold': ("Microsoft YaHei", 14, "bold"),
            'body': ("Microsoft YaHei", 14, "normal"),
            'small': ("Microsoft YaHei", 12, "normal")
        }
        
        self.title("WNACG Mini Downloader")
        self.geometry("950x1000")
        self.minsize(800, 600)
        self.configure(fg_color=self.app_colors['bg'])
        
        icon_path = get_resource_path('icon.ico')
        if os.path.exists(icon_path):
            try: self.after(200, lambda: self.iconbitmap(icon_path))
            except: pass
            
        self.setup_ui()
        self.bind_events()
        self.bind("<FocusIn>", self.on_focus_in)
        
        self.after(500, download_manager.sync_disk_state)
        update_service.check_for_updates()

    def setup_ui(self):
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=5)
        self.grid_columnconfigure(1, weight=4)
        
        # --- Top Bar ---
        self.frame_a = ctk.CTkFrame(self, corner_radius=16, fg_color=self.app_colors['frame'])
        self.frame_a.grid(row=0, column=0, columnspan=2, padx=16, pady=(16, 8), sticky="nsew")
        self.frame_a.grid_columnconfigure(0, weight=1)
        
        path_frame = ctk.CTkFrame(self.frame_a, fg_color="transparent")
        path_frame.grid(row=0, column=0, padx=16, pady=8, sticky="w")
        
        ctk.CTkLabel(path_frame, text="保存路径:", font=self.app_fonts['body_bold'], text_color=self.app_colors['text_primary']).pack(side="left", padx=(0, 8))
        self.path_entry = ctk.CTkEntry(path_frame, width=280, font=self.app_fonts['small'], fg_color=self.app_colors['item_default'], border_width=1, border_color=self.app_colors['btn_secondary'], corner_radius=8, text_color=self.app_colors['text_primary'])
        self.path_entry.pack(side="left", padx=(0, 16))
        self.path_entry.insert(0, config_manager.download_path)
        self.path_entry.bind('<Return>', lambda e: self.manual_path_update())
        
        ctk.CTkButton(path_frame, text="浏览", width=64, height=32, font=self.app_fonts['body'], fg_color=self.app_colors['btn_secondary'], hover_color=self.app_colors['btn_secondary_hover'], text_color=self.app_colors['text_primary'], corner_radius=8, command=self.choose_download_path).pack(side="left")
        
        ctk.CTkButton(self.frame_a, text="日志", width=80, height=32, font=self.app_fonts['body'], fg_color=self.app_colors['btn_secondary'], text_color=self.app_colors['text_primary'], hover_color=self.app_colors['btn_secondary_hover'], corner_radius=8, command=self.open_log).grid(row=0, column=1, padx=8, pady=8)
        ctk.CTkButton(self.frame_a, text="设置", width=80, height=32, font=self.app_fonts['body_bold'], fg_color=self.app_colors['btn_primary'], text_color=self.app_colors['text_on_primary'], hover_color=self.app_colors['btn_primary_hover'], corner_radius=8, command=self.open_settings).grid(row=0, column=2, padx=(8, 16), pady=8)
        
        # --- Main Content ---
        # Left: Search
        self.search_panel = SearchPanel(self, self.app_colors, self.app_fonts)
        self.search_panel.grid(row=1, column=0, padx=(16, 8), pady=(8, 16), sticky="nsew")
        self.search_panel.configure(fg_color=self.app_colors['frame'], corner_radius=16)
        
        # Right: Queue
        right_container = ctk.CTkFrame(self, fg_color="transparent")
        right_container.grid(row=1, column=1, padx=(8, 16), pady=(8, 16), sticky="nsew")
        right_container.grid_rowconfigure(0, weight=1)
        right_container.grid_columnconfigure(0, weight=1)
        
        self.queue_panel = QueuePanel(right_container, self.app_colors, self.app_fonts)
        self.queue_panel.grid(row=0, column=0, sticky="nsew")
        self.queue_panel.configure(fg_color=self.app_colors['frame'], corner_radius=16)
        
    def bind_events(self):
        event_bus.subscribe("TOAST", self.on_toast)

    def on_toast(self, message, type="info"):
        self.after(0, lambda: show_toast(self, message, type))

    def on_focus_in(self, event):
        if event.widget == self:
            download_manager.sync_disk_state()

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
        if hasattr(self, 'settings_window') and self.settings_window is not None and self.settings_window.winfo_exists():
            self.settings_window.lift()
            self.settings_window.focus()
        else:
            from ui.views.settings_view import SettingsWindow
            self.settings_window = SettingsWindow(self)

    def run(self):
        self.mainloop()
