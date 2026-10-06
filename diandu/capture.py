# -*- coding: utf-8 -*-
"""屏幕圈选(遮罩框选 + mss 截图)与划词(模拟 Ctrl+C 读剪贴板)。"""
import time
import traceback

import keyboard
import mss
import pyperclip
from PIL import Image

from . import win32util
from .config import log_err


def choose_region_blocking():
    """全屏半透明遮罩上拖拽框选;Esc/右键取消;单击=取光标附近一整条。

    返回主屏物理像素矩形 (left, top, width, height),取消返回 None。
    在调用者线程中运行(各自的 tkinter 实例)。
    """
    import tkinter as tk
    result = {"rect": None}
    sw, sh = win32util.screen_size()
    root = tk.Tk()
    root.overrideredirect(True)
    root.geometry("%dx%d+0+0" % (sw, sh))
    root.attributes("-topmost", True)
    root.attributes("-alpha", 0.22)
    root.configure(bg="black", cursor="crosshair")
    cv = tk.Canvas(root, bg="black", highlightthickness=0)
    cv.pack(fill="both", expand=True)
    cv.create_text(sw // 2, 36, text="圈选模式:拖拽框选 · 单击取一整条 · Esc 取消",
                   fill="#22d3ee", font=("Microsoft YaHei", 16))
    sel = {}
    rect_id = [None]

    def press(e):
        sel["x0"], sel["y0"] = e.x_root, e.y_root
        rect_id[0] = cv.create_rectangle(e.x_root, e.y_root, e.x_root, e.y_root,
                                         outline="#22d3ee", width=2)

    def move(e):
        if "x0" in sel:
            cv.coords(rect_id[0], sel["x0"], sel["y0"], e.x_root, e.y_root)

    def release(e):
        x0, y0 = sel.get("x0", e.x_root), sel.get("y0", e.y_root)
        left, top = min(x0, e.x_root), min(y0, e.y_root)
        w, h = abs(e.x_root - x0), abs(e.y_root - y0)
        if w < 6 or h < 6:  # 单击:取光标附近一整条(约一行公式/术语的高度)
            w, h = 640, 200
            left, top = e.x_root - w // 2, e.y_root - h // 2
        left = max(0, min(left, sw - 8))
        top = max(0, min(top, sh - 8))
        w = min(int(w), sw - left)
        h = min(int(h), sh - top)
        result["rect"] = (int(left), int(top), w, h)
        root.destroy()

    def cancel(e):
        root.destroy()

    cv.bind("<ButtonPress-1>", press)
    cv.bind("<B1-Motion>", move)
    cv.bind("<ButtonRelease-1>", release)
    root.bind("<Escape>", cancel)
    root.bind("<Button-3>", cancel)
    root.mainloop()
    return result["rect"]


def grab_region(rect):
    left, top, w, h = rect
    with mss.mss() as sct:
        shot = sct.grab({"left": left, "top": top, "width": w, "height": h})
        return Image.frombytes("RGB", shot.size, shot.rgb)


def get_selected_text():
    """对当前选中内容模拟 Ctrl+C 并读取;结束后恢复用户原剪贴板。"""
    try:
        prev = pyperclip.paste()
    except Exception:
        prev = None
    try:
        pyperclip.copy("")
    except Exception:
        prev = None  # 剪贴板不可写时放弃哨兵与恢复,尽力而为

    text = None
    for i in range(3):
        try:
            keyboard.press_and_release("ctrl+c")
        except Exception:
            log_err("模拟 Ctrl+C 失败\n" + traceback.format_exc())
        time.sleep(0.35 + 0.15 * i)
        try:
            txt = pyperclip.paste()
        except Exception:
            txt = ""
        if txt and txt.strip():
            text = txt.strip()
            break

    if prev is not None:
        try:
            pyperclip.copy(prev)
        except Exception:
            pass
    return text
