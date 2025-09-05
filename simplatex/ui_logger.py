import tkinter as tk
import time


class UILogger:
    def __init__(self, root, parent):
        self.root = root
        self.outer_frame = tk.Frame(parent)

        # 级别控制
        self.log_level_var = tk.StringVar(value='INFO')
        self.ctrl_frame = tk.Frame(self.outer_frame)
        self.ctrl_frame.pack(padx=8, fill='x')
        tk.Label(self.ctrl_frame, text="日志级别:").pack(side=tk.LEFT)
        self.level_menu = tk.OptionMenu(self.ctrl_frame, self.log_level_var, 'DEBUG', 'INFO', 'WARN', 'ERROR')
        self.level_menu.pack(side=tk.LEFT, padx=(5, 0))

        # 日志文本区
        self.text_frame = tk.Frame(self.outer_frame)
        self.text_frame.pack(padx=8, pady=5, fill='both', expand=True)
        self.log_text = tk.Text(self.text_frame, height=8, wrap='word', state='disabled')
        self.log_text.pack(side=tk.LEFT, fill='both', expand=True)
        self.scrollbar = tk.Scrollbar(self.text_frame, command=self.log_text.yview)
        self.scrollbar.pack(side=tk.RIGHT, fill='y')
        self.log_text.config(yscrollcommand=self.scrollbar.set)

        # 颜色标签
        self.log_text.tag_config('DEBUG', foreground='#666666')
        self.log_text.tag_config('INFO', foreground='#000000')
        self.log_text.tag_config('WARN', foreground='#c77d00')
        self.log_text.tag_config('ERROR', foreground='#cc0000')
        self.log_text.tag_config('SUCCESS', foreground='#2e7d32')

    def get_widget(self):
        return self.outer_frame

    def pack(self, *args, **kwargs):
        self.outer_frame.pack(*args, **kwargs)

    def set_level(self, level: str):
        self.log_level_var.set(level)

    def get_level(self) -> str:
        return self.log_level_var.get()

    def _level_to_value(self, level):
        mapping = {'DEBUG': 10, 'INFO': 20, 'SUCCESS': 25, 'WARN': 30, 'ERROR': 40}
        return mapping.get(level, 20)

    def _current_threshold(self):
        try:
            return self._level_to_value(self.log_level_var.get())
        except Exception:
            return 20

    def log(self, message, level='INFO'):
        if self._level_to_value(level) < self._current_threshold():
            try:
                print(f"{level}: {message}")
            except Exception:
                pass
            return
        ts = time.strftime("%H:%M:%S")
        line = f"[{ts}] {level}: {message}\n"

        def append():
            try:
                self.log_text.config(state='normal')
                self.log_text.insert('end', line, level)
                self.log_text.see('end')
                self.log_text.config(state='disabled')
            except Exception as e:
                print(f"日志输出失败: {e}")

        try:
            self.root.after(0, append)
        except Exception:
            append()
        try:
            print(f"{level}: {message}")
        except Exception:
            pass 