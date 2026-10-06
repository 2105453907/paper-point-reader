# -*- coding: utf-8 -*-
"""输入层:鼠标侧键低级钩子(WH_MOUSE_LL,拦截 XBUTTON)与全局键盘热键。"""
import ctypes
import ctypes.wintypes
import threading
import time
import traceback

import keyboard

from . import actions, runtime, trayicon, windows
from .config import log_err

WH_MOUSE_LL = 14
WM_XBUTTONDOWN = 0x020B
WM_XBUTTONUP = 0x020C
WM_XBUTTONDBLCLK = 0x020D
ULONG_PTR = ctypes.c_size_t
LRESULT = ctypes.c_ssize_t


class MSLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("pt", ctypes.wintypes.POINT),
        ("mouseData", ctypes.wintypes.DWORD),
        ("flags", ctypes.wintypes.DWORD),
        ("time", ctypes.wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


MOUSE_HOOKPROC = ctypes.WINFUNCTYPE(LRESULT, ctypes.c_int, ctypes.c_size_t, ctypes.c_ssize_t)
_user32 = ctypes.windll.user32
_user32.SetWindowsHookExW.restype = ctypes.c_void_p
_user32.SetWindowsHookExW.argtypes = [ctypes.c_int, MOUSE_HOOKPROC, ctypes.c_void_p,
                                      ctypes.wintypes.DWORD]
_user32.CallNextHookEx.restype = LRESULT
_user32.CallNextHookEx.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_size_t,
                                   ctypes.c_ssize_t]

_MouseProc_ref = None  # 防止回调被 GC


def _mouse_hook_proc(n_code, w_param, l_param):
    try:
        if n_code >= 0 and w_param in (WM_XBUTTONDOWN, WM_XBUTTONUP, WM_XBUTTONDBLCLK):
            info = ctypes.cast(l_param, ctypes.POINTER(MSLLHOOKSTRUCT)).contents
            xbtn = (info.mouseData >> 16) & 0xFFFF
            action = runtime.mouse_binding.get(xbtn)
            if action and runtime.enabled["v"]:
                runtime.mouse_swallowed["v"] += 1
                if w_param == WM_XBUTTONDOWN:
                    threading.Thread(target=action, daemon=True).start()
                return 1  # 吞掉,不再执行浏览器后退等原生功能
    except Exception:
        log_err(traceback.format_exc())
    return _user32.CallNextHookEx(None, n_code, w_param, l_param)


def install_mouse_hooks(cfg):
    """按配置接管鼠标侧键;在独立线程安装并泵消息循环。"""
    global _MouseProc_ref
    b1 = str(cfg.get("mouse_side1", "region")).lower()
    b2 = str(cfg.get("mouse_side2", "text")).lower()
    for xbtn, mode in ((1, b1), (2, b2)):
        if mode == "region":
            runtime.mouse_binding[xbtn] = lambda: actions.region_flow(cfg)
        elif mode == "text":
            runtime.mouse_binding[xbtn] = lambda: actions.text_flow(cfg)
    if not runtime.mouse_binding:
        return
    _MouseProc_ref = MOUSE_HOOKPROC(_mouse_hook_proc)
    hook = _user32.SetWindowsHookExW(WH_MOUSE_LL, _MouseProc_ref, None, 0)
    if not hook:
        log_err("鼠标侧键钩子安装失败(错误码 %s),侧键将保留原生功能" % ctypes.GetLastError())
        return
    msg = ctypes.wintypes.MSG()
    while _user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
        _user32.TranslateMessage(ctypes.byref(msg))
        _user32.DispatchMessageW(ctypes.byref(msg))


def hotkey_loop(cfg):
    """注册键盘备用热键(圈选/划词/相关小窗/总开关)。"""
    def trigger(flow):
        def call():
            if runtime.enabled["v"]:
                threading.Thread(target=flow, args=(cfg,), daemon=True).start()
        return call

    try:
        keyboard.add_hotkey(cfg["hotkey_select_region"], trigger(actions.region_flow))
        keyboard.add_hotkey(cfg["hotkey_copy_text"], trigger(actions.text_flow))
        keyboard.add_hotkey(
            cfg.get("hotkey_side_window", "ctrl+alt+s"),
            lambda: threading.Thread(target=windows.toggle_side, daemon=True).start())
        keyboard.add_hotkey(
            cfg.get("hotkey_toggle", "ctrl+alt+p"),
            lambda: threading.Thread(target=trayicon.toggle_enabled, daemon=True).start())
    except Exception:
        log_err("热键注册失败:\n" + traceback.format_exc())
    while True:
        time.sleep(60)
