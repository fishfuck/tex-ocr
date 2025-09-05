from PIL import Image
import time
import mss


class MultiMonitorScreenshot:
    """多显示器截图处理类（按次创建 mss 以增强稳定性）"""

    def __init__(self, monitors_info):
        self.monitors_info = monitors_info

    def _grab_with_retry(self, region):
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
        pass 