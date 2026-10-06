# -*- coding: utf-8 -*-
"""系统托盘图标、菜单,以及「启用/暂停点读机」开关。"""
import os
import threading
import traceback

from . import config, runtime, windows
from .config import log_err


def _make_icon(color):
    from PIL import Image, ImageDraw, ImageFont
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([2, 2, 62, 62], radius=14, fill=color)
    try:
        font = ImageFont.truetype("msyh.ttc", 34)
        d.text((32, 34), "读", font=font, fill="white", anchor="mm")
    except Exception:
        d.text((14, 20), "DU", fill="white")
    return img


def toggle_enabled():
    """开关点读机:暂停后侧键恢复浏览器原生功能、讲解热键失效。"""
    runtime.enabled["v"] = not runtime.enabled["v"]
    on = runtime.enabled["v"]
    icon = runtime.tray_icon
    if icon is not None:
        try:
            icon.icon = runtime.tray_icons["on" if on else "off"]
            icon.title = "文献点读机" if on else "文献点读机(已暂停)"
        except Exception:
            log_err("更新托盘图标失败:\n" + traceback.format_exc())
        try:
            if on:
                icon.notify("已启用:侧键1 圈选讲解,侧键2 划词讲解", "文献点读机")
            else:
                icon.notify("已暂停:鼠标侧键恢复后退/前进,讲解热键不再触发", "文献点读机")
        except Exception:
            pass
    return on


def make_tray(cfg):
    try:
        import pystray
    except Exception:
        log_err("托盘模块加载失败:\n" + traceback.format_exc())
        return

    runtime.tray_icons["on"] = _make_icon((37, 99, 235, 255))
    runtime.tray_icons["off"] = _make_icon((156, 163, 175, 255))

    def toggle_window(*a):
        try:
            if runtime.win is not None and runtime.webview_ok["v"]:
                runtime.win.show()
        except Exception:
            pass

    def read_paper(*a):
        from . import document
        threading.Thread(target=document.drop_zone, args=(cfg,), daemon=True).start()

    menu = pystray.Menu(
        pystray.MenuItem("启用点读机", lambda icon, item: toggle_enabled(),
                         checked=lambda item: runtime.enabled["v"]),
        pystray.MenuItem("显示窗口", toggle_window, default=True),
        pystray.MenuItem("通读论文(拖入 / 选择文件)…", read_paper),
        pystray.MenuItem("打开相关小窗", lambda *a: (windows.side_render(), windows.show_side())),
        pystray.MenuItem("打开设置", lambda *a: _startfile(config.CONFIG_PATH)),
        pystray.MenuItem("打开历史记录", lambda *a: (os.makedirs(config.HISTORY_DIR, exist_ok=True),
                                                     _startfile(config.HISTORY_DIR))),
        pystray.MenuItem("退出", lambda icon, item: (icon.stop(), os._exit(0))),
    )
    try:
        icon = pystray.Icon("paper_point_reader", runtime.tray_icons["on"], "文献点读机", menu)
        runtime.tray_icon = icon
        icon.run_detached()
    except Exception:
        log_err("托盘启动失败(不影响使用):\n" + traceback.format_exc())


def _startfile(path):
    try:
        os.startfile(path)
    except Exception:
        pass
