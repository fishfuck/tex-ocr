import tkinter as tk
from PIL import Image
import json
import requests
import os
import platform
from SimpletexApi import get_req_data, SIMPLETEX_APP_ID, SIMPLETEX_APP_SECRET
from DisplayScaling import get_monitors_info  # 使用跨平台实现
import time
from threading import Thread
from functools import partial

# 新组件
from ui_logger import UILogger
from screenshot import MultiMonitorScreenshot
from hotkeys import HotkeyManager
from capture_overlay import CaptureOverlay
from ocr_worker import OcrWorker

# 可选热键库仍用于 DPI 感知与平台差异
# 仅在 Windows 尝试设置 DPI 感知
if platform.system() == "Windows":
    import ctypes
    try:
        shcore = ctypes.windll.shcore
        PROCESS_PER_MONITOR_DPI_AWARE = 2
        shcore.SetProcessDpiAwareness(PROCESS_PER_MONITOR_DPI_AWARE)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


class ScreenCapture:
    def __init__(self, root):
        self.root = root
        self.root.title("屏幕公式ocr")
        self.root.geometry('450x500')
        
        # 设置任务栏图标
        try:
            icon_path = os.path.join(os.path.dirname(__file__), "favicon.ico")
            if os.path.exists(icon_path):
                self.root.iconbitmap(icon_path)
        except Exception as e:
            pass
        
        self.is_capturing = False
        self.select_position = None

        self.label = tk.Label(root, text="点击按钮开始截图")
        self.label.pack(pady=10)

        # 添加接口选择框架
        self.api_frame = tk.Frame(root)
        self.api_frame.pack(pady=5)
        
        self.api_label = tk.Label(self.api_frame, text="选择接口:")
        self.api_label.pack(side=tk.LEFT, padx=(0, 5))
        
        # 接口选择变量
        self.api_var = tk.StringVar(value="turbo")
        
        # 接口选择单选按钮
        self.turbo_radio = tk.Radiobutton(self.api_frame, text="轻量接口", 
                                        variable=self.api_var, value="turbo")
        self.turbo_radio.pack(side=tk.LEFT, padx=(0, 10))
        
        self.standard_radio = tk.Radiobutton(self.api_frame, text="标准接口", 
                                           variable=self.api_var, value="standard")
        self.standard_radio.pack(side=tk.LEFT)

        self.capture_button = tk.Button(root, text="开始截图", command=self.start_capture)
        self.capture_button.pack(pady=10)

        # 日志组件
        self.logger = UILogger(self.root, root)
        self.logger.pack(padx=8, pady=5, fill='both', expand=True)

        self.screen_width = 0
        self.screen_height = 0
        
        # 获取多显示器信息和缩放比例（跨平台）
        self.monitors_info = self.get_monitors_info()
        self.scaling_factor = 1.0  # 默认值，会在截图时动态确定
        
        # 创建截图处理器
        self.screenshot_handler = MultiMonitorScreenshot(self.monitors_info)
        
        # 显示检测到的显示器信息
        self.display_monitor_info()

        # 热键管理器 + 心跳
        self.hotkeys = HotkeyManager(self.trigger_capture_from_hotkey)
        self.start_hotkey_listener()
        self.ensure_hotkey_alive()
        
        self.logger.log("程序启动完成，已初始化界面与监听。")

    # 统一日志代理
    def log(self, message, level='INFO'):
        self.logger.log(message, level=level)
    
    def trigger_capture_from_hotkey(self, hotkey):
        try:
            self.root.after(0, lambda: self.start_capture(hotkey))
        except Exception as e:
            print(f"调度主线程截图失败: {e}")
            self.log(f"调度主线程截图失败: {e}", level='ERROR')
    
    def get_monitors_info(self):
        try:
            return get_monitors_info()
        except Exception as e:
            print(f"获取显示器信息失败: {e}")
            self.log(f"获取显示器信息失败，使用默认值: {e}", level='WARN')
            return [{'index': 0, 'scaling_factor': 1.0, 'width': 1920, 'height': 1080, 'x': 0, 'y': 0}]
    
    def get_monitor_for_position(self, x, y):
        for monitor in self.monitors_info:
            if (monitor['x'] <= x < monitor['x'] + monitor['width'] and 
                monitor['y'] <= y < monitor['y'] + monitor['height']):
                return monitor
        return self.monitors_info[0] if self.monitors_info else {'scaling_factor': 1.0}
    
    def start_hotkey_listener(self):
        self.hotkeys.start()
        self.log("热键监听线程已启动。")
    
    def ensure_hotkey_alive(self):
        try:
            if not self.hotkeys.is_alive():
                self.log("检测到热键线程不在运行，尝试重启...", level='WARN')
                self.hotkeys.start()
        except Exception as e:
            self.log(f"热键心跳检查异常: {e}", level='ERROR')
        finally:
            self.root.after(5000, self.ensure_hotkey_alive)

    def start_capture(self, hotkey=None):
        if getattr(self, 'is_capturing', False):
            print("正在进行截图，忽略重复触发的热键/点击")
            self.log("正在进行截图，忽略重复触发的热键/点击。", level='DEBUG')
            return
        self.is_capturing = True
        try:
            self.capture_button.config(state='disabled')
        except Exception:
            pass
        self.log(f"开始截图，触发方式: {hotkey or '按钮'}")
        self.root.withdraw()
        self.root.lift()
        self.root.after(500, partial(self.capture_screen, hotkey=hotkey))

    def capture_screen(self, hotkey=None):
        self.update_screen_dimensions()
        # 调用覆盖层组件
        def on_finish(l, t, r, b):
            self.on_region_selected(hotkey, l, t, r, b)
        def on_cancel():
            self.cancel_capture()
        self.overlay = CaptureOverlay(self.root, self.total_width, self.total_height, self.min_x, self.min_y, on_finish, on_cancel)
        self.log(f"创建截图窗口: 位置({self.min_x}, {self.min_y}), 尺寸 {self.total_width}x{self.total_height}", level='DEBUG')

    def cancel_capture(self):
        if hasattr(self, 'overlay'):
            try:
                self.overlay.destroy()
            except Exception:
                pass
        self.root.deiconify()
        self.label.config(text="截图已取消")
        self.is_capturing = False
        try:
            self.capture_button.config(state='normal')
        except Exception:
            pass
        self.log("截图已取消。")

    def on_region_selected(self, hotkey, actual_left, actual_top, actual_right, actual_bottom):
        self.log(f"最终截图区域: ({actual_left}, {actual_top}) 到 ({actual_right}, {actual_bottom})", level='DEBUG')
        screenshot = self.screenshot_handler.capture_area(actual_left, actual_top, actual_right, actual_bottom)
        if screenshot is None:
            print("截图失败！")
            self.root.deiconify()
            self.label.config(text="截图失败，请重试")
            self.is_capturing = False
            try:
                self.capture_button.config(state='normal')
            except Exception:
                pass
            self.log("截图失败，请重试。", level='ERROR')
            return
        # 保存临时文件
        tmp_path = "./screenshot.png"
        screenshot.save(tmp_path)
        self.log("已保存临时截图 ./screenshot.png", level='DEBUG')
        # 异步识别
        def api_url_getter():
            if self.api_var.get() == "standard":
                self.log("使用标准接口 /api/latex_ocr")
                return "https://server.simpletex.cn/api/latex_ocr"
            else:
                self.log("使用轻量接口 /api/latex_ocr_turbo")
                return "https://server.simpletex.cn/api/latex_ocr_turbo"
        def auth_getter():
            header, data = get_req_data({}, SIMPLETEX_APP_ID, SIMPLETEX_APP_SECRET)
            return header, data
        def on_done(text, raw):
            self.on_ocr_done(hotkey, text, raw, tmp_path)
        def on_error(exc):
            self.on_ocr_error(exc, tmp_path)
        self.ocr = OcrWorker(api_url_getter, auth_getter, on_done, on_error)
        self.ocr.submit(tmp_path)

    def on_ocr_error(self, exc, tmp_path):
        try:
            os.remove(tmp_path)
        except Exception:
            pass
        self.root.deiconify()
        self.label.config(text="识别失败，请重试")
        self.is_capturing = False
        try:
            self.capture_button.config(state='normal')
        except Exception:
            pass
        self.log(f"识别失败: {exc}", level='ERROR')

    def on_ocr_done(self, hotkey, text, raw, tmp_path):
        try:
            os.remove(tmp_path)
            self.log("已删除临时截图文件。", level='DEBUG')
        except Exception:
            pass
        if hotkey == "ctrl+shift+win":
            text = " $" + text + "$ "
        elif hotkey == "ctrl+shift+alt":
            text = "$$\n" + text + "\n$$"
        elif hotkey == "ctrl+win+alt":
            text = " $$" + text.strip() + "$$ "
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.root.update()
        print(raw)
        self.log("识别完成，结果已复制到剪贴板。", level='SUCCESS')
        self.root.deiconify()
        self.label.config(text="截图成功，已复制到剪切板")
        self.is_capturing = False
        try:
            self.capture_button.config(state='normal')
        except Exception:
            pass
        self.log("截图识别流程完成。", level='SUCCESS')

    def update_screen_dimensions(self):
        if not hasattr(self, 'monitors_info') or not self.monitors_info:
            self.monitors_info = self.get_monitors_info()
        min_x = min(monitor['x'] for monitor in self.monitors_info)
        min_y = min(monitor['y'] for monitor in self.monitors_info)
        max_x = max(monitor['x'] + monitor['width'] for monitor in self.monitors_info)
        max_y = max(monitor['y'] + monitor['height'] for monitor in self.monitors_info)
        self.total_width = max_x - min_x
        self.total_height = max_y - min_y
        self.min_x = min_x
        self.min_y = min_y
        print(f"屏幕边界: 最小({min_x}, {min_y}), 最大({max_x}, {max_y})")
        print(f"总尺寸: {self.total_width}x{self.total_height}")
        self.log(f"屏幕边界: 最小({min_x}, {min_y}), 最大({max_x}, {max_y}); 总尺寸: {self.total_width}x{self.total_height}", level='DEBUG')
        for monitor in self.monitors_info:
            monitor['relative_x'] = monitor['x'] - min_x
            monitor['relative_y'] = monitor['y'] - min_y
            print(f"显示器 {monitor['index']}: 相对位置({monitor['relative_x']}, {monitor['relative_y']})")

    def display_monitor_info(self):
        print(f"检测到 {len(self.monitors_info)} 个显示器:")
        self.log(f"检测到 {len(self.monitors_info)} 个显示器。", level='INFO')
        for monitor in self.monitors_info:
            print(f"  显示器 {monitor['index']}: 位置({monitor['x']},{monitor['y']}), "
                  f"尺寸{monitor['width']}x{monitor['height']}, "
                  f"缩放比例{monitor['scaling_factor']}")
            self.log(
                f"显示器 {monitor['index']}: 位置({monitor['x']},{monitor['y']}), 尺寸{monitor['width']}x{monitor['height']}, 缩放比例{monitor['scaling_factor']}",
                level='DEBUG'
            )
        if len(self.monitors_info) > 1:
            min_x = min(monitor['x'] for monitor in self.monitors_info)
            min_y = min(monitor['y'] for monitor in self.monitors_info)
            max_x = max(monitor['x'] + monitor['width'] for monitor in self.monitors_info)
            max_y = max(monitor['y'] + monitor['height'] for monitor in self.monitors_info)
            total_width = max_x - min_x
            total_height = max_y - min_y
            print(f"总屏幕区域: 位置({min_x}, {min_y}), 尺寸{total_width}x{total_height}")
            self.log(f"总屏幕区域: 位置({min_x}, {min_y}), 尺寸{total_width}x{total_height}", level='DEBUG')

    def cleanup(self):
        if hasattr(self, 'screenshot_handler'):
            self.screenshot_handler.close()
        self.log("已清理资源，准备退出。")

    def __del__(self):
        self.cleanup()

if __name__ == "__main__":
    root = tk.Tk()
    app = ScreenCapture(root)
    
    def on_closing():
        app.cleanup()
        root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()
