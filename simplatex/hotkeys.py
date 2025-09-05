import time
import platform
from threading import Thread
from functools import partial

try:
    import keyboard as kb  # type: ignore
except Exception:
    kb = None

try:
    from pynput import keyboard as pynput_keyboard  # type: ignore
except Exception:
    pynput_keyboard = None


class HotkeyManager:
    def __init__(self, on_hotkey):
        self.on_hotkey = on_hotkey
        self.thread = None

    def start(self):
        if self.thread is not None and self.thread.is_alive():
            return
        self.thread = Thread(target=self._run)
        self.thread.daemon = True
        self.thread.start()

    def is_alive(self):
        return self.thread is not None and self.thread.is_alive()

    def _run(self):
        system_name = platform.system()
        # 优先 keyboard（Windows 体验较好）
        if kb is not None and system_name == 'Windows':
            try:
                kb.add_hotkey('ctrl+shift+win', partial(self.on_hotkey, "ctrl+shift+win"))
                kb.add_hotkey('ctrl+shift+alt', partial(self.on_hotkey, "ctrl+shift+alt"))
                kb.add_hotkey('ctrl+win+alt', partial(self.on_hotkey, "ctrl+win+alt"))
                while True:
                    time.sleep(1)
                return
            except Exception as e:
                print(f"keyboard 热键注册失败，回退到 pynput: {e}")
        # 回退到 pynput
        if pynput_keyboard is not None:
            if system_name == 'Darwin':
                mapping = {
                    '<ctrl>+<shift>+<cmd>': partial(self.on_hotkey, "ctrl+shift+win"),
                    '<ctrl>+<shift>+<alt>': partial(self.on_hotkey, "ctrl+shift+alt"),
                    '<ctrl>+<alt>+<cmd>': partial(self.on_hotkey, "ctrl+win+alt"),
                }
            elif system_name == 'Linux':
                mapping = {
                    '<ctrl>+<shift>+<super>': partial(self.on_hotkey, "ctrl+shift+win"),
                    '<ctrl>+<shift>+<alt>': partial(self.on_hotkey, "ctrl+shift+alt"),
                    '<ctrl>+<alt>+<super>': partial(self.on_hotkey, "ctrl+win+alt"),
                }
            else:
                mapping = {
                    '<ctrl>+<shift>+<cmd>': partial(self.on_hotkey, "ctrl+shift+win"),
                    '<ctrl>+<shift>+<alt>': partial(self.on_hotkey, "ctrl+shift+alt"),
                    '<ctrl>+<alt>+<cmd>': partial(self.on_hotkey, "ctrl+win+alt"),
                }
            try:
                hotkeys = pynput_keyboard.GlobalHotKeys(mapping)
                hotkeys.start()
                hotkeys.join()
                return
            except Exception as e:
                print(f"pynput 热键注册失败: {e}")
        print("未能注册全局热键。请使用界面按钮进行截图。") 