# -*- coding: utf-8 -*-
"""鼠标侧键钩子自测(仅 Windows,手动运行):

    python tests/test_mousehook.py

合成 XBUTTON1/2 事件,验证低级钩子拦截侧键并触发对应流程。
测试中圈选/划词流程被替换为计数桩,不会真的弹窗。
"""
import ctypes
import os
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from diandu import actions, inputs, runtime
from diandu.config import load_config

fired = []
actions.region_flow = lambda cfg: fired.append("region")
actions.text_flow = lambda cfg: fired.append("text")

cfg = load_config()
threading.Thread(target=inputs.install_mouse_hooks, args=(cfg,), daemon=True).start()
time.sleep(1.0)

me = ctypes.windll.user32.mouse_event
XDOWN, XUP = 0x0080, 0x0100  # MOUSEEVENTF_XDOWN / XUP;dwData: 1=XBUTTON1, 2=XBUTTON2
me(XDOWN, 0, 0, 1, 0)
me(XUP, 0, 0, 1, 0)
time.sleep(0.3)
me(XDOWN, 0, 0, 2, 0)
me(XUP, 0, 0, 2, 0)
time.sleep(1.5)

print("swallowed =", runtime.mouse_swallowed["v"])
print("fired =", fired)
# 测试期间请勿触碰鼠标侧键;真实侧键按下会产生额外事件,故只校验前两个触发
ok = runtime.mouse_swallowed["v"] >= 4 and fired[:2] == ["region", "text"]
print("MOUSE-HOOK-TEST:", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
