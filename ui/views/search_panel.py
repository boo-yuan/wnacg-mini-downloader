import tkinter as tk
import customtkinter as ctk
import threading
from ui.components.scrollable_frame import AutoHideScrollableFrame
from services.search_service import search_service
from services.download_manager import download_manager
from core.event_bus import event_bus
from network.client import network_client

class SearchPanel(ctk.CTkFrame):
    def __init__(self, master, app_colors, app_fonts):
        super().__init__(master, fg_color=app_colors['frame'], corner_radius=16)
        self.colors = app_colors
        self.fonts = app_fonts
        self.current_page = 1
        self.total_pages = 1
        self.current_query = ""
        self.is_searching = False
        
        self.current_search_items = {}
        self.selected_search_ids = set()
        self.last_clicked_search_id = None
        self.search_drag_start_selected = set()
        
        self.setup_ui()
        event_bus.subscribe("TASK_PROGRESS", self.on_task_progress)
        event_bus.subscribe("TASK_COMPLETED", self.on_task_completed)
        event_bus.subscribe("TASK_REMOVED", self.on_task_removed)
        
        self._start_disk_status_watcher()

    def setup_ui(self):
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(self, text="资源探索", font=self.fonts['h2'], text_color=self.colors['text_primary']).grid(row=0, column=0, pady=(16, 0), padx=16, sticky="w")
        
        search_frame = ctk.CTkFrame(self, fg_color="transparent")
        search_frame.grid(row=1, column=0, padx=16, pady=8, sticky="ew")
        search_frame.grid_columnconfigure(0, weight=1)
        
        self.search_entry = ctk.CTkEntry(search_frame, placeholder_text="输入漫画名称开始搜索...", height=40, font=self.fonts['body'], fg_color=self.colors['item_default'], border_width=0, corner_radius=8, text_color=self.colors['text_primary'])
        self.search_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.search_entry.bind('<Return>', lambda e: self.start_search(1))
        
        self.paste_btn = ctk.CTkButton(search_frame, text="📋", width=40, height=40, font=("Arial", 16), fg_color=self.colors['item_default'], text_color=self.colors['text_secondary'], hover_color=self.colors['btn_secondary_hover'], corner_radius=8, command=self._quick_paste)
        self.paste_btn.grid(row=0, column=1, padx=(0, 8))
        
        self.clear_btn = ctk.CTkButton(search_frame, text="✕", width=40, height=40, font=("Arial", 16), fg_color=self.colors['item_default'], text_color=self.colors['text_secondary'], hover_color=self.colors['btn_secondary_hover'], corner_radius=8, command=lambda: self.search_entry.delete(0, 'end'))
        self.clear_btn.grid(row=0, column=2, padx=(0, 16))
        
        self.search_btn = ctk.CTkButton(search_frame, text="搜索", width=88, height=40, font=self.fonts['body_bold'], fg_color=self.colors['btn_primary'], hover_color=self.colors['btn_primary_hover'], text_color=self.colors['text_on_primary'], corner_radius=8, command=lambda: self.start_search(1))
        self.search_btn.grid(row=0, column=3)
        
        self.list_frame = AutoHideScrollableFrame(self, corner_radius=8, fg_color="transparent", bg_color="transparent")
        self.list_frame.grid(row=2, column=0, padx=8, pady=0, sticky="nsew")
        
        if hasattr(self.list_frame, '_parent_canvas'):
            self.list_frame._parent_canvas.bind("<Button-1>", self.on_search_empty_click)
            self.list_frame._parent_canvas.bind("<B1-Motion>", self.on_search_drag_motion)
            
        self.pagination_frame = ctk.CTkFrame(self, fg_color="transparent", height=40)
        self.pagination_frame.grid(row=3, column=0, pady=(8, 16))

    def _start_disk_status_watcher(self):
        def watcher_loop():
            import re
            import os
            import time
            from core.config_manager import config_manager
            while True:
                time.sleep(2)
                if self.is_searching: continue
                if not self.current_search_items: continue
                
                try:
                    for aid, info in list(self.current_search_items.items()):
                        btn = info.get('list_btn')
                        if not btn or not btn.winfo_exists(): continue
                        
                        item = info['data']
                        task_id = f"task_{aid}"
                        
                        if task_id in download_manager.tasks:
                            info['last_disk_exists'] = None
                            continue
                            
                        base_title = re.sub(r'[\\/*?:"<>|]', '_', item['title']).strip()
                        if base_title.startswith("[未完成]_"):
                            base_title = base_title[len("[未完成]_"):]
                        completed_dir = os.path.join(config_manager.download_path, base_title)
                        
                        exists = os.path.exists(completed_dir)
                        last_exists = info.get('last_disk_exists')
                        
                        if exists != last_exists:
                            info['last_disk_exists'] = exists
                            if exists:
                                self.after(0, lambda b=btn: self._set_btn_state(b, "下载完成"))
                            else:
                                self.after(0, lambda b=btn: self._set_btn_state(b, "一键下载"))
                                self.after(0, lambda b=btn, t=task_id, i=item: b.configure(command=lambda inner_b=b: self.trigger_download(t, i, inner_b)))
                except Exception as e:
                    pass
                    
        threading.Thread(target=watcher_loop, daemon=True).start()

    def _quick_paste(self):
        try:
            text = self.clipboard_get()
            self.search_entry.delete(0, 'end')
            self.search_entry.insert(0, text)
        except Exception:
            pass

    def start_search(self, page=1):
        query = self.search_entry.get().strip()
        if not query: return
        
        download_manager.sync_disk_state()
        
        self.current_query = query
        self.current_page = page
        self.is_searching = True
        self.search_btn.configure(text="加载中...", state="disabled")
        
        for widget in self.list_frame.winfo_children():
            widget.destroy()
            
        ctk.CTkLabel(self.list_frame, text="正在连接服务器...", font=self.fonts['body'], text_color=self.colors['text_secondary'], fg_color='transparent').pack(pady=40)
        
        import asyncio
        asyncio.run_coroutine_threadsafe(self._search_task(query, page), download_manager.loop)
        
    async def _search_task(self, query, page):
        results, total_pages, err = await search_service.search(query, page)
        self.after(0, self.update_list_ui, results, total_pages, err)
        
    def update_list_ui(self, results, total_pages, err):
        self.is_searching = False
        self.search_btn.configure(text="搜索", state="normal")
        self.total_pages = total_pages
        
        self.current_search_items.clear()
        self.selected_search_ids.clear()
        self.last_clicked_search_id = None
        
        for widget in self.list_frame.winfo_children():
            widget.destroy()
            
        if err:
            ctk.CTkLabel(self.list_frame, text=err, font=self.fonts['body'], text_color="#EF4444").pack(pady=40)
            return
            
        if not results:
            ctk.CTkLabel(self.list_frame, text="未找到相关资源", font=self.fonts['body'], text_color=self.colors['text_secondary'], fg_color='transparent').pack(pady=40)
            self.update_pagination()
            return
            
        for item in results:
            self.create_list_item(item)
            
        self.update_pagination()
        self.list_frame._parent_canvas.after(100, lambda: self.list_frame._parent_canvas.event_generate("<Configure>"))

    def create_list_item(self, item):
        item_frame = ctk.CTkFrame(self.list_frame, corner_radius=8, fg_color=self.colors['item_default'], border_width=2, border_color=self.colors['bg'])
        item_frame.pack(fill="x", padx=8, pady=4)
        item_frame.grid_columnconfigure(1, weight=1)
        item_frame.grid_rowconfigure(2, weight=1)
        
        img_label = ctk.CTkLabel(item_frame, text="Loading", width=56, height=76, fg_color='transparent', text_color=self.colors['text_secondary'], corner_radius=4)
        img_label.grid(row=0, column=0, rowspan=3, padx=(12, 16), pady=12)
        
        if item['img_url']:
            import asyncio
            asyncio.run_coroutine_threadsafe(self._load_image_task(item['img_url'], img_label), download_manager.loop)
            
        title_label = ctk.CTkLabel(item_frame, text=item['title'], font=self.fonts['body_bold'], text_color=self.colors['text_primary'], anchor="w", justify="left", wraplength=320)
        title_label.grid(row=0, column=1, padx=0, pady=(12, 4), sticky="nw")
        
        count_label = ctk.CTkLabel(item_frame, text=item['count'], font=self.fonts['small'], text_color=self.colors['text_secondary'], anchor="w")
        count_label.grid(row=1, column=1, padx=0, pady=0, sticky="nw")
        
        btn = ctk.CTkButton(item_frame, text="一键下载", font=self.fonts['small'], fg_color=self.colors['btn_primary'], hover_color=self.colors['btn_primary_hover'], text_color=self.colors['text_on_primary'], width=72, height=28, corner_radius=4)
        btn.grid(row=2, column=1, padx=(0, 12), pady=(4, 12), sticky="se")
        
        if not item['aid']:
            btn.configure(state="disabled", text="无法解析AID")
        else:
            task_id = f"task_{item['aid']}"
            if task_id in download_manager.tasks:
                status = download_manager.tasks[task_id]['status']
                if "完成" in status:
                    self._set_btn_state(btn, "下载完成")
                else:
                    self._set_btn_state(btn, "下载中" if "下载中" in status or "准备" in status or "解析" in status else "继续下载")
            else:
                self._set_btn_state(btn, "一键下载")
                
            btn.configure(command=lambda b=btn: self.trigger_download(task_id, item, b))

        self.current_search_items[item['aid']] = {
            'data': item,
            'ui_frame': item_frame,
            'list_btn': btn
        }
        self._bind_search_click_recursive(item_frame, item['aid'])

    def _set_btn_state(self, btn, state):
        if not btn.winfo_exists(): return
        if state == "等待中":
            btn.configure(text="等待中", fg_color=self.colors['btn_disabled'], hover_color=self.colors['btn_disabled'], text_color=self.colors['text_secondary'], state="disabled")
        elif state == "下载中":
            btn.configure(text="下载中", fg_color=self.colors['btn_primary'], hover_color=self.colors['btn_primary_hover'], text_color=self.colors['text_on_primary'], state="disabled")
        elif state == "继续下载":
            btn.configure(text="继续下载", fg_color=self.colors['btn_warning'], hover_color=self.colors['btn_warning'], text_color=self.colors['text_on_primary'], state="normal")
        elif state == "一键下载":
            btn.configure(text="一键下载", fg_color=self.colors['btn_primary'], hover_color=self.colors['btn_primary_hover'], text_color=self.colors['text_on_primary'], state="normal")
        elif state == "下载完成":
            btn.configure(text="下载完成", fg_color=self.colors['btn_disabled'], hover_color=self.colors['btn_disabled'], text_color=self.colors['text_secondary'], state="disabled")

    def trigger_download(self, task_id, item, btn):
        download_manager.add_task(task_id, item['aid'], item['title'], item['domain'])
        self._set_btn_state(btn, "等待中")

    async def _load_image_task(self, url, label):
        image = await network_client.download_thumbnail(url)
        if image and label.winfo_exists():
            ctk_img = ctk.CTkImage(light_image=image, dark_image=image, size=(56, 76))
            self.after(0, lambda: label.configure(image=ctk_img, text=""))
        elif label.winfo_exists():
            self.after(0, lambda: label.configure(text="Failed"))

    def update_pagination(self):
        for widget in self.pagination_frame.winfo_children():
            widget.destroy()
            
        if self.current_query and self.total_pages > 0:
            prev_btn = ctk.CTkButton(self.pagination_frame, text="◀", width=36, height=32, font=("Arial", 14, "bold"),
                                     fg_color=self.colors['item_default'], text_color=self.colors['text_primary'], hover_color=self.colors['bg'],
                                     command=lambda: self.start_search(max(1, self.current_page - 1)),
                                     state="normal" if self.current_page > 1 else "disabled")
            prev_btn.pack(side="left", padx=4)
            
            start_page = max(1, self.current_page - 2)
            end_page = min(self.total_pages, self.current_page + 2)
            
            if start_page > 1:
                p_first = ctk.CTkButton(self.pagination_frame, text="1", width=36, height=32, font=self.fonts['small'],
                                       fg_color=self.colors['item_default'], text_color=self.colors['text_primary'], hover_color=self.colors['bg'],
                                       command=lambda: self.start_search(1))
                p_first.pack(side="left", padx=4)
                if start_page > 2:
                    ctk.CTkLabel(self.pagination_frame, text="...", font=self.fonts['small'], text_color=self.colors['text_secondary'], fg_color='transparent').pack(side="left", padx=4)
            
            for p in range(start_page, end_page + 1):
                if p == self.current_page:
                    p_btn = ctk.CTkButton(self.pagination_frame, text=str(p), width=36, height=32, font=self.fonts['body_bold'],
                                          fg_color=self.colors['btn_primary'], text_color=self.colors['text_on_primary'], hover_color=self.colors['btn_primary_hover'])
                else:
                    p_btn = ctk.CTkButton(self.pagination_frame, text=str(p), width=36, height=32, font=self.fonts['small'],
                                          fg_color=self.colors['item_default'], text_color=self.colors['text_primary'], hover_color=self.colors['bg'],
                                          command=lambda p=p: self.start_search(p))
                p_btn.pack(side="left", padx=4)
                
            if end_page < self.total_pages:
                if end_page < self.total_pages - 1:
                    ctk.CTkLabel(self.pagination_frame, text="...", font=self.fonts['small'], text_color=self.colors['text_secondary'], fg_color='transparent').pack(side="left", padx=4)
                p_last = ctk.CTkButton(self.pagination_frame, text=str(self.total_pages), width=36, height=32, font=self.fonts['small'],
                                       fg_color=self.colors['item_default'], text_color=self.colors['text_primary'], hover_color=self.colors['bg'],
                                       command=lambda: self.start_search(self.total_pages))
                p_last.pack(side="left", padx=4)
            
            next_btn = ctk.CTkButton(self.pagination_frame, text="▶", width=36, height=32, font=("Arial", 14, "bold"),
                                     fg_color=self.colors['item_default'], text_color=self.colors['text_primary'], hover_color=self.colors['bg'],
                                     command=lambda: self.start_search(min(self.total_pages, self.current_page + 1)),
                                     state="normal" if self.current_page < self.total_pages else "disabled")
            next_btn.pack(side="left", padx=4)

    # Event Handlers
    def on_task_progress(self, task_id, status_text, progress_val):
        aid = task_id.replace("task_", "")
        if aid in self.current_search_items:
            btn = self.current_search_items[aid]['list_btn']
            self.after(0, lambda: self._set_btn_state(btn, "下载中" if "下载" in status_text or "解析" in status_text else "继续下载"))

    def on_task_completed(self, task_id):
        aid = task_id.replace("task_", "")
        if aid in self.current_search_items:
            btn = self.current_search_items[aid]['list_btn']
            self.after(0, lambda: self._set_btn_state(btn, "下载完成"))

    def on_task_removed(self, task_id):
        aid = task_id.replace("task_", "")
        if aid in self.current_search_items:
            btn = self.current_search_items[aid]['list_btn']
            self.after(0, lambda: self._set_btn_state(btn, "一键下载"))

    # Multi-selection logic
    def on_search_empty_click(self, event):
        self.search_drag_start_y = event.y_root
        is_ctrl = (event.state & 0x0004) != 0
        if not is_ctrl:
            self.selected_search_ids.clear()
            self.last_clicked_search_id = None
        self.search_drag_start_selected = set(self.selected_search_ids)
        self.update_search_selection_ui()

    def _bind_search_click_recursive(self, widget, aid):
        if isinstance(widget, ctk.CTkButton):
            return
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
        self.search_drag_item_coords = {}
        for k, item_info in self.current_search_items.items():
            f = item_info['ui_frame']
            if f and f.winfo_exists():
                self.search_drag_item_coords[k] = (f.winfo_rooty(), f.winfo_height())
                
        self.update_search_selection_ui()

    def on_search_drag_motion(self, event):
        if not hasattr(self, 'search_drag_start_y'): return
        
        y1 = min(self.search_drag_start_y, event.y_root)
        y2 = max(self.search_drag_start_y, event.y_root)
        
        is_ctrl = (event.state & 0x0004) != 0
        new_selection = set(self.search_drag_start_selected) if is_ctrl else set()
        
        for aid, (fy, fh) in getattr(self, 'search_drag_item_coords', {}).items():
            
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
                frame.configure(fg_color=self.colors['item_selected'], border_color=self.colors['item_border_selected'])
            else:
                frame.configure(fg_color=self.colors['item_default'], border_color=self.colors['bg'])

    def clear_search_selection(self):
        self.selected_search_ids.clear()
        self.last_clicked_search_id = None
        self.update_search_selection_ui()

    def on_search_right_click(self, event, aid):
        if aid not in self.selected_search_ids:
            self.selected_search_ids = {aid}
            self.last_clicked_search_id = aid
            self.update_search_selection_ui()
            
        menu = tk.Menu(self, tearoff=0, font=("Microsoft YaHei", 11))
        menu.add_command(label="全选列表", command=self.select_all_search)
        menu.add_command(label="取消选中", command=self.clear_search_selection)
        menu.add_separator()
        menu.add_command(label="加入列队", command=self.batch_add_to_queue)
        
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
                self.trigger_download(task_id, item_info['data'], item_info['list_btn'])
        self.selected_search_ids.clear()
        self.update_search_selection_ui()
