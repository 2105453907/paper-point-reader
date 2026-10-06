# -*- coding: utf-8 -*-
"""Win32 小工具:DPI 感知、屏幕尺寸、光标位置与弹窗定位。"""
import ctypes
import ctypes.wintypes

_user32 = ctypes.windll.user32


class _POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


def enable_dpi_awareness():
    """让 tkinter / mss / WebView 全部使用物理像素,高分屏下坐标一致。"""
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            _user32.SetProcessDPIAware()
        except Exception:
            pass


def screen_size():
    return _user32.GetSystemMetrics(0), _user32.GetSystemMetrics(1)


def cursor_pos():
    pt = _POINT()
    _user32.GetCursorPos(ctypes.byref(pt))
    return pt.x, pt.y


def popup_pos(w, h):
    """让弹窗尽量贴着光标出现,且完整落在主屏内。"""
    x, y = cursor_pos()
    sw, sh = screen_size()
    x = min(max(0, x + 14), max(0, sw - w - 8))
    y = min(max(0, y - 40), max(0, sh - h - 8))
    return int(x), int(y)
