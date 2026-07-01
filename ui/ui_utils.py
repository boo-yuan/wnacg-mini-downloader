import customtkinter as ctk

class Toast(ctk.CTkFrame):
    def __init__(self, parent, message, duration=3000, type="info"):
        # colors for different types
        colors = {
            "info": ("#007AFF", "#0A84FF"),
            "error": ("#FF3B30", "#FF453A"),
            "success": ("#34C759", "#30D158")
        }
        color = colors.get(type, colors["info"])
        
        super().__init__(parent, fg_color=color, corner_radius=8)
        self.parent = parent
        self.message = message
        self.duration = duration
        
        self.label = ctk.CTkLabel(self, text=self.message, text_color="white", font=("Microsoft YaHei", 13, "bold"))
        self.label.pack(padx=20, pady=10)
        
    def show(self):
        # Place it at the top center
        self.place(relx=0.5, rely=0.05, anchor="n")
        self.lift()
        # Fade out / destroy after duration
        self.after(self.duration, self.destroy)
        
def show_toast(parent, message, type="info"):
    toast = Toast(parent, message, type=type)
    toast.show()
