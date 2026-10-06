# -*- coding: utf-8 -*-
"""跨模块共享的运行时状态(窗口句柄、标志位、相关小窗卡片等)。"""
import queue
import threading

win = None          # 主讲解弹窗 (webview.Window)
side = None         # 相关小窗 (webview.Window)
settings_win = None # 键位设置窗 (webview.Window)
api = None          # JS 桥 (bridge.Api)

ready = threading.Event()        # webview GUI 循环已启动
webview_ok = {"v": False}        # WebView2 可用
win_lock = threading.Lock()      # 串行化主弹窗操作(show/hide/move/evaluate_js)
side_win_lock = threading.Lock() # 串行化相关小窗操作
win_visible = {"v": False}       # 主弹窗当前是否可见(自己跟踪,避免重复 show)
has_content = {"v": False}       # 主弹窗是否已有过内容(决定是否放欢迎信息)
side_visible = {"v": False}
fallback_q = queue.Queue()       # 基础模式(无 WebView2)的更新队列

chat_seq = {"v": 0}
chat_lock = threading.Lock()

side_cards = []                  # 相关小窗卡片(最新的在最前)
side_lock = threading.Lock()

region_open = {"v": False}       # 圈选遮罩是否已打开

enabled = {"v": True}            # 点读机开关:暂停后侧键/热键失效并恢复侧键原生功能
tray_icon = None                 # pystray 图标对象(供开关时更新图标/提示)
tray_icons = {}                  # {"on": 蓝色图标, "off": 灰色图标}

mouse_binding = {}               # XBUTTON 编号 -> 触发函数(存在即拦截)
mouse_swallowed = {"v": 0}       # 调试计数
