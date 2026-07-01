import os
import customtkinter as ctk
from core.config_manager import config_manager
from core.logger import get_app_dir

def get_resource_path(relative_path):
    import sys
    import os
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(base_path, relative_path)

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
        self.api_mode_var = ctk.StringVar(value=config_manager.api_domain_mode)
        
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
        self.api_entry.insert(0, config_manager.custom_api_domain)
        
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
        
        self.entry_cc, self.entry_crt = create_dual_ios_row(speed_frame, "漫画并发", config_manager.concurrent_comics, 1, 10, "间隔(秒)", config_manager.comic_rest_time, 0, 60)
        
        sep1 = ctk.CTkFrame(speed_frame, height=1, fg_color=("#C6C6C8", "#38383A"))
        sep1.pack(fill="x", padx=(15, 0))
        
        self.entry_ci, self.entry_irt = create_dual_ios_row(speed_frame, "图片并发", config_manager.concurrent_images, 1, 50, "间隔(秒)", config_manager.image_rest_time, 0, 60)

        # 3. 代理类型
        ctk.CTkLabel(self, text="网络代理", font=("Microsoft YaHei", 16, "bold"), text_color=self.parent.color_text_primary).pack(pady=(15, 5), padx=20, anchor="w")
        self.proxy_mode_var = ctk.StringVar(value=config_manager.proxy_mode)
        
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
        self.proxy_ip_entry.insert(0, config_manager.custom_proxy_ip)
        
        ctk.CTkLabel(self.proxy_custom_frame, text=":").pack(side="left", padx=2, pady=5)
        
        self.proxy_port_frame = ctk.CTkFrame(self.proxy_custom_frame, fg_color="transparent")
        self.proxy_port_frame.pack(side="left", padx=(5, 10), pady=5)
        self.proxy_port_entry = ctk.CTkEntry(self.proxy_port_frame, width=60, fg_color="transparent", border_width=1, border_color=("#CBD5E1", "#334155"))
        self.proxy_port_entry.grid(row=0, column=0, padx=(0,5))
        self.proxy_port_entry.insert(0, config_manager.custom_proxy_port)
        
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
        
        self.on_api_mode_change(config_manager.api_domain_mode)
        self.on_proxy_mode_change(config_manager.proxy_mode)
        
        # 2. 下载格式
        ctk.CTkLabel(self, text="下载格式", font=("Microsoft YaHei", 16, "bold"), text_color=self.parent.color_text_primary).pack(pady=(15, 5), padx=20, anchor="w")
        self.format_var = ctk.StringVar(value=config_manager.download_format)
        format_frame = ctk.CTkFrame(self, fg_color="transparent")
        format_frame.pack(fill="x", padx=30)
        
        formats = ["jpg", "png", "webp", "原始格式"]
        for i, fmt in enumerate(formats):
            rb = ctk.CTkRadioButton(format_frame, text=fmt, variable=self.format_var, value=fmt, fg_color="#3B82F6", text_color=self.parent.color_text_primary)
            rb.grid(row=0, column=i, padx=(0, 15), pady=5, sticky="w")
            
        # 3. 文件命名设置
        ctk.CTkLabel(self, text="文件命名", font=("Microsoft YaHei", 16, "bold"), text_color=self.parent.color_text_primary).pack(pady=(15, 5), padx=20, anchor="w")
        self.naming_var = ctk.BooleanVar(value=config_manager.use_original_filename)
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
        config_manager.api_domain_mode = self.api_mode_var.get()
        config_manager.custom_api_domain = self.api_entry.get().strip()
        config_manager.proxy_mode = self.proxy_mode_var.get()
        config_manager.custom_proxy_ip = self.proxy_ip_entry.get().strip()
        config_manager.custom_proxy_port = self.proxy_port_entry.get().strip()
        
        try: config_manager.concurrent_comics = int(self.entry_cc.get())
        except: pass
        try: config_manager.comic_rest_time = int(self.entry_crt.get())
        except: pass
        try: config_manager.concurrent_images = int(self.entry_ci.get())
        except: pass
        try: config_manager.image_rest_time = int(self.entry_irt.get())
        except: pass
        
        config_manager.download_format = self.format_var.get()
        config_manager.use_original_filename = self.naming_var.get()
        
        config_manager.save_config()
        self.destroy()
