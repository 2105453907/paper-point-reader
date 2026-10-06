# -*- coding: utf-8 -*-
"""两个 WebView 窗口的显示与更新:主讲解弹窗、相关小窗,以及基础模式兜底。"""
import json
import time
import traceback

from . import runtime, win32util
from .config import log_err


def wait_win_ready(win, timeout=10):
    """等页面(含 CDN 脚本)加载完成。"""
    end = time.time() + timeout
    while time.time() < end:
        try:
            if win.evaluate_js("window.__pageReady===true"):
                return True
        except Exception:
            pass
        time.sleep(0.2)
    return True


# ---------------------------------------------------------------- 主弹窗

def popup_show():
    if runtime.webview_ok["v"] and runtime.win is not None:
        try:
            runtime.ready.wait(15)
            wait_win_ready(runtime.win)
            cfg = runtime.api.cfg
            w, h = int(cfg["popup_width"]), int(cfg["popup_height"])
            x, y = win32util.popup_pos(w, h)
            runtime.win.move(x, y)
            runtime.win.show()
        except Exception:
            log_err("popup_show:\n" + traceback.format_exc())
    else:
        runtime.fallback_q.put(("show", None, None))


def popup_new_query(badge, thumb=""):
    popup_show()
    if runtime.webview_ok["v"] and runtime.win is not None:
        try:
            runtime.win.evaluate_js("newQuery(%s, %s)"
                                    % (json.dumps(badge), json.dumps(thumb or "")))
        except Exception:
            log_err("popup_new_query:\n" + traceback.format_exc())
    else:
        runtime.fallback_q.put(("new", badge, thumb))


def popup_update(text, final=False):
    if runtime.webview_ok["v"] and runtime.win is not None:
        try:
            runtime.win.evaluate_js("update(%s, %s)"
                                    % (json.dumps(text or ""), "true" if final else "false"))
        except Exception:
            log_err("popup_update:\n" + traceback.format_exc())
    else:
        runtime.fallback_q.put(("update", text or "", final))


# ---------------------------------------------------------------- 相关小窗

def side_render():
    if runtime.side is None or not runtime.webview_ok["v"]:
        return
    try:
        runtime.ready.wait(15)
        wait_win_ready(runtime.side)
        with runtime.side_lock:
            snapshot = json.dumps(runtime.side_cards, ensure_ascii=True)
        runtime.side.evaluate_js("render(%s)" % snapshot)
    except Exception:
        log_err("side_render:\n" + traceback.format_exc())


def show_side():
    if runtime.side is None or not runtime.webview_ok["v"]:
        return
    try:
        runtime.ready.wait(15)
        wait_win_ready(runtime.side)
        cfg = runtime.api.cfg
        w, h = int(cfg["side_width"]), int(cfg["side_height"])
        sw, sh = win32util.screen_size()
        runtime.side.move(max(0, sw - w - 24), min(90, max(0, sh - h - 8)))
        runtime.side.show()
        runtime.side_visible["v"] = True
    except Exception:
        log_err("show_side:\n" + traceback.format_exc())


def hide_side():
    if runtime.side is None:
        return
    try:
        runtime.side.hide()
    except Exception:
        pass
    runtime.side_visible["v"] = False


def toggle_side():
    if runtime.side is None or not runtime.webview_ok["v"]:
        popup_new_query("相关小窗", "")
        popup_update("WebView2 不可用,相关小窗无法显示。", True)
        return
    if runtime.side_visible["v"]:
        hide_side()
    else:
        side_render()
        show_side()


# ---------------------------------------------------------------- 基础模式兜底

def run_fallback_gui(cfg):
    """WebView2 不可用时的纯 tkinter 兜底:显示纯文本讲解。"""
    import tkinter as tk
    root = tk.Tk()
    root.title("文献点读机(基础模式)")
    root.geometry("%dx%d" % (int(cfg["popup_width"]), int(cfg["popup_height"])))
    tk.Label(root, text="WebView2 不可用,已切换基础模式:公式将以 LaTeX 源码显示",
             fg="#b91c1c", anchor="w").pack(fill="x", padx=6)
    txt = tk.Text(root, wrap="word", font=("Microsoft YaHei", 11))
    txt.pack(fill="both", expand=True)

    def poll():
        try:
            while True:
                kind, a, b = runtime.fallback_q.get_nowait()
                if kind == "show":
                    root.deiconify()
                    root.lift()
                elif kind == "new":
                    root.deiconify()
                    root.lift()
                    root.title("文献点读机 · " + (a or ""))
                    txt.delete("1.0", "end")
                elif kind == "update":
                    txt.delete("1.0", "end")
                    txt.insert("1.0", str(a))
                    if b:
                        txt.see("end")
        except queue.Empty:
            pass
        root.after(200, poll)

    poll()
    root.mainloop()
