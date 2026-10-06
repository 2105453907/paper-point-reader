# -*- coding: utf-8 -*-
"""两个 WebView 窗口的显示与更新:主讲解弹窗、相关小窗,以及基础模式兜底。

窗口操作全部串行化(win_lock / side_win_lock),并用 win_visible 自行跟踪可见性。
原因:pywebview 的 WinForms 实现里 move() 走 SetWindowPos(..., SWP_SHOWWINDOW),
本身就会显示窗口;若并发线程反复 move/show 会互相打架,表现为窗口"闪来闪去"、
甚至看起来打不开。这里保证:已可见就不再重复 move/show。
"""
import json
import queue
import time
import traceback

from . import APP_NAME, runtime, win32util
from .config import log_err

WELCOME = (
    "**点读机已就绪**\n\n"
    "- 鼠标**侧键1**:圈选公式/图表/术语讲解;鼠标**侧键2**:划词讲解\n"
    "- `Ctrl+Alt+O` 通读整篇论文(拖文件进小窗) · `Ctrl+Alt+L` PDF 重建为 LaTeX\n"
    "- `Ctrl+Alt+S` 相关小窗 · `Ctrl+Alt+P` 启用/暂停 · `Esc` 隐藏本窗口\n\n"
    "按一下侧键,或把论文拖到桌面图标上即可开始。"
)


def wait_win_ready(win, timeout=10):
    """等页面(含 CDN 脚本)加载完成。须在对应窗口锁内调用。"""
    end = time.time() + timeout
    while time.time() < end:
        try:
            if win.evaluate_js("window.__pageReady===true"):
                return True
        except Exception:
            pass
        time.sleep(0.2)
    return True


def _win_eval(script):
    with runtime.win_lock:
        runtime.win.evaluate_js(script)


# ---------------------------------------------------------------- 主弹窗

def popup_show():
    if not (runtime.webview_ok["v"] and runtime.win is not None):
        runtime.fallback_q.put(("show", None, None))
        return
    with runtime.win_lock:
        if runtime.win_visible["v"]:
            return  # 已可见:绝不重复 move/show,杜绝闪动
        try:
            runtime.ready.wait(15)
            wait_win_ready(runtime.win)
            cfg = runtime.api.cfg
            w, h = int(cfg["popup_width"]), int(cfg["popup_height"])
            x, y = win32util.popup_pos(w, h)
            runtime.win.move(x, y)   # move 自带 SWP_SHOWWINDOW:先定位、再激活
            runtime.win.show()
            runtime.win_visible["v"] = True
        except Exception:
            log_err("popup_show:\n" + traceback.format_exc())


def popup_new_query(badge, thumb=""):
    """先写好内容(隐藏状态也能写),再显示窗口:避免旧内容一闪而过。"""
    if runtime.webview_ok["v"] and runtime.win is not None:
        try:
            runtime.ready.wait(15)
            _win_eval("newQuery(%s, %s)" % (json.dumps(badge), json.dumps(thumb or "")))
            runtime.has_content["v"] = True
        except Exception:
            log_err("popup_new_query:\n" + traceback.format_exc())
    else:
        runtime.fallback_q.put(("new", badge, thumb))
    popup_show()


def popup_update(text, final=False):
    if runtime.webview_ok["v"] and runtime.win is not None:
        try:
            _win_eval("update(%s, %s)" % (json.dumps(text or ""), "true" if final else "false"))
            runtime.has_content["v"] = True
        except Exception:
            log_err("popup_update:\n" + traceback.format_exc())
    else:
        runtime.fallback_q.put(("update", text or "", final))


def force_show_popup(ensure_welcome=True):
    """把主弹窗强制带到前台(双击图标/托盘用);空窗口时放一张欢迎卡。"""
    if not (runtime.webview_ok["v"] and runtime.win is not None):
        return
    with runtime.win_lock:
        try:
            runtime.win.hide()
        except Exception:
            pass
        runtime.win_visible["v"] = False
    if ensure_welcome and not runtime.has_content["v"]:
        popup_new_query(APP_NAME, "")
        popup_update(WELCOME, True)
    else:
        popup_show()


# ---------------------------------------------------------------- 相关小窗

def side_render():
    if runtime.side is None or not runtime.webview_ok["v"]:
        return
    try:
        with runtime.side_win_lock:
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
    with runtime.side_win_lock:
        if runtime.side_visible["v"]:
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
    with runtime.side_win_lock:
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
    root.title(APP_NAME + "(基础模式)")
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
                    root.title(APP_NAME + " · " + (a or ""))
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
