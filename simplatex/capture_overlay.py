import tkinter as tk
from functools import partial


class CaptureOverlay:
    def __init__(self, root, total_width, total_height, min_x, min_y, on_finish, on_cancel):
        self.root = root
        self.total_width = total_width
        self.total_height = total_height
        self.min_x = min_x
        self.min_y = min_y
        self.on_finish = on_finish
        self.on_cancel = on_cancel

        self.top = tk.Toplevel(self.root)
        self.top.geometry(f"{self.total_width}x{self.total_height}+{self.min_x}+{self.min_y}")
        self.top.attributes('-alpha', 0.3)
        self.top.attributes('-topmost', True)
        self.top.overrideredirect(True)

        try:
            self.top.focus_force()
            self.top.grab_set()
        except Exception:
            pass

        self.canvas = tk.Canvas(self.top, bg='gray', width=self.total_width, height=self.total_height)
        self.canvas.pack(fill='both', expand=True)
        try:
            self.canvas.focus_set()
        except Exception:
            pass

        self.start_x = tk.IntVar()
        self.start_y = tk.IntVar()
        self.rect = None

        self.top.bind('<Button-1>', self.on_button_press)
        self.top.bind('<B1-Motion>', self.on_mouse_drag)
        self.top.bind('<ButtonRelease-1>', self.on_button_release)

        self.top.bind('<Button-3>', lambda e: self.cancel())
        self.canvas.bind('<Button-3>', lambda e: self.cancel())
        self.top.bind('<Escape>', lambda e: self.cancel())

        self.top.bind('<Enter>', lambda e: self.show_hint())
        self.top.bind('<Leave>', lambda e: self.hide_hint())

        self.hint_label = None

    def show_hint(self):
        if self.top.winfo_exists() and self.hint_label is None:
            self.hint_label = tk.Label(self.top, text="右键或按ESC取消截图", 
                                       bg='yellow', fg='black', font=('Arial', 12, 'bold'))
            self.hint_label.place(relx=0.5, rely=0.1, anchor='center')

    def hide_hint(self):
        if self.hint_label is not None and self.hint_label.winfo_exists():
            self.hint_label.destroy()
            self.hint_label = None

    def on_button_press(self, event):
        self.start_x.set(event.x)
        self.start_y.set(event.y)
        self.rect = self.canvas.create_rectangle(self.start_x.get(), self.start_y.get(), self.start_x.get(), self.start_y.get(), outline='red')

    def on_mouse_drag(self, event):
        self.canvas.coords(self.rect, self.start_x.get(), self.start_y.get(), event.x, event.y)

    def on_button_release(self, event):
        end_x = event.x
        end_y = event.y

        left = min(self.start_x.get(), end_x)
        top = min(self.start_y.get(), end_y)
        right = max(self.start_x.get(), end_x)
        bottom = max(self.start_y.get(), end_y)

        actual_left = left + self.min_x
        actual_top = top + self.min_y
        actual_right = right + self.min_x
        actual_bottom = bottom + self.min_y

        self.destroy()
        if callable(self.on_finish):
            self.on_finish(actual_left, actual_top, actual_right, actual_bottom)

    def destroy(self):
        try:
            if self.top.winfo_exists():
                self.top.destroy()
        except Exception:
            pass

    def cancel(self):
        self.destroy()
        if callable(self.on_cancel):
            self.on_cancel() 