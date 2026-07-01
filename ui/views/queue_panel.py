import tkinter as tk
import customtkinter as ctk
from ui.components.scrollable_frame import AutoHideScrollableFrame
from services.download_manager import download_manager
from core.event_bus import event_bus

class QueuePanel(ctk.CTkFrame):
    def __init__(self, master, app_colors, app_fonts):
        super().__init__(master, fg_color=app_colors['frame'], corner_radius=16)
        self.colors = app_colors
        self.fonts = app_fonts
        
        self.selected_task_ids = set()
        self.last_clicked_task_id = None
        self.ui_tasks = {} # task_id -> frame, progressbar, status_lbl
        
        self.setup_ui()
        
        event_bus.subscribe("TASK_ADDED", self.on_task_added)
        event_bus.subscribe("TASK_ADDED_FROM_CACHE", self.on_task_added)
        event_bus.subscribe("TASK_PROGRESS", self.on_task_progress)
        event_bus.subscribe("TASK_REMOVED", self.on_task_removed)

    def setup_ui(self):
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        header_frame_c = ctk.CTkFrame(self, fg_color="transparent")
        header_frame_c.grid(row=0, column=0, pady=(24, 8), padx=24, sticky="ew")
        header_frame_c.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(header_frame_c, text="任务队列", font=self.fonts['h2'], text_color=self.colors['text_primary']).grid(row=0, column=0, sticky="w")
        
        self.queue_frame = AutoHideScrollableFrame(self, corner_radius=8, fg_color="transparent", bg_color="transparent")
        self.queue_frame.grid(row=1, column=0, padx=16, pady=(0, 16), sticky="nsew")
        
        if hasattr(self.queue_frame, '_parent_canvas'):
            self.queue_frame._parent_canvas.bind("<Button-1>", self.on_empty_click)
            self.queue_frame._parent_canvas.bind("<Button-3>", self.on_empty_right_click)
            self.queue_frame._parent_canvas.bind("<B1-Motion>", self.on_drag_motion)

    # Event handlers
    def on_task_added(self, task_data):
        self.after(0, lambda: self.add_task_to_ui(task_data))

    def on_task_progress(self, task_id, status_text, progress_val):
        self.after(0, lambda: self.update_task_ui(task_id, status_text, progress_val))

    def on_task_removed(self, task_id):
        self.after(0, lambda: self.remove_task_ui(task_id))

    def add_task_to_ui(self, task_data):
        item_frame = ctk.CTkFrame(self.queue_frame, corner_radius=8, fg_color=self.colors['item_default'], border_width=2, border_color=self.colors['bg'])
        item_frame.pack(fill="x", padx=4, pady=4)
        item_frame.grid_columnconfigure(0, weight=1)
        
        lbl_title = ctk.CTkLabel(item_frame, text=task_data['title'], font=self.fonts['body_bold'], text_color=self.colors['text_primary'], anchor="w", justify="left")
        lbl_title.grid(row=0, column=0, padx=8, pady=(8, 0), sticky="nw")
        
        lbl_status = ctk.CTkLabel(item_frame, text=task_data['status'], font=self.fonts['small'], text_color=self.colors['text_secondary'], anchor="w")
        lbl_status.grid(row=1, column=0, padx=8, pady=(4, 0), sticky="nw")
        
        progressbar = ctk.CTkProgressBar(item_frame, progress_color=self.colors['btn_primary'], fg_color=self.colors['bg'], height=6)
        progressbar.grid(row=2, column=0, padx=8, pady=(4, 8), sticky="ew")
        progressbar.set(task_data.get('progress', 0.0))
        
        self.ui_tasks[task_data['id']] = {
            'frame': item_frame,
            'lbl_status': lbl_status,
            'progressbar': progressbar
        }
        
        self._bind_click_recursive(item_frame, task_data['id'])
        self.queue_frame._parent_canvas.after(100, lambda: self.queue_frame._parent_canvas.event_generate("<Configure>"))

    def update_task_ui(self, task_id, status_text, progress_val):
        if task_id not in self.ui_tasks: return
        ui_obj = self.ui_tasks[task_id]
        
        is_error = "失败" in status_text or "错误" in status_text
        if is_error:
            text_color = ("#FF3B30", "#FF453A")
            pb_color = ("#FF3B30", "#FF453A")
        elif "暂停" in status_text:
            text_color = self.colors['btn_warning']
            pb_color = self.colors['btn_warning']
        elif "解析" in status_text:
            text_color = ("#AF52DE", "#BF5AF2")
            pb_color = ("#AF52DE", "#BF5AF2")
        elif "准备" in status_text:
            text_color = ("#34C759", "#30D158")
            pb_color = ("#34C759", "#30D158")
        elif "等待" in status_text:
            text_color = self.colors['text_secondary']
            pb_color = self.colors['btn_secondary']
        else:
            text_color = self.colors['btn_primary']
            pb_color = self.colors['btn_primary']
            
        ui_obj['lbl_status'].configure(text=status_text, text_color=text_color)
        ui_obj['progressbar'].set(progress_val)
        ui_obj['progressbar'].configure(progress_color=pb_color)

    def remove_task_ui(self, task_id):
        if task_id in self.ui_tasks:
            frame = self.ui_tasks[task_id]['frame']
            if frame.winfo_exists():
                frame.destroy()
            del self.ui_tasks[task_id]
            
        if task_id in self.selected_task_ids:
            self.selected_task_ids.remove(task_id)
            self.update_task_selection_ui()
            
        self.queue_frame._parent_canvas.after(100, lambda: self.queue_frame._parent_canvas.event_generate("<Configure>"))

    # Select / drag logic
    def on_empty_click(self, event):
        self.drag_start_y = event.y_root
        
        is_ctrl = (event.state & 0x0004) != 0
        if not is_ctrl:
            self.selected_task_ids.clear()
            self.last_clicked_task_id = None
            
        self.drag_start_selected = set(self.selected_task_ids)
        self.drag_item_coords = {}
        for k, ui_obj in self.ui_tasks.items():
            f = ui_obj['frame']
            if f and f.winfo_exists():
                self.drag_item_coords[k] = (f.winfo_rooty(), f.winfo_height())
                
        self.update_task_selection_ui()

    def _bind_click_recursive(self, widget, task_id):
        if isinstance(widget, ctk.CTkButton):
            return
        widget.bind("<Button-1>", lambda e: self.on_task_click(e, task_id))
        widget.bind("<Double-Button-1>", lambda e: self.on_task_double_click(e, task_id))
        widget.bind("<B1-Motion>", self.on_drag_motion)
        widget.bind("<Button-3>", lambda e: self.on_task_right_click(e, task_id))
        for child in widget.winfo_children():
            self._bind_click_recursive(child, task_id)

    def on_task_click(self, event, task_id):
        self.drag_start_y = event.y_root
        
        is_ctrl = (event.state & 0x0004) != 0
        is_shift = (event.state & 0x0001) != 0
        
        all_ids = [t_id for t_id in self.ui_tasks.keys() if self.ui_tasks[t_id]['frame'].winfo_exists()]
        
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
        self.drag_item_coords = {}
        for k, ui_obj in self.ui_tasks.items():
            f = ui_obj['frame']
            if f and f.winfo_exists():
                self.drag_item_coords[k] = (f.winfo_rooty(), f.winfo_height())
                
        self.update_task_selection_ui()

    def on_drag_motion(self, event):
        if not hasattr(self, 'drag_start_y'): return
        
        y1 = min(self.drag_start_y, event.y_root)
        y2 = max(self.drag_start_y, event.y_root)
        
        is_ctrl = (event.state & 0x0004) != 0
        new_selection = set(self.drag_start_selected) if is_ctrl else set()
        
        for t_id, (fy, fh) in getattr(self, 'drag_item_coords', {}).items():
            
            if (fy + fh >= y1) and (fy <= y2):
                new_selection.add(t_id)
            elif not is_ctrl and t_id in new_selection:
                new_selection.discard(t_id)
                
        if new_selection != self.selected_task_ids:
            self.selected_task_ids = new_selection
            self.update_task_selection_ui()

    def update_task_selection_ui(self):
        for t_id, ui_obj in self.ui_tasks.items():
            frame = ui_obj['frame']
            if not frame.winfo_exists(): continue
            if t_id in self.selected_task_ids:
                frame.configure(fg_color=self.colors['item_selected'], border_color=self.colors['item_border_selected'])
            else:
                frame.configure(fg_color=self.colors['item_default'], border_color=self.colors['bg'])

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
            
        menu = tk.Menu(self, tearoff=0, font=("Microsoft YaHei", 11))
        menu.add_command(label="全选队列", command=self.select_all_tasks)
        menu.add_command(label="取消选中", command=self.clear_task_selection)
        menu.add_separator()
        menu.add_command(label="继续下载", command=self.resume_selected_tasks)
        menu.add_command(label="暂停下载", command=self.pause_selected_tasks)
        menu.add_separator()
        menu.add_command(label="取消任务", command=self.cancel_selected_tasks)
        menu.add_command(label="移除任务", command=self.remove_selected_tasks)
        
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def select_all_tasks(self):
        self.selected_task_ids = {t_id for t_id in self.ui_tasks.keys() if self.ui_tasks[t_id]['frame'].winfo_exists()}
        self.update_task_selection_ui()
        
    def pause_selected_tasks(self):
        for t_id in self.selected_task_ids:
            download_manager.pause_task(t_id)

    def resume_selected_tasks(self):
        for t_id in self.selected_task_ids:
            download_manager.resume_task(t_id)

    def cancel_selected_tasks(self):
        for t_id in list(self.selected_task_ids):
            download_manager.cancel_task(t_id)

    def remove_selected_tasks(self):
        for t_id in list(self.selected_task_ids):
            download_manager.remove_task(t_id)
        self.selected_task_ids.clear()

    def on_task_double_click(self, event, task_id):
        task = download_manager.tasks.get(task_id)
        if task:
            if task['is_paused']:
                download_manager.resume_task(task_id)
            else:
                download_manager.pause_task(task_id)
