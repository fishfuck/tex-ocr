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
import mss
import mss.tools

# 可选热键库：优先 keyboard（在 Windows 上较好用），否则回退到 pynput
try:
    import keyboard as kb  # type: ignore
except Exception:
    kb = None

try:
    from pynput import keyboard as pynput_keyboard  # type: ignore
except Exception:
    pynput_keyboard = None

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


class MultiMonitorScreenshot:
    """多显示器截图处理类（按次创建 mss 以增强稳定性）"""
    
    def __init__(self, monitors_info):
        self.monitors_info = monitors_info
    
    def _grab_with_retry(self, region):
        """使用 mss 抓取，失败自动重试一次。"""
        last_err = None
        for attempt in range(2):
            try:
                with mss.mss() as sct:
                    screenshot = sct.grab(region)
                    return screenshot
            except Exception as e:
                last_err = e
                print(f"mss 抓取失败（第{attempt+1}次）: {e}")
                time.sleep(0.05)
        raise last_err if last_err else RuntimeError("未知的 mss 抓取失败")
    
    def capture_area(self, left, top, right, bottom):
        """截取指定区域的屏幕（每次创建 mss）"""
        try:
            region = {
                'left': int(left),
                'top': int(top),
                'width': max(0, int(right) - int(left)),
                'height': max(0, int(bottom) - int(top))
            }
            print(f"截图区域: {region}")
            screenshot = self._grab_with_retry(region)
            img = Image.frombytes("RGB", screenshot.size, screenshot.rgb)
            return img
        except Exception as e:
            print(f"截图失败: {e}")
            return None
    
    def capture_monitor(self, monitor_index):
        """截取指定显示器的整个屏幕（每次创建 mss）"""
        try:
            monitor = self.monitors_info[monitor_index]
            region = {
                'left': int(monitor['x']),
                'top': int(monitor['y']),
                'width': int(monitor['width']),
                'height': int(monitor['height'])
            }
            print(f"截取显示器 {monitor_index}: {region}")
            screenshot = self._grab_with_retry(region)
            img = Image.frombytes("RGB", screenshot.size, screenshot.rgb)
            return img
        except Exception as e:
            print(f"截取显示器 {monitor_index} 失败: {e}")
            return None
    
    def close(self):
        """兼容旧接口，按次创建无需关闭"""
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
        
        # 日志级别控制
        self.log_level_var = tk.StringVar(value='INFO')
        self.log_ctrl_frame = tk.Frame(root)
        self.log_ctrl_frame.pack(padx=8, fill='x')
        tk.Label(self.log_ctrl_frame, text="日志级别:").pack(side=tk.LEFT)
        self.log_level_menu = tk.OptionMenu(self.log_ctrl_frame, self.log_level_var, 'DEBUG', 'INFO', 'WARN', 'ERROR')
        self.log_level_menu.pack(side=tk.LEFT, padx=(5, 0))

        # 日志区域
        self.log_frame = tk.Frame(root)
        self.log_frame.pack(padx=8, pady=5, fill='both', expand=True)
        self.log_text = tk.Text(self.log_frame, height=8, wrap='word', state='disabled')
        self.log_text.pack(side=tk.LEFT, fill='both', expand=True)
        self.log_scroll = tk.Scrollbar(self.log_frame, command=self.log_text.yview)
        self.log_scroll.pack(side=tk.RIGHT, fill='y')
        self.log_text.config(yscrollcommand=self.log_scroll.set)
        # 日志颜色标签
        self.log_text.tag_config('DEBUG', foreground='#666666')
        self.log_text.tag_config('INFO', foreground='#000000')
        self.log_text.tag_config('WARN', foreground='#c77d00')
        self.log_text.tag_config('ERROR', foreground='#cc0000')
        self.log_text.tag_config('SUCCESS', foreground='#2e7d32')

        self.screen_width = 0
        self.screen_height = 0
        
        # 获取多显示器信息和缩放比例（跨平台）
        self.monitors_info = self.get_monitors_info()
        self.scaling_factor = 1.0  # 默认值，会在截图时动态确定
        
        # 创建截图处理器
        self.screenshot_handler = MultiMonitorScreenshot(self.monitors_info)
        
        # 显示检测到的显示器信息
        self.display_monitor_info()

        # 监听线程引用
        self.hotkey_thread = None
        
        # 启动监听快捷键的线程
        self.start_hotkey_listener()
        # 启动心跳自检
        self.ensure_hotkey_alive()
        
        # 启动完成日志
        self.log("程序启动完成，已初始化界面与监听。")
    
    def _level_to_value(self, level):
        mapping = {'DEBUG': 10, 'INFO': 20, 'SUCCESS': 25, 'WARN': 30, 'ERROR': 40}
        return mapping.get(level, 20)

    def _current_threshold(self):
        try:
            return self._level_to_value(self.log_level_var.get())
        except Exception:
            return 20

    def log(self, message, level='INFO'):
        """线程安全的日志输出到界面与控制台，带等级与颜色"""
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
    
    def trigger_capture_from_hotkey(self, hotkey):
        """将热键事件转发到主线程执行 Tk 操作"""
        try:
            self.root.after(0, lambda: self.start_capture(hotkey))
        except Exception as e:
            print(f"调度主线程截图失败: {e}")
            self.log(f"调度主线程截图失败: {e}", level='ERROR')
    
    def get_monitors_info(self):
        """获取所有显示器的信息（跨平台）"""
        try:
            return get_monitors_info()
        except Exception as e:
            print(f"获取显示器信息失败: {e}")
            self.log(f"获取显示器信息失败，使用默认值: {e}", level='WARN')
            return [{'index': 0, 'scaling_factor': 1.0, 'width': 1920, 'height': 1080, 'x': 0, 'y': 0}]
    
    def get_monitor_for_position(self, x, y):
        """根据坐标确定对应的显示器"""
        for monitor in self.monitors_info:
            if (monitor['x'] <= x < monitor['x'] + monitor['width'] and 
                monitor['y'] <= y < monitor['y'] + monitor['height']):
                return monitor
        # 如果没找到，返回第一个显示器
        return self.monitors_info[0] if self.monitors_info else {'scaling_factor': 1.0}
    
    def start_hotkey_listener(self):
        # 使用新线程监听全局快捷键
        hotkey_thread = Thread(target=self.listen_hotkey)
        hotkey_thread.daemon = True
        hotkey_thread.start()
        self.hotkey_thread = hotkey_thread
        self.log("热键监听线程已启动。")
    
    def ensure_hotkey_alive(self):
        """周期性检查并自愈热键监听线程"""
        try:
            if not getattr(self, 'hotkey_thread', None) or not self.hotkey_thread.is_alive():
                print("检测到热键线程不在运行，尝试重启...")
                self.log("检测到热键线程不在运行，尝试重启...", level='WARN')
                self.start_hotkey_listener()
        except Exception as e:
            print(f"热键心跳检查异常: {e}")
            self.log(f"热键心跳检查异常: {e}", level='ERROR')
        finally:
            # 5 秒检查一次
            self.root.after(5000, self.ensure_hotkey_alive)
    
    def listen_hotkey(self):
        system_name = platform.system()
        # 优先使用 keyboard 库（更易于在 Windows 上工作）
        if kb is not None and system_name == 'Windows':
            try:
                kb.add_hotkey('ctrl+shift+win', partial(self.trigger_capture_from_hotkey, "ctrl+shift+win"))
                kb.add_hotkey('ctrl+shift+alt', partial(self.trigger_capture_from_hotkey, "ctrl+shift+alt"))
                kb.add_hotkey('ctrl+win+alt', partial(self.trigger_capture_from_hotkey, "ctrl+win+alt"))
                self.log("已注册 keyboard 全局热键。")
                # 保持线程常驻
                while True:
                    time.sleep(1)
                return
            except Exception as e:
                print(f"keyboard 热键注册失败，回退到 pynput: {e}")
                self.log(f"keyboard 热键注册失败，回退到 pynput: {e}", level='WARN')
        
        # 回退到 pynput 的全局热键（跨平台）
        if pynput_keyboard is not None:
            if system_name == 'Darwin':
                mapping = {
                    '<ctrl>+<shift>+<cmd>': partial(self.trigger_capture_from_hotkey, "ctrl+shift+win"),
                    '<ctrl>+<shift>+<alt>': partial(self.trigger_capture_from_hotkey, "ctrl+shift+alt"),
                    '<ctrl>+<alt>+<cmd>': partial(self.trigger_capture_from_hotkey, "ctrl+win+alt"),
                }
            elif system_name == 'Linux':
                mapping = {
                    '<ctrl>+<shift>+<super>': partial(self.trigger_capture_from_hotkey, "ctrl+shift+win"),
                    '<ctrl>+<shift>+<alt>': partial(self.trigger_capture_from_hotkey, "ctrl+shift+alt"),
                    '<ctrl>+<alt>+<super>': partial(self.trigger_capture_from_hotkey, "ctrl+win+alt"),
                }
            else:  # Windows 或其他
                mapping = {
                    '<ctrl>+<shift>+<cmd>': partial(self.trigger_capture_from_hotkey, "ctrl+shift+win"),
                    '<ctrl>+<shift>+<alt>': partial(self.trigger_capture_from_hotkey, "ctrl+shift+alt"),
                    '<ctrl>+<alt>+<cmd>': partial(self.trigger_capture_from_hotkey, "ctrl+win+alt"),
                }
            try:
                hotkeys = pynput_keyboard.GlobalHotKeys(mapping)
                hotkeys.start()
                self.log("已注册 pynput 全局热键。")
                # 保持线程常驻
                hotkeys.join()
                return
            except Exception as e:
                print(f"pynput 热键注册失败: {e}")
                self.log(f"pynput 热键注册失败: {e}", level='ERROR')
        
        print("未能注册全局热键。请使用界面按钮进行截图。")
        self.log("未能注册全局热键，请使用界面按钮进行截图。", level='WARN')
    
    def start_capture(self, hotkey=None):
        # 防止截图过程中重复触发
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
        # 最小化主窗口
        self.root.withdraw()
        self.root.lift()
        self.root.after(500, partial(self.capture_screen, hotkey=hotkey))

    def capture_screen(self, hotkey=None):
        # 获取所有显示器的总尺寸和位置
        self.update_screen_dimensions()
        
        # 创建全屏幕顶级窗口
        self.top = tk.Toplevel(self.root)
        
        # 设置窗口位置和大小，覆盖所有显示器
        self.top.geometry(f"{self.total_width}x{self.total_height}+{self.min_x}+{self.min_y}")
        self.top.attributes('-alpha', 0.3)  # 半透明
        self.top.attributes('-topmost', True)  # 确保窗口始终在最上层
        
        # 移除窗口边框
        self.top.overrideredirect(True)
        
        # 确保键盘焦点与全局事件捕获
        try:
            self.top.focus_force()
            self.top.grab_set()
        except Exception:
            pass
        
        # 创建覆盖所有显示器的Canvas
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
        self.top.bind('<ButtonRelease-1>', partial(self.on_button_release, hotkey))
        
        print(f"创建截图窗口: 位置({self.min_x}, {self.min_y}), 尺寸 {self.total_width}x{self.total_height}")
        self.log(f"创建截图窗口: 位置({self.min_x}, {self.min_y}), 尺寸 {self.total_width}x{self.total_height}", level='DEBUG')
        
        # 添加右键取消功能 - 绑定到窗口和Canvas
        self.top.bind('<Button-3>', lambda e: self.cancel_capture())
        self.canvas.bind('<Button-3>', lambda e: self.cancel_capture())
        self.top.bind('<Escape>', lambda e: self.cancel_capture())
        
        # 添加提示信息
        self.top.bind('<Enter>', lambda e: self.show_cancel_hint())
        self.top.bind('<Leave>', lambda e: self.hide_cancel_hint())
    
    def cancel_capture(self):
        """取消截图"""
        if hasattr(self, 'top'):
            self.top.destroy()
        self.root.deiconify()
        self.label.config(text="截图已取消")
        self.is_capturing = False
        try:
            self.capture_button.config(state='normal')
        except Exception:
            pass
        self.log("截图已取消。")
    
    def show_cancel_hint(self):
        """显示取消提示信息"""
        if hasattr(self, 'top') and self.top.winfo_exists():
            # 在截图窗口上显示提示信息
            if not hasattr(self, 'hint_label'):
                self.hint_label = tk.Label(self.top, text="右键或按ESC取消截图", 
                                         bg='yellow', fg='black', font=('Arial', 12, 'bold'))
                self.hint_label.place(relx=0.5, rely=0.1, anchor='center')
    
    def hide_cancel_hint(self):
        """隐藏取消提示信息"""
        if hasattr(self, 'hint_label') and self.hint_label.winfo_exists():
            self.hint_label.destroy()
            delattr(self, 'hint_label')

    def update_screen_dimensions(self):
        """更新屏幕尺寸信息，支持多显示器"""
        if not hasattr(self, 'monitors_info') or not self.monitors_info:
            self.monitors_info = self.get_monitors_info()
        
        # 计算所有显示器的边界
        min_x = min(monitor['x'] for monitor in self.monitors_info)
        min_y = min(monitor['y'] for monitor in self.monitors_info)
        max_x = max(monitor['x'] + monitor['width'] for monitor in self.monitors_info)
        max_y = max(monitor['y'] + monitor['height'] for monitor in self.monitors_info)
        
        # 总尺寸和偏移
        self.total_width = max_x - min_x
        self.total_height = max_y - min_y
        self.min_x = min_x
        self.min_y = min_y
        
        print(f"屏幕边界: 最小({min_x}, {min_y}), 最大({max_x}, {max_y})")
        print(f"总尺寸: {self.total_width}x{self.total_height}")
        self.log(f"屏幕边界: 最小({min_x}, {min_y}), 最大({max_x}, {max_y}); 总尺寸: {self.total_width}x{self.total_height}", level='DEBUG')
        
        # 更新每个显示器的相对位置
        for monitor in self.monitors_info:
            monitor['relative_x'] = monitor['x'] - min_x
            monitor['relative_y'] = monitor['y'] - min_y
            print(f"显示器 {monitor['index']}: 相对位置({monitor['relative_x']}, {monitor['relative_y']})")

    def on_button_press(self, event):
        self.start_x.set(event.x)
        self.start_y.set(event.y)
        self.rect = self.canvas.create_rectangle(self.start_x.get(), self.start_y.get(), self.start_x.get(), self.start_y.get(), outline='red')

    def on_mouse_drag(self, event):
        self.canvas.coords(self.rect, self.start_x.get(), self.start_y.get(), event.x, event.y)

    def on_button_release(self, hotkey, event):
        end_x = event.x
        end_y = event.y

        # 确保坐标正确
        left = min(self.start_x.get(), end_x)
        top = min(self.start_y.get(), end_y)
        right = max(self.start_x.get(), end_x)
        bottom = max(self.start_y.get(), end_y)
        
        # 将Canvas坐标转换为实际屏幕坐标
        actual_left = left + self.min_x
        actual_top = top + self.min_y
        actual_right = right + self.min_x
        actual_bottom = bottom + self.min_y
        
        print(f"Canvas坐标: ({left}, {top}) 到 ({right}, {bottom})")
        print(f"实际屏幕坐标: ({actual_left}, {actual_top}) 到 ({actual_right}, {actual_bottom})")
        self.log(f"选择区域: Canvas ({left},{top})-({right},{bottom}); 实际 ({actual_left},{actual_top})-({actual_right},{actual_bottom})", level='DEBUG')
        
        # 根据截图位置确定对应的显示器和缩放比例
        monitor = self.get_monitor_for_position(actual_left, actual_top)
        self.scaling_factor = monitor['scaling_factor']
        
        print(f"使用显示器 {monitor['index']}，缩放比例: {self.scaling_factor}")
        self.log(f"使用显示器 {monitor['index']}，缩放比例 {self.scaling_factor}", level='DEBUG')

        self.top.destroy()

        # 计算截图区域（直接使用物理屏幕坐标，不再乘以缩放）
        left = int(actual_left)
        top = int(actual_top)
        right = int(actual_right)
        bottom = int(actual_bottom)
        
        print(f"最终截图区域: ({left}, {top}) 到 ({right}, {bottom})")
        self.log(f"最终截图区域: ({left}, {top}) 到 ({right}, {bottom})", level='DEBUG')

        # 截图
        screenshot = self.screenshot_handler.capture_area(left, top, right, bottom)
        
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
        
        # 保存截图
        screenshot.save("./screenshot.png")
        self.log("已保存临时截图 ./screenshot.png", level='DEBUG')

        # 根据选择的接口确定API地址
        if self.api_var.get() == "standard":
            api_url = "https://server.simpletex.cn/api/latex_ocr"
            print("使用标准接口")
            self.log("使用标准接口 /api/latex_ocr")
        else:
            api_url = "https://server.simpletex.cn/api/latex_ocr_turbo"
            print("使用轻量接口")
            self.log("使用轻量接口 /api/latex_ocr_turbo")
        
        # 关闭img_file
        with open("./screenshot.png", 'rb') as f:
            img_file = {"file": f}
            data = {

            } # 请求参数数据（非文件型参数），视情况填入，可以参考各个接口的参数说明
            header, data = get_req_data(data, SIMPLETEX_APP_ID, SIMPLETEX_APP_SECRET)
            res = requests.post(api_url, files=img_file, data=data, headers=header)
        
        self.log(f"识别请求完成，状态码 {res.status_code}")
        result = json.loads(res.text)
        text = result["res"]["latex"]

        if hotkey == "ctrl+shift+win":
            text = " $" + text + "$ "
        elif hotkey == "ctrl+shift+alt":
            text = "$$\n" + text + "\n$$"
        elif hotkey == "ctrl+win+alt":
            text = " $$" + text.strip() + "$$ "
        else:
            text = text
        
        # 将text复制到系统剪切板
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.root.update()
        print(result)
        self.log("识别完成，结果已复制到剪贴板。", level='SUCCESS')
        # 删除截图文件
        os.remove("./screenshot.png")
        self.log("已删除临时截图文件。", level='DEBUG')

        # 重新显示主窗口
        self.root.deiconify()
        self.label.config(text="截图成功，已复制到剪切板")
        self.is_capturing = False
        try:
            self.capture_button.config(state='normal')
        except Exception:
            pass
        self.log("截图识别流程完成。", level='SUCCESS')
    
    def display_monitor_info(self):
        """显示检测到的显示器信息"""
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
        
        # 计算总屏幕区域
        if len(self.monitors_info) > 1:
            min_x = min(monitor['x'] for monitor in self.monitors_info)
            min_y = min(monitor['y'] for monitor in self.monitors_info)
            max_x = max(monitor['x'] + monitor['width'] for monitor in self.monitors_info)
            max_y = max(monitor['y'] + monitor['height'] for monitor in self.monitors_info)
            total_width = max_x - min_x
            total_height = max_y - min_y
            
            print(f"总屏幕区域: 位置({min_x}, {min_y}), 尺寸{total_width}x{total_height}")
            self.log(f"总屏幕区域: 位置({min_x}, {min_y}), 尺寸{total_width}x{total_height}", level='DEBUG')
        
        # 更新界面标签显示显示器信息
        monitor_text = f"检测到 {len(self.monitors_info)} 个显示器"
        if len(self.monitors_info) > 1:
            monitor_text += f" (主屏缩放: {self.monitors_info[0]['scaling_factor']})"
        self.label.config(text=monitor_text)
    
    def cleanup(self):
        """清理资源"""
        if hasattr(self, 'screenshot_handler'):
            self.screenshot_handler.close()
        self.log("已清理资源，准备退出。")
    
    def __del__(self):
        """析构函数"""
        self.cleanup()

if __name__ == "__main__":
    root = tk.Tk()
    app = ScreenCapture(root)
    
    # 确保程序退出时清理资源
    def on_closing():
        app.cleanup()
        root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()
