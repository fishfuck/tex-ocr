import platform
from typing import List, Dict

try:
    import mss  # type: ignore
except Exception:
    mss = None  # mss 可能未安装，运行时回退到 tkinter

import tkinter as tk


def get_display_scaling() -> List[float]:
    """跨平台返回每个显示器的缩放比例占位值。
    说明：
    - 为了跨平台稳定，统一返回 1.0（物理像素坐标直接使用）。
    - 若未来需要精确 DPI，可在 Windows 下用 Win32 API 或在 macOS 用 Quartz 扩展。
    """
    try:
        monitors = get_monitors_info()
        return [monitor.get('scaling_factor', 1.0) for monitor in monitors]
    except Exception:
        return [1.0]


def _monitors_from_mss() -> List[Dict]:
    if mss is None:
        raise RuntimeError("mss 未安装")
    with mss.mss() as sct:
        # sct.monitors[0] 是虚拟桌面总体区域；1..n 为各物理显示器
        monitors_info: List[Dict] = []
        for i, mon in enumerate(sct.monitors[1:], start=0):
            monitor_info = {
                'index': i,
                'scaling_factor': 1.0,  # 统一按物理像素处理
                'width': int(mon['width']),
                'height': int(mon['height']),
                'x': int(mon['left']),
                'y': int(mon['top'])
            }
            monitors_info.append(monitor_info)
        if not monitors_info:
            raise RuntimeError("mss 未能枚举显示器")
        return monitors_info


def get_monitors_info_simple() -> List[Dict]:
    """简单回退方案：仅返回主屏信息。"""
    root = tk.Tk()
    root.withdraw()
    try:
        main_width = root.winfo_screenwidth()
        main_height = root.winfo_screenheight()
        return [{
            'index': 0,
            'scaling_factor': 1.0,
            'width': int(main_width),
            'height': int(main_height),
            'x': 0,
            'y': 0,
        }]
    finally:
        try:
            root.destroy()
        except Exception:
            pass


def get_monitors_info() -> List[Dict]:
    """跨平台获取所有显示器的几何信息。
    - 优先使用 mss（Windows/Linux/macOS 均支持）。
    - 失败则回退到 tkinter 单屏方案。
    返回字段：index, scaling_factor, width, height, x, y
    """
    try:
        return _monitors_from_mss()
    except Exception:
        return get_monitors_info_simple()


if __name__ == "__main__":
    print("=== 显示器信息检测 ===")
    print("平台:", platform.system())

    print("\n1. 缩放比例检测:")
    scaling_factors = get_display_scaling()
    for i, scaling_factor in enumerate(scaling_factors):
        print(f"  显示器 {i} 的缩放比例：{scaling_factor}")

    print("\n2. 显示器信息:")
    try:
        monitors = get_monitors_info()
        for monitor in monitors:
            print(
                f"  显示器 {monitor['index']}: 位置({monitor['x']},{monitor['y']}), "
                f"尺寸{monitor['width']}x{monitor['height']}, "
                f"缩放比例{monitor['scaling_factor']}"
            )
    except Exception as e:
        print(f"  获取失败: {e}")
