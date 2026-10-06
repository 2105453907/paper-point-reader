# -*- coding: utf-8 -*-
"""系统托盘图标与菜单。"""
import os
import traceback

from . import config, runtime, windows


def make_tray(cfg):
    try:
        import pystray
        from PIL import Image, ImageDraw, ImageFont
    except Exception:
        log_err_local("托盘模块加载失败:\n" + traceback.format_exc())
        return

    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([2, 2, 62, 62], radius=14, fill=(37, 99, 235, 255))
    try:
        font = ImageFont.truetype("msyh.ttc", 34)
        d.text((32, 34), "读", font=font, fill="white", anchor="mm")
    except Exception:
        d.text((14, 20), "DU", fill="white")

    def toggle(*a):
        try:
            if runtime.win is not None and runtime.webview_ok["v"]:
                runtime.win.show()
        except Exception:
            pass

    menu = pystray.Menu(
        pystray.MenuItem("显示窗口", toggle, default=True),
        pystray.MenuItem("打开相关小窗", lambda *a: (windows.side_render(), windows.show_side())),
        pystray.MenuItem("打开设置", lambda *a: _startfile(config.CONFIG_PATH)),
        pystray.MenuItem("打开历史记录", lambda *a: (os.makedirs(config.HISTORY_DIR, exist_ok=True),
                                                     _startfile(config.HISTORY_DIR))),
        pystray.MenuItem("退出", lambda icon, item: (icon.stop(), os._exit(0))),
    )
    try:
        icon = pystray.Icon("paper_point_reader", img, "文献点读机", menu)
        icon.run_detached()
    except Exception:
        log_err_local("托盘启动失败(不影响使用):\n" + traceback.format_exc())


def _startfile(path):
    try:
        os.startfile(path)
    except Exception:
        pass


def log_err_local(text):
    from .config import log_err
    log_err(text)
