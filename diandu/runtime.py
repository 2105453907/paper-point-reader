# -*- coding: utf-8 -*-
"""跨模块共享的运行时状态(窗口句柄、标志位、相关小窗卡片等)。"""
import queue
import threading

win = None          # 主讲解弹窗 (webview.Window)
side = None         # 相关小窗 (webview.Window)
api = None          # JS 桥 (bridge.Api)

ready = threading.Event()        # webview GUI 循环已启动
webview_ok = {"v": False}        # WebView2 可用
side_visible = {"v": False}
fallback_q = queue.Queue()       # 基础模式(无 WebView2)的更新队列

chat_seq = {"v": 0}
chat_lock = threading.Lock()

side_cards = []                  # 相关小窗卡片(最新的在最前)
side_lock = threading.Lock()

region_open = {"v": False}       # 圈选遮罩是否已打开

mouse_binding = {}               # XBUTTON 编号 -> 触发函数(存在即拦截)
mouse_swallowed = {"v": 0}       # 调试计数
