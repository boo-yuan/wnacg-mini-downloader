import os
import sys
import threading
import subprocess
import tkinter as tk

import customtkinter as ctk

from utils import logger, search_wnacg, download_thumbnail, delete_task_state, get_app_dir, get_resource_path
from download_manager import DownloadManager

def setup_autohide_scrollbar(ctk_scrollable_frame):
    def check_scrollbar():
        canvas = ctk_scrollable_frame._parent_canvas
        bbox = canvas.bbox("all")
        if not bbox: return
        
        content_height = bbox[3] - bbox[1]
        canvas_height = canvas.winfo_height()
        
        if content_height <= canvas_height + 2:
            if ctk_scrollable_frame._scrollbar.winfo_ismapped():
                ctk_scrollable_frame._scrollbar.grid_remove()
        else:
            if not ctk_scrollable_frame._scrollbar.winfo_ismapped():
                ctk_scrollable_frame._scrollbar.grid()

    def on_configure(*args):
        ctk_scrollable_frame.after(10, check_scrollbar)
                
    canvas = ctk_scrollable_frame._parent_canvas
    content_frame = ctk_scrollable_frame._parent_frame
    
    canvas.bind("<Configure>", on_configure, add="+")
    content_frame.bind("<Configure>", on_configure, add="+")
    
    ctk_scrollable_frame.after(100, check_scrollbar)

class SettingsWindow(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("全局设置")
        self.resizable(False, False)
        
        icon_path = get_resource_path('icon.ico')
        if os.path.exists(icon_path):
            try: self.after(200, lambda: self.iconbitmap(icon_path))
            except: pass
        self.attributes("-topmost", True)
        self.parent = parent
        self.configure(fg_color=self.parent.color_bg)
        
        # 1. API域名
        ctk.CTkLabel(self, text="API域名", font=("Microsoft YaHei", 16, "bold"), text_color=self.parent.color_text_primary).pack(pady=(15, 5), padx=20, anchor="w")
        self.api_mode_var = ctk.StringVar(value=parent.api_domain_mode)
        
        api_seg_frame = ctk.CTkFrame(self, fg_color="transparent")
        api_seg_frame.pack(fill="x", padx=30, pady=(0, 5))
        self.api_seg = ctk.CTkSegmentedButton(
            api_seg_frame, values=["默认", "自定义"], variable=self.api_mode_var, command=self.on_api_mode_change,
            fg_color=("#E5E5EA", "#1C1C1E"),
            selected_color=("#FFFFFF", "#636366"),
            selected_hover_color=("#FFFFFF", "#636366"),
            unselected_color=("#E5E5EA", "#1C1C1E"),
            unselected_hover_color=("#D1D1D6", "#2C2C2E"),
            text_color=self.parent.color_text_primary
        )
        self.api_seg.pack(side="left")
        
        self.api_custom_frame = ctk.CTkFrame(self, fg_color=self.parent.color_frame, border_width=0, corner_radius=10)
        self.api_custom_frame.pack(fill="x", padx=30, pady=(0, 10))
        
        ctk.CTkLabel(self.api_custom_frame, text="自定义API域名").pack(side="left", padx=10, pady=5)
        self.api_entry = ctk.CTkEntry(self.api_custom_frame, width=200, fg_color="transparent", border_width=0)
        self.api_entry.pack(side="left", padx=5, pady=5, fill="x", expand=True)
        self.api_entry.insert(0, parent.custom_api_domain)
        
        self.release_page_btn = ctk.CTkButton(self.api_custom_frame, text="打开发布页", width=80, fg_color=self.parent.color_item, text_color=self.parent.color_text_primary, hover_color=self.parent.color_item_selected, corner_radius=6, command=lambda: __import__('webbrowser').open("https://wnacg01.link"))
        self.release_page_btn.pack(side="right", padx=10, pady=5)
        
        def create_dual_ios_row(parent_frame, label1, val1, min1, max1, label2, val2, min2, max2):
            row = ctk.CTkFrame(parent_frame, fg_color="transparent")
            row.pack(fill="x", padx=15, pady=8)
            
            left_frame = ctk.CTkFrame(row, fg_color="transparent")
            left_frame.pack(side="left", fill="x", expand=True)
            
            lbl1 = ctk.CTkLabel(left_frame, text=label1, font=("Microsoft YaHei", 14), text_color=self.parent.color_text_primary)
            lbl1.pack(side="left")
            
            ctrl1 = ctk.CTkFrame(left_frame, fg_color=self.parent.color_item, corner_radius=8)
            ctrl1.pack(side="right", padx=(0, 10))
            
            entry1 = ctk.CTkEntry(ctrl1, width=35, fg_color="transparent", border_width=0, justify="center", font=("Microsoft YaHei", 14), text_color=self.parent.color_text_primary)
            entry1.insert(0, str(val1))
            
            def dec1():
                try:
                    v = int(entry1.get())
                    entry1.delete(0, 'end')
                    entry1.insert(0, str(max(min1, v-1)))
                except: pass
            def inc1():
                try:
                    v = int(entry1.get())
                    entry1.delete(0, 'end')
                    entry1.insert(0, str(min(max1, v+1)))
                except: pass
                
            btn_dec1 = ctk.CTkButton(ctrl1, text="－", width=26, height=26, fg_color="transparent", text_color=self.parent.color_text_primary, hover_color=self.parent.color_item_selected, command=dec1)
            btn_dec1.pack(side="left", padx=2)
            entry1.pack(side="left")
            btn_inc1 = ctk.CTkButton(ctrl1, text="＋", width=26, height=26, fg_color="transparent", text_color=self.parent.color_text_primary, hover_color=self.parent.color_item_selected, command=inc1)
            btn_inc1.pack(side="left", padx=2)
            
            right_frame = ctk.CTkFrame(row, fg_color="transparent")
            right_frame.pack(side="right", fill="x", expand=True)
            
            lbl2 = ctk.CTkLabel(right_frame, text=label2, font=("Microsoft YaHei", 14), text_color=self.parent.color_text_primary)
            lbl2.pack(side="left", padx=(10, 0))
            
            ctrl2 = ctk.CTkFrame(right_frame, fg_color=self.parent.color_item, corner_radius=8)
            ctrl2.pack(side="right")
            
            entry2 = ctk.CTkEntry(ctrl2, width=35, fg_color="transparent", border_width=0, justify="center", font=("Microsoft YaHei", 14), text_color=self.parent.color_text_primary)
            entry2.insert(0, str(val2))
            
            def dec2():
                try:
                    v = int(entry2.get())
                    entry2.delete(0, 'end')
                    entry2.insert(0, str(max(min2, v-1)))
                except: pass
            def inc2():
                try:
                    v = int(entry2.get())
                    entry2.delete(0, 'end')
                    entry2.insert(0, str(min(max2, v+1)))
                except: pass
                
            btn_dec2 = ctk.CTkButton(ctrl2, text="－", width=26, height=26, fg_color="transparent", text_color=self.parent.color_text_primary, hover_color=self.parent.color_item_selected, command=dec2)
            btn_dec2.pack(side="left", padx=2)
            entry2.pack(side="left")
            btn_inc2 = ctk.CTkButton(ctrl2, text="＋", width=26, height=26, fg_color="transparent", text_color=self.parent.color_text_primary, hover_color=self.parent.color_item_selected, command=inc2)
            btn_inc2.pack(side="left", padx=2)
            
            return entry1, entry2

        # 2. 下载速度
        ctk.CTkLabel(self, text="下载速度", font=("Microsoft YaHei", 16, "bold"), text_color=self.parent.color_text_primary).pack(pady=(15, 5), padx=20, anchor="w")
        
        speed_frame = ctk.CTkFrame(self, fg_color=self.parent.color_frame, corner_radius=10)
        speed_frame.pack(fill="x", padx=30, pady=(0, 5))
        
        self.entry_cc, self.entry_crt = create_dual_ios_row(speed_frame, "漫画并发", parent.concurrent_comics, 1, 10, "间隔(秒)", parent.comic_rest_time, 0, 60)
        
        sep1 = ctk.CTkFrame(speed_frame, height=1, fg_color=("#C6C6C8", "#38383A"))
        sep1.pack(fill="x", padx=(15, 0))
        
        self.entry_ci, self.entry_irt = create_dual_ios_row(speed_frame, "图片并发", parent.concurrent_images, 1, 50, "间隔(秒)", parent.image_rest_time, 0, 60)

        # 3. 代理类型
        ctk.CTkLabel(self, text="网络代理", font=("Microsoft YaHei", 16, "bold"), text_color=self.parent.color_text_primary).pack(pady=(15, 5), padx=20, anchor="w")
        self.proxy_mode_var = ctk.StringVar(value=parent.proxy_mode)
        
        proxy_seg_frame = ctk.CTkFrame(self, fg_color="transparent")
        proxy_seg_frame.pack(fill="x", padx=30, pady=(0, 5))
        self.proxy_seg = ctk.CTkSegmentedButton(
            proxy_seg_frame, values=["系统代理", "直连", "自定义"], variable=self.proxy_mode_var, command=self.on_proxy_mode_change,
            fg_color=("#E5E5EA", "#1C1C1E"),
            selected_color=("#FFFFFF", "#636366"),
            selected_hover_color=("#FFFFFF", "#636366"),
            unselected_color=("#E5E5EA", "#1C1C1E"),
            unselected_hover_color=("#D1D1D6", "#2C2C2E"),
            text_color=self.parent.color_text_primary
        )
        self.proxy_seg.pack(side="left")
        
        self.proxy_custom_frame = ctk.CTkFrame(self, fg_color=self.parent.color_frame, border_width=0, corner_radius=10)
        self.proxy_custom_frame.pack(fill="x", padx=30, pady=(0, 10))
        
        ctk.CTkLabel(self.proxy_custom_frame, text="http://").pack(side="left", padx=(10, 2), pady=5)
        self.proxy_ip_entry = ctk.CTkEntry(self.proxy_custom_frame, width=200, fg_color="transparent", border_width=0)
        self.proxy_ip_entry.pack(side="left", padx=5, pady=5, fill="x", expand=True)
        self.proxy_ip_entry.insert(0, parent.custom_proxy_ip)
        
        ctk.CTkLabel(self.proxy_custom_frame, text=":").pack(side="left", padx=2, pady=5)
        
        self.proxy_port_frame = ctk.CTkFrame(self.proxy_custom_frame, fg_color="transparent")
        self.proxy_port_frame.pack(side="left", padx=(5, 10), pady=5)
        self.proxy_port_entry = ctk.CTkEntry(self.proxy_port_frame, width=60, fg_color="transparent", border_width=1, border_color=("#CBD5E1", "#334155"))
        self.proxy_port_entry.grid(row=0, column=0, padx=(0,5))
        self.proxy_port_entry.insert(0, parent.custom_proxy_port)
        
        def dec_port():
            try:
                val = int(self.proxy_port_entry.get())
                self.proxy_port_entry.delete(0, 'end')
                self.proxy_port_entry.insert(0, str(max(1, val - 1)))
            except: pass
        def inc_port():
            try:
                val = int(self.proxy_port_entry.get())
                self.proxy_port_entry.delete(0, 'end')
                self.proxy_port_entry.insert(0, str(min(65535, val + 1)))
            except: pass

        btn_dec = ctk.CTkButton(self.proxy_port_frame, text="－", width=20, fg_color="transparent", text_color=("#0F172A", "#F1F5F9"), hover_color=("#CBD5E1", "#334155"), command=dec_port)
        btn_dec.grid(row=0, column=1)
        btn_inc = ctk.CTkButton(self.proxy_port_frame, text="＋", width=20, fg_color="transparent", text_color=("#0F172A", "#F1F5F9"), hover_color=("#CBD5E1", "#334155"), command=inc_port)
        btn_inc.grid(row=0, column=2)
        
        self.on_api_mode_change(parent.api_domain_mode)
        self.on_proxy_mode_change(parent.proxy_mode)
        
        # 2. 下载格式
        ctk.CTkLabel(self, text="下载格式", font=("Microsoft YaHei", 16, "bold"), text_color=("#0F172A", "#F1F5F9")).pack(pady=(15, 5), padx=20, anchor="w")
        self.format_var = ctk.StringVar(value=parent.download_format)
        format_frame = ctk.CTkFrame(self, fg_color="transparent")
        format_frame.pack(fill="x", padx=30)
        
        formats = ["jpg", "png", "webp", "原始格式"]
        for i, fmt in enumerate(formats):
            rb = ctk.CTkRadioButton(format_frame, text=fmt, variable=self.format_var, value=fmt, fg_color="#3B82F6", text_color=("#0F172A", "#F1F5F9"))
            rb.grid(row=0, column=i, padx=(0, 15), pady=5, sticky="w")
            
        # 3. 文件命名设置
        ctk.CTkLabel(self, text="文件命名", font=("Microsoft YaHei", 16, "bold"), text_color=self.parent.color_text_primary).pack(pady=(15, 5), padx=20, anchor="w")
        self.naming_var = ctk.BooleanVar(value=parent.use_original_filename)
        naming_frame = ctk.CTkFrame(self, fg_color="transparent")
        naming_frame.pack(fill="x", padx=30)
        cb_naming = ctk.CTkCheckBox(naming_frame, text="使用图片原文件名", variable=self.naming_var, fg_color=self.parent.color_accent, text_color=self.parent.color_text_primary)
        cb_naming.grid(row=0, column=0, pady=5, sticky="w")
        
        self.save_btn = ctk.CTkButton(self, text="保存全局设置", height=40, font=("Microsoft YaHei", 14, "bold"), fg_color=self.parent.color_accent, hover_color=self.parent.color_accent_hover, command=self.save_settings)
        self.save_btn.pack(pady=25)
        
    def on_api_mode_change(self, value):
        if value == "默认":
            for child in self.api_custom_frame.winfo_children():
                child.configure(state="disabled")
        else:
            for child in self.api_custom_frame.winfo_children():
                child.configure(state="normal")

    def on_proxy_mode_change(self, value):
        if value != "自定义":
            for child in self.proxy_custom_frame.winfo_children():
                if isinstance(child, ctk.CTkEntry):
                    child.configure(state="disabled")
            for child in self.proxy_port_frame.winfo_children():
                child.configure(state="disabled")
        else:
            for child in self.proxy_custom_frame.winfo_children():
                if isinstance(child, ctk.CTkEntry):
                    child.configure(state="normal")
            for child in self.proxy_port_frame.winfo_children():
                child.configure(state="normal")
            
    def save_settings(self):
        self.parent.api_domain_mode = self.api_mode_var.get()
        self.parent.custom_api_domain = self.api_entry.get().strip()
        self.parent.proxy_mode = self.proxy_mode_var.get()
        self.parent.custom_proxy_ip = self.proxy_ip_entry.get().strip()
        self.parent.custom_proxy_port = self.proxy_port_entry.get().strip()
        
        try: self.parent.concurrent_comics = int(self.entry_cc.get())
        except: pass
        try: self.parent.comic_rest_time = int(self.entry_crt.get())
        except: pass
        try: self.parent.concurrent_images = int(self.entry_ci.get())
        except: pass
        try: self.parent.image_rest_time = int(self.entry_irt.get())
        except: pass
        
        self.parent.download_format = self.format_var.get()
        self.parent.use_original_filename = self.naming_var.get()
        
        self.parent.save_config()
        if hasattr(self.parent, 'download_manager'):
            self.parent.download_manager.update_workers()
        self.destroy()

class ModernApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Wnacg Mini Downloader")
        self.geometry("850x950")
        self.minsize(800, 800)
        
        icon_path = get_resource_path('icon.ico')
        if os.path.exists(icon_path):
            try: self.iconbitmap(icon_path)
            except: pass
        
        self.color_bg = ("#F2F2F7", "#000000")
        self.color_frame = ("#FFFFFF", "#1C1C1E")
        self.color_item = ("#F2F2F7", "#2C2C2E")
        self.color_item_selected = ("#D1E8FF", "#1C3D66")
        self.color_text_primary = ("#000000", "#FFFFFF")
        self.color_text_secondary = ("#8E8E93", "#98989D")
        self.color_accent = ("#007AFF", "#0A84FF")
        self.color_accent_hover = ("#0051A8", "#0066CC")
        
        self.configure(fg_color=self.color_bg)
        
        self.api_domain_mode = "默认"
        self.custom_api_domain = "www.wn07.ru"
        self.proxy_mode = "系统代理"
        self.custom_proxy_ip = "127.0.0.1"
        self.custom_proxy_port = "7890"
        
        self.concurrent_comics = 2
        self.comic_rest_time = 0
        self.concurrent_images = 5
        self.image_rest_time = 1
        
        self.current_page = 1
        self.total_pages = 1
        self.current_query = ""
        self.is_searching = False
        
        base_dir = get_app_dir()
        self.download_path = os.path.join(base_dir, "download")
        if not os.path.exists(self.download_path):
            os.makedirs(self.download_path, exist_ok=True)
        self.config_file = os.path.join(base_dir, "config.json")
        self.download_format = "jpg"
        self.use_original_filename = True
        self.load_config()
        
        self.selected_task_ids = set()
        self.last_clicked_task_id = None
        
        self.current_search_items = {}
        self.selected_search_ids = set()
        self.last_clicked_search_id = None
        self.search_drag_start_selected = set()
        
        self.download_manager = DownloadManager(self)
        
        self.setup_ui()
        self.bind("<Control-a>", lambda e: self.select_all_tasks())
        self.bind("<Control-A>", lambda e: self.select_all_tasks())
        self.bind("<FocusIn>", self.on_focus_in)
        
        self.download_manager.sync_disk_state()
        self._start_disk_status_watcher()
        
    def _start_disk_status_watcher(self):
        def watcher_loop():
            import re
            import os
            import time
            import threading
            while True:
                time.sleep(2)
                if getattr(self, 'is_searching', False): continue
                if not hasattr(self, 'current_search_items'): continue
                
                try:
                    for aid, info in list(self.current_search_items.items()):
                        btn = info.get('list_btn')
                        if not btn or not btn.winfo_exists(): continue
                        
                        item = info['data']
                        task_id = f"task_{aid}"
                        
                        if task_id in self.download_manager.tasks:
                            info['last_disk_exists'] = None
                            continue
                            
                        base_title = re.sub(r'[\\/*?:"<>|]', '_', item['title']).strip()
                        if base_title.startswith("[未完成]_"):
                            base_title = base_title[len("[未完成]_"):]
                        completed_dir = os.path.join(self.download_path, base_title)
                        
                        exists = os.path.exists(completed_dir)
                        last_exists = info.get('last_disk_exists')
                        
                        if exists != last_exists:
                            info['last_disk_exists'] = exists
                            if exists:
                                self.download_manager.update_list_button_state(btn, "下载完成")
                            else:
                                self.download_manager.update_list_button_state(btn, "一键下载")
                                self.after(0, lambda b=btn, t=task_id, i=item, p=info['proxies']: b.configure(command=lambda inner_b=b: self.trigger_download(t, i, inner_b, p)))
                except Exception:
                    pass
                    
        import threading
        threading.Thread(target=watcher_loop, daemon=True).start()

    def on_focus_in(self, event):
        if event.widget == self:
            if hasattr(self, 'download_manager'):
                self.download_manager.sync_disk_state()

    def load_config(self):
        try:
            if os.path.exists(self.config_file):
                import json
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    if 'api_domain_mode' in config:
                        self.api_domain_mode = config['api_domain_mode']
                    if 'custom_api_domain' in config:
                        self.custom_api_domain = config['custom_api_domain']
                    if 'proxy_mode' in config:
                        self.proxy_mode = config['proxy_mode']
                    else:
                        if config.get('use_system_proxy', True):
                            self.proxy_mode = "系统代理"
                        elif config.get('custom_proxy_url'):
                            self.proxy_mode = "自定义"
                            import re
                            m = re.search(r'//([^:]+):(\d+)', config['custom_proxy_url'])
                            if m:
                                self.custom_proxy_ip = m.group(1)
                                self.custom_proxy_port = m.group(2)
                    if 'custom_proxy_ip' in config:
                        self.custom_proxy_ip = config['custom_proxy_ip']
                    if 'custom_proxy_port' in config:
                        self.custom_proxy_port = str(config['custom_proxy_port'])
                        
                    if 'concurrent_comics' in config: self.concurrent_comics = config['concurrent_comics']
                    if 'comic_rest_time' in config: self.comic_rest_time = config['comic_rest_time']
                    if 'concurrent_images' in config: self.concurrent_images = config['concurrent_images']
                    if 'image_rest_time' in config: self.image_rest_time = config['image_rest_time']

                    if 'download_path' in config and os.path.isdir(config['download_path']):
                        self.download_path = config['download_path']
                    if 'download_format' in config:
                        self.download_format = config['download_format']
                    if 'use_original_filename' in config:
                        self.use_original_filename = config['use_original_filename']
        except Exception as e:
            from utils import logger
            logger.error(f"Error loading config: {e}")

    def save_config(self):
        try:
            import json
            config = {
                'api_domain_mode': self.api_domain_mode,
                'custom_api_domain': self.custom_api_domain,
                'proxy_mode': self.proxy_mode,
                'custom_proxy_ip': self.custom_proxy_ip,
                'custom_proxy_port': self.custom_proxy_port,
                'concurrent_comics': self.concurrent_comics,
                'comic_rest_time': self.comic_rest_time,
                'concurrent_images': self.concurrent_images,
                'image_rest_time': self.image_rest_time,
                'download_path': self.download_path,
                'download_format': self.download_format,
                'use_original_filename': self.use_original_filename
            }
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            from utils import logger
            logger.error(f"Error saving config: {e}")

    def choose_download_path(self):
        import tkinter.filedialog as fd
        path = fd.askdirectory(initialdir=self.download_path, title="选择下载保存路径")
        if path:
            path = os.path.normpath(path)
            self.path_entry.delete(0, 'end')
            self.path_entry.insert(0, path)
            self.manual_path_update()

    def manual_path_update(self):
        new_path = self.path_entry.get().strip()
        if os.path.isdir(new_path):
            self.download_path = os.path.normpath(new_path)
            self.save_config()
            
            for widget in self.queue_frame.winfo_children():
                widget.destroy()
            self.download_manager.tasks.clear()
            self.selected_task_ids.clear()
            
            for item_id, info in self.current_search_items.items():
                if info['list_btn'] and info['list_btn'].winfo_exists():
                    self.download_manager.update_list_button_state(info['list_btn'], "一键下载")
                    info['list_btn'].configure(command=lambda b=info['list_btn'], tid=f"task_{item_id}", itm=info['data'], p=info['proxies']: self.trigger_download(tid, itm, b, p))
                    
            self.download_manager.sync_disk_state()
        else:
            self.path_entry.delete(0, 'end')
            self.path_entry.insert(0, self.download_path)
            
    def setup_ui(self):
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=3)
        self.grid_columnconfigure(1, weight=2)
        
        self.frame_a = ctk.CTkFrame(self, corner_radius=12, fg_color=self.color_frame)
        self.frame_a.grid(row=0, column=0, columnspan=2, padx=15, pady=(15, 5), sticky="nsew")
        self.frame_a.grid_columnconfigure(0, weight=1)
        
        path_frame = ctk.CTkFrame(self.frame_a, fg_color="transparent")
        path_frame.grid(row=0, column=0, padx=25, pady=15, sticky="w")
        
        ctk.CTkLabel(path_frame, text="下载路径:", font=("Microsoft YaHei", 14, "bold"), text_color=self.color_text_primary).pack(side="left", padx=(0, 10))
        self.path_entry = ctk.CTkEntry(path_frame, width=280, fg_color=self.color_item, border_width=0, corner_radius=6, text_color=self.color_text_primary)
        self.path_entry.pack(side="left", padx=(0, 10))
        self.path_entry.insert(0, self.download_path)
        self.path_entry.bind('<Return>', lambda e: self.manual_path_update())
        
        ctk.CTkButton(path_frame, text="浏览...", width=60, font=("Microsoft YaHei", 12), fg_color=self.color_item, hover_color=self.color_item_selected, text_color=self.color_text_primary, corner_radius=6, command=self.choose_download_path).pack(side="left")
        
        ctk.CTkButton(self.frame_a, text="查看日志", width=90, fg_color=self.color_item, text_color=self.color_text_primary, hover_color=self.color_item_selected, corner_radius=6, command=self.open_log).grid(row=0, column=1, padx=5, pady=15)
        ctk.CTkButton(self.frame_a, text="全局设置", width=90, fg_color=self.color_accent, hover_color=self.color_accent_hover, corner_radius=6, command=self.open_settings).grid(row=0, column=2, padx=20, pady=15)

        self.frame_b = ctk.CTkFrame(self, corner_radius=12, fg_color=self.color_frame)
        self.frame_b.grid(row=1, column=0, padx=(15, 5), pady=(5, 15), sticky="nsew")
        self.frame_b.grid_rowconfigure(2, weight=1)
        self.frame_b.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(self.frame_b, text="资源探索", font=("Microsoft YaHei", 18, "bold"), text_color=self.color_text_primary).grid(row=0, column=0, pady=(15, 0), padx=20, sticky="w")
        
        search_frame = ctk.CTkFrame(self.frame_b, fg_color="transparent")
        search_frame.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        search_frame.grid_columnconfigure(0, weight=1)
        search_frame.grid_columnconfigure(1, weight=0)
        search_frame.grid_columnconfigure(2, weight=0)
        search_frame.grid_columnconfigure(3, weight=0)
        
        self.search_entry = ctk.CTkEntry(search_frame, placeholder_text="输入关键字开始搜索...", height=40, font=("Microsoft YaHei", 14), fg_color=self.color_item, border_width=0, corner_radius=8, text_color=self.color_text_primary)
        self.search_entry.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        self.search_entry.bind('<Return>', lambda e: self.start_search(1))
        
        self.paste_btn = ctk.CTkButton(search_frame, text="📋", width=30, height=40, font=("Arial", 16), fg_color=self.color_item, text_color=self.color_text_secondary, hover_color=self.color_item_selected, corner_radius=8, command=self._quick_paste)
        self.paste_btn.grid(row=0, column=1, padx=(0, 5))
        
        self.clear_btn = ctk.CTkButton(search_frame, text="✕", width=30, height=40, font=("Arial", 16), fg_color=self.color_item, text_color=self.color_text_secondary, hover_color=self.color_item_selected, corner_radius=8, command=lambda: self.search_entry.delete(0, 'end'))
        self.clear_btn.grid(row=0, column=2, padx=(0, 10))
        
        self.search_btn = ctk.CTkButton(search_frame, text="搜索", width=80, height=40, font=("Microsoft YaHei", 14, "bold"), fg_color=self.color_accent, hover_color=self.color_accent_hover, corner_radius=8, command=lambda: self.start_search(1))
        self.search_btn.grid(row=0, column=3)
        
        self.list_frame = ctk.CTkScrollableFrame(self.frame_b, corner_radius=8, fg_color="transparent", bg_color="transparent")
        self.list_frame.grid(row=2, column=0, padx=10, pady=0, sticky="nsew")
        
        if hasattr(self.list_frame, '_parent_canvas'):
            self.list_frame._parent_canvas.bind("<Button-1>", self.on_search_empty_click)
            self.list_frame._parent_canvas.bind("<B1-Motion>", self.on_search_drag_motion)
            
        setup_autohide_scrollbar(self.list_frame)
            
        self.pagination_frame = ctk.CTkFrame(self.frame_b, fg_color="transparent", height=40)
        self.pagination_frame.grid(row=3, column=0, pady=(5, 10))
        self.update_pagination()
        
        self.frame_c = ctk.CTkFrame(self, corner_radius=12, fg_color=self.color_frame)
        self.frame_c.grid(row=1, column=1, padx=(5, 15), pady=(5, 15), sticky="nsew")
        self.frame_c.grid_rowconfigure(1, weight=1)
        self.frame_c.grid_columnconfigure(0, weight=1)
        
        header_frame_c = ctk.CTkFrame(self.frame_c, fg_color="transparent")
        header_frame_c.grid(row=0, column=0, pady=(15, 5), padx=20, sticky="ew")
        header_frame_c.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(header_frame_c, text="任务队列", font=("Microsoft YaHei", 18, "bold"), text_color=self.color_text_primary).grid(row=0, column=0, sticky="w")
        
        self.queue_frame = ctk.CTkScrollableFrame(self.frame_c, corner_radius=8, fg_color="transparent", bg_color="transparent")
        self.queue_frame.grid(row=1, column=0, padx=5, pady=(0, 10), sticky="nsew")
        
        if hasattr(self.queue_frame, '_parent_canvas'):
            self.queue_frame._parent_canvas.bind("<Button-1>", self.on_empty_click)
            self.queue_frame._parent_canvas.bind("<Button-3>", self.on_empty_right_click)
            self.queue_frame._parent_canvas.bind("<B1-Motion>", self.on_drag_motion)
            
        setup_autohide_scrollbar(self.queue_frame)

    def _quick_paste(self):
        try:
            text = self.clipboard_get()
            self.search_entry.delete(0, 'end')
            self.search_entry.insert(0, text)
        except Exception:
            pass

    # ---------------- Search List Drag Selection Logic ----------------
    def on_search_empty_click(self, event):
        self.search_drag_start_y = event.y_root
        is_ctrl = (event.state & 0x0004) != 0
        if not is_ctrl:
            self.selected_search_ids.clear()
            self.last_clicked_search_id = None
        self.search_drag_start_selected = set(self.selected_search_ids)
        self.update_search_selection_ui()

    def _bind_search_click_recursive(self, widget, aid):
        widget.bind("<Button-1>", lambda e: self.on_search_click(e, aid))
        widget.bind("<B1-Motion>", self.on_search_drag_motion)
        widget.bind("<Button-3>", lambda e: self.on_search_right_click(e, aid))
        for child in widget.winfo_children():
            self._bind_search_click_recursive(child, aid)

    def on_search_click(self, event, aid):
        self.search_drag_start_y = event.y_root
        is_ctrl = (event.state & 0x0004) != 0
        is_shift = (event.state & 0x0001) != 0
        
        all_ids = list(self.current_search_items.keys())
        
        if is_ctrl:
            if aid in self.selected_search_ids:
                self.selected_search_ids.remove(aid)
            else:
                self.selected_search_ids.add(aid)
            self.last_clicked_search_id = aid
        elif is_shift and self.last_clicked_search_id in all_ids:
            try:
                start_idx = all_ids.index(self.last_clicked_search_id)
                end_idx = all_ids.index(aid)
                if start_idx > end_idx:
                    start_idx, end_idx = end_idx, start_idx
                self.selected_search_ids = set(all_ids[start_idx:end_idx+1])
            except ValueError:
                self.selected_search_ids = {aid}
                self.last_clicked_search_id = aid
        else:
            self.selected_search_ids = {aid}
            self.last_clicked_search_id = aid
            
        self.search_drag_start_selected = set(self.selected_search_ids)
        self.update_search_selection_ui()

    def on_search_drag_motion(self, event):
        if not hasattr(self, 'search_drag_start_y'): return
        
        y1 = min(self.search_drag_start_y, event.y_root)
        y2 = max(self.search_drag_start_y, event.y_root)
        
        is_ctrl = (event.state & 0x0004) != 0
        new_selection = set(self.search_drag_start_selected) if is_ctrl else set()
        
        for aid, item_info in self.current_search_items.items():
            frame = item_info['ui_frame']
            if not frame or not frame.winfo_exists(): continue
            fy = frame.winfo_rooty()
            fh = frame.winfo_height()
            
            if (fy + fh >= y1) and (fy <= y2):
                new_selection.add(aid)
            elif not is_ctrl and aid in new_selection:
                new_selection.discard(aid)
                
        if new_selection != self.selected_search_ids:
            self.selected_search_ids = new_selection
            self.update_search_selection_ui()

    def update_search_selection_ui(self):
        for aid, item_info in self.current_search_items.items():
            frame = item_info['ui_frame']
            if not frame or not frame.winfo_exists(): continue
            if aid in self.selected_search_ids:
                frame.configure(fg_color=self.color_item_selected, border_color=self.color_accent)
            else:
                frame.configure(fg_color=self.color_item, border_color=self.color_bg)

    def clear_search_selection(self):
        self.selected_search_ids.clear()
        self.last_clicked_search_id = None
        self.update_search_selection_ui()

    def on_search_right_click(self, event, aid):
        if aid not in self.selected_search_ids:
            self.selected_search_ids = {aid}
            self.last_clicked_search_id = aid
            self.update_search_selection_ui()
            
        menu = tk.Menu(self, tearoff=0, font=("Microsoft YaHei", 12))
        menu.add_command(label="全选列表", command=self.select_all_search)
        menu.add_command(label="取消选中", command=self.clear_search_selection)
        menu.add_separator()
        menu.add_command(label="批量加入任务队列", command=self.batch_add_to_queue)
        
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def select_all_search(self):
        self.selected_search_ids = set(self.current_search_items.keys())
        self.update_search_selection_ui()
        
    def batch_add_to_queue(self):
        for aid in list(self.selected_search_ids):
            item_info = self.current_search_items.get(aid)
            if item_info:
                task_id = f"task_{aid}"
                self.trigger_download(task_id, item_info['data'], item_info['list_btn'], item_info['proxies'])
        self.selected_search_ids.clear()
        self.update_search_selection_ui()
    # -------------------------------------------------------------

    def on_empty_click(self, event):
        self.drag_start_y = event.y_root
        
        is_ctrl = (event.state & 0x0004) != 0
        if not is_ctrl:
            self.selected_task_ids.clear()
            self.last_clicked_task_id = None
            
        self.drag_start_selected = set(self.selected_task_ids)
        self.update_task_selection_ui()

    def _bind_click_recursive(self, widget, task_id):
        widget.bind("<Button-1>", lambda e: self.on_task_click(e, task_id))
        widget.bind("<B1-Motion>", self.on_drag_motion)
        widget.bind("<Button-3>", lambda e: self.on_task_right_click(e, task_id))
        for child in widget.winfo_children():
            self._bind_click_recursive(child, task_id)

    def add_task_to_ui(self, task_data):
        item_frame = ctk.CTkFrame(self.queue_frame, corner_radius=8, fg_color=self.color_item, border_width=0)
        item_frame.pack(fill="x", padx=2, pady=2)
        item_frame.grid_columnconfigure(0, weight=1)
        
        lbl_title = ctk.CTkLabel(item_frame, text=task_data['title'], font=("Microsoft YaHei", 12, "bold"), text_color=self.color_text_primary, anchor="w", justify="left")
        lbl_title.grid(row=0, column=0, padx=10, pady=(5, 0), sticky="nw")
        
        lbl_status = ctk.CTkLabel(item_frame, text=task_data['status'], font=("Microsoft YaHei", 11), text_color=self.color_text_secondary, anchor="w")
        lbl_status.grid(row=1, column=0, padx=10, pady=0, sticky="nw")
        
        progressbar = ctk.CTkProgressBar(item_frame, progress_color=self.color_accent, fg_color=self.color_bg, height=6)
        progressbar.grid(row=2, column=0, padx=10, pady=(2, 5), sticky="ew")
        progressbar.set(task_data.get('progress', 0.0))
        
        task_data['ui_frame'] = item_frame
        task_data['ui_lbl_status'] = lbl_status
        task_data['ui_progressbar'] = progressbar
        
        self._bind_click_recursive(item_frame, task_data['id'])
        
        # Trigger layout check for scrollbar
        self.queue_frame._parent_canvas.after(100, lambda: self.queue_frame._parent_canvas.event_generate("<Configure>"))

    def on_task_click(self, event, task_id):
        self.drag_start_y = event.y_root
        
        is_ctrl = (event.state & 0x0004) != 0
        is_shift = (event.state & 0x0001) != 0
        
        all_ids = [t_id for t_id, t in list(self.download_manager.tasks.items()) if t['ui_frame'] and t['ui_frame'].winfo_exists()]
        
        if is_ctrl:
            if task_id in self.selected_task_ids:
                self.selected_task_ids.remove(task_id)
            else:
                self.selected_task_ids.add(task_id)
            self.last_clicked_task_id = task_id
        elif is_shift and self.last_clicked_task_id in all_ids:
            try:
                start_idx = all_ids.index(self.last_clicked_task_id)
                end_idx = all_ids.index(task_id)
                if start_idx > end_idx:
                    start_idx, end_idx = end_idx, start_idx
                self.selected_task_ids = set(all_ids[start_idx:end_idx+1])
            except ValueError:
                self.selected_task_ids = {task_id}
                self.last_clicked_task_id = task_id
        else:
            self.selected_task_ids = {task_id}
            self.last_clicked_task_id = task_id
            
        self.drag_start_selected = set(self.selected_task_ids)
        self.update_task_selection_ui()

    def on_drag_motion(self, event):
        if not hasattr(self, 'drag_start_y'): return
        
        y1 = min(self.drag_start_y, event.y_root)
        y2 = max(self.drag_start_y, event.y_root)
        
        is_ctrl = (event.state & 0x0004) != 0
        new_selection = set(self.drag_start_selected) if is_ctrl else set()
        
        for t_id, task in list(self.download_manager.tasks.items()):
            frame = task['ui_frame']
            if not frame or not frame.winfo_exists(): continue
            fy = frame.winfo_rooty()
            fh = frame.winfo_height()
            
            if (fy + fh >= y1) and (fy <= y2):
                new_selection.add(t_id)
            elif not is_ctrl and t_id in new_selection:
                new_selection.discard(t_id)
                
        if new_selection != self.selected_task_ids:
            self.selected_task_ids = new_selection
            self.update_task_selection_ui()

    def clear_task_selection(self):
        self.selected_task_ids.clear()
        self.last_clicked_task_id = None
        self.update_task_selection_ui()

    def on_empty_right_click(self, event):
        self.clear_task_selection()
        self.on_task_right_click(event, None)

    def on_task_right_click(self, event, task_id):
        if task_id is not None and task_id not in self.selected_task_ids:
            self.selected_task_ids = {task_id}
            self.last_clicked_task_id = task_id
            self.update_task_selection_ui()
            
        menu = tk.Menu(self, tearoff=0, font=("Microsoft YaHei", 12))
        menu.add_command(label="全选队列", command=self.select_all_tasks)
        menu.add_command(label="取消选中", command=self.clear_task_selection)
        menu.add_separator()
        menu.add_command(label="继续下载", command=self.resume_selected_tasks)
        menu.add_command(label="暂停下载", command=self.pause_selected_tasks)
        menu.add_separator()
        menu.add_command(label="取消并移除", command=self.cancel_selected_tasks)
        
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def update_task_selection_ui(self):
        for t_id, task in list(self.download_manager.tasks.items()):
            frame = task['ui_frame']
            if not frame or not frame.winfo_exists(): continue
            if t_id in self.selected_task_ids:
                frame.configure(fg_color=self.color_item_selected, border_color=self.color_accent)
            else:
                frame.configure(fg_color=self.color_item, border_color=self.color_bg)

    def select_all_tasks(self):
        self.selected_task_ids = {t_id for t_id, t in list(self.download_manager.tasks.items()) if t['ui_frame'] and t['ui_frame'].winfo_exists()}
        self.update_task_selection_ui()
        
    def pause_selected_tasks(self):
        for t_id in self.selected_task_ids:
            task = self.download_manager.tasks.get(t_id)
            if task and task['status'] not in ['下载完成', '已暂停', '已暂停 (启动缓存)']:
                task['cancel_flag'] = True
                task['is_paused'] = True
                self.download_manager.update_task_ui(t_id, "已暂停", task['progress'])
                self.download_manager.update_list_button_state(task['list_btn'], "继续下载")

    def resume_selected_tasks(self):
        for t_id in self.selected_task_ids:
            task = self.download_manager.tasks.get(t_id)
            if task and task['is_paused']:
                task['cancel_flag'] = False
                task['is_paused'] = False
                self.download_manager.update_task_ui(t_id, "等待中", task['progress'])
                self.download_manager.update_list_button_state(task['list_btn'], "等待中")
                self.download_manager.queue.put(t_id)

    def cancel_selected_tasks(self):
        for t_id in list(self.selected_task_ids):
            task = self.download_manager.tasks.get(t_id)
            if task:
                task['cancel_flag'] = True
                if task['ui_frame'] and task['ui_frame'].winfo_exists():
                    task['ui_frame'].destroy()
                self.download_manager.update_list_button_state(task['list_btn'], "一键下载")
                
                threading.Thread(target=delete_task_state, args=(task,), daemon=True).start()
                del self.download_manager.tasks[t_id]
        self.selected_task_ids.clear()
        
        # Trigger layout check for scrollbar
        self.queue_frame._parent_canvas.after(100, lambda: self.queue_frame._parent_canvas.event_generate("<Configure>"))

    def remove_task(self, task_id):
        task = self.download_manager.tasks.get(task_id)
        if not task: return
        
        if task['ui_frame'] and task['ui_frame'].winfo_exists():
            task['ui_frame'].destroy()
            
        if task['list_btn'] and task['list_btn'].winfo_exists():
            self.download_manager.update_list_button_state(task['list_btn'], "下载完成")
            
        if task_id in self.selected_task_ids:
            self.selected_task_ids.remove(task_id)
            self.update_task_selection_ui()
            
        if task_id in self.download_manager.tasks:
            del self.download_manager.tasks[task_id]
            
        # Trigger layout check for scrollbar
        self.queue_frame._parent_canvas.after(100, lambda: self.queue_frame._parent_canvas.event_generate("<Configure>"))

    def open_log(self):
        try:
            import platform
            from utils import LOG_FILE
            if platform.system() == 'Windows':
                os.startfile(LOG_FILE)
            elif sys.platform == "darwin":
                subprocess.call(["open", LOG_FILE])
            else:
                subprocess.call(["xdg-open", LOG_FILE])
        except Exception as e:
            logger.error(f"Cannot open log file: {e}")
            
    def open_settings(self):
        SettingsWindow(self)
        
    def start_search(self, page=1):
        query = self.search_entry.get().strip()
        if not query: return
        
        self.download_manager.sync_disk_state()
        
        self.current_query = query
        self.current_page = page
        self.is_searching = True
        self.search_btn.configure(text="加载中...", state="disabled")
        
        for widget in self.list_frame.winfo_children():
            widget.destroy()
            
        ctk.CTkLabel(self.list_frame, text="正在连接服务器...", font=("Microsoft YaHei", 14), text_color=self.color_text_secondary).pack(pady=40)
        
        threading.Thread(target=self._search_thread, args=(query, page), daemon=True).start()
        
    def _search_thread(self, query, page):
        from utils import get_proxies, search_wnacg
        proxies = get_proxies(self.proxy_mode, self.custom_proxy_ip, self.custom_proxy_port)
        
        api_domain = None
        if self.api_domain_mode == "自定义" and self.custom_api_domain:
            api_domain = self.custom_api_domain if self.custom_api_domain.startswith("http") else "https://" + self.custom_api_domain
            
        results, total_pages, err = search_wnacg(query, page, proxies, api_domain)
        self.after(0, self.update_list_ui, results, total_pages, err, proxies)
        
    def update_list_ui(self, results, total_pages, err, proxies):
        self.is_searching = False
        self.search_btn.configure(text="搜索", state="normal")
        self.total_pages = total_pages
        
        self.current_search_items.clear()
        self.selected_search_ids.clear()
        self.last_clicked_search_id = None
        
        for widget in self.list_frame.winfo_children():
            widget.destroy()
            
        if err:
            ctk.CTkLabel(self.list_frame, text=err, text_color="#EF4444").pack(pady=40)
            return
            
        if not results:
            ctk.CTkLabel(self.list_frame, text="未找到相关资源", font=("Microsoft YaHei", 14), text_color=self.color_text_secondary).pack(pady=40)
            self.update_pagination()
            return
            
        for index, item in enumerate(results):
            self.create_list_item(item, proxies)
            
        self.update_pagination()
        
        self.list_frame._parent_canvas.after(100, lambda: self.list_frame._parent_canvas.event_generate("<Configure>"))
        
    def create_list_item(self, item, proxies):
        item_frame = ctk.CTkFrame(self.list_frame, corner_radius=10, fg_color=self.color_item, border_width=0)
        item_frame.pack(fill="x", padx=2, pady=3)
        item_frame.grid_columnconfigure(1, weight=1)
        item_frame.grid_rowconfigure(2, weight=1)
        
        img_label = ctk.CTkLabel(item_frame, text="Loading", width=55, height=75, fg_color=self.color_frame, text_color=self.color_text_secondary, corner_radius=4)
        img_label.grid(row=0, column=0, rowspan=3, padx=(8, 10), pady=8)
        
        if item['img_url']:
            threading.Thread(target=self._load_image_thread, args=(item['img_url'], img_label, proxies), daemon=True).start()
            
        title_label = ctk.CTkLabel(item_frame, text=item['title'], font=("Microsoft YaHei", 13, "bold"), text_color=self.color_text_primary, anchor="w", justify="left", wraplength=320)
        title_label.grid(row=0, column=1, padx=2, pady=(8, 0), sticky="nw")
        
        count_label = ctk.CTkLabel(item_frame, text=item['count'], font=("Microsoft YaHei", 12), text_color=self.color_text_secondary, anchor="w")
        count_label.grid(row=1, column=1, padx=2, pady=0, sticky="nw")
        
        btn = ctk.CTkButton(item_frame, text="一键下载", font=("Microsoft YaHei", 12, "bold"), fg_color=self.color_accent, hover_color=self.color_accent_hover, text_color="#FFFFFF", width=70, height=26, corner_radius=6)
        btn.grid(row=2, column=1, padx=10, pady=(2, 8), sticky="se")
        
        if not item['aid']:
            btn.configure(state="disabled", text="无法解析AID")
        else:
            task_id = f"task_{item['aid']}"
            if task_id in self.download_manager.tasks:
                status = self.download_manager.tasks[task_id]['status']
                if "等待中" in status:
                    self.download_manager.update_list_button_state(btn, "等待中")
                elif "下载中" in status or "准备" in status or "解析" in status:
                    self.download_manager.update_list_button_state(btn, "下载中")
                elif "完成" in status:
                    self.download_manager.update_list_button_state(btn, "下载完成")
                else:
                    self.download_manager.update_list_button_state(btn, "继续下载")
                    btn.configure(command=lambda b=btn: self.trigger_download(task_id, item, b, proxies))
                
                self.download_manager.tasks[task_id]['list_btn'] = btn
            else:
                btn.configure(command=lambda b=btn: self.trigger_download(task_id, item, b, proxies))

            self.current_search_items[item['aid']] = {
                'data': item,
                'ui_frame': item_frame,
                'proxies': proxies,
                'list_btn': btn
            }
            self._bind_search_click_recursive(item_frame, item['aid'])

    def trigger_download(self, task_id, item, btn, proxies):
        self.download_manager.add_task(task_id, item['aid'], item['title'], item['domain'], btn, proxies)
            
    def _load_image_thread(self, url, label, proxies):
        image = download_thumbnail(url, proxies)
        if image:
            ctk_img = ctk.CTkImage(light_image=image, dark_image=image, size=(55, 75))
            self.after(0, lambda: label.configure(image=ctk_img, text=""))
        else:
            self.after(0, lambda: label.configure(text="Failed"))

    def update_pagination(self):
        for widget in self.pagination_frame.winfo_children():
            widget.destroy()
            
        if self.current_query and self.total_pages > 0:
            prev_btn = ctk.CTkButton(self.pagination_frame, text="◀", width=36, height=28, font=("Arial", 14, "bold"),
                                     fg_color=self.color_item, text_color=self.color_text_primary, hover_color=self.color_bg,
                                     command=lambda: self.start_search(max(1, self.current_page - 1)),
                                     state="normal" if self.current_page > 1 else "disabled")
            prev_btn.pack(side="left", padx=3)
            
            start_page = max(1, self.current_page - 2)
            end_page = min(self.total_pages, self.current_page + 2)
            
            if start_page > 1:
                p_first = ctk.CTkButton(self.pagination_frame, text="1", width=36, height=28, font=("Arial", 13),
                                       fg_color=self.color_item, text_color=self.color_text_primary, hover_color=self.color_bg,
                                       command=lambda: self.start_search(1))
                p_first.pack(side="left", padx=2)
                if start_page > 2:
                    ctk.CTkLabel(self.pagination_frame, text="...", font=("Arial", 13), text_color=self.color_text_secondary).pack(side="left", padx=2)
            
            for p in range(start_page, end_page + 1):
                if p == self.current_page:
                    p_btn = ctk.CTkButton(self.pagination_frame, text=str(p), width=36, height=28, font=("Arial", 13, "bold"),
                                          fg_color=self.color_accent, text_color="#FFFFFF", hover_color=self.color_accent_hover)
                else:
                    p_btn = ctk.CTkButton(self.pagination_frame, text=str(p), width=36, height=28, font=("Arial", 13),
                                          fg_color=self.color_item, text_color=self.color_text_primary, hover_color=self.color_bg,
                                          command=lambda p=p: self.start_search(p))
                p_btn.pack(side="left", padx=2)
                
            if end_page < self.total_pages:
                if end_page < self.total_pages - 1:
                    ctk.CTkLabel(self.pagination_frame, text="...", font=("Arial", 13), text_color=self.color_text_secondary).pack(side="left", padx=2)
                p_last = ctk.CTkButton(self.pagination_frame, text=str(self.total_pages), width=36, height=28, font=("Arial", 13),
                                       fg_color=self.color_item, text_color=self.color_text_primary, hover_color=self.color_bg,
                                       command=lambda: self.start_search(self.total_pages))
                p_last.pack(side="left", padx=2)
            
            next_btn = ctk.CTkButton(self.pagination_frame, text="▶", width=36, height=28, font=("Arial", 14, "bold"),
                                     fg_color=self.color_item, text_color=self.color_text_primary, hover_color=self.color_bg,
                                     command=lambda: self.start_search(min(self.total_pages, self.current_page + 1)),
                                     state="normal" if self.current_page < self.total_pages else "disabled")
            next_btn.pack(side="left", padx=3)
