import customtkinter as ctk

class AutoHideScrollableFrame(ctk.CTkScrollableFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self._setup_autohide()

    def _setup_autohide(self):
        self._check_job = None
        
        def check_scrollbar():
            self._check_job = None
            canvas = self._parent_canvas
            bbox = canvas.bbox("all")
            if not bbox: return
            
            content_height = bbox[3] - bbox[1]
            canvas_height = canvas.winfo_height()
            
            if content_height <= canvas_height + 2:
                if self._scrollbar.winfo_ismapped():
                    self._scrollbar.grid_remove()
            else:
                if not self._scrollbar.winfo_ismapped():
                    self._scrollbar.grid()

        def on_configure(*args):
            if self._check_job is not None:
                self.after_cancel(self._check_job)
            self._check_job = self.after(50, check_scrollbar)
                    
        canvas = self._parent_canvas
        content_frame = self._parent_frame
        
        canvas.bind("<Configure>", on_configure, add="+")
        content_frame.bind("<Configure>", on_configure, add="+")
        
        self.after(100, check_scrollbar)
