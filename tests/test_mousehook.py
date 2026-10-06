# -*- coding: utf-8 -*-
"""鼠标侧键钩子自测(仅 Windows,手动运行):

    python tests/test_mousehook.py

合成 XBUTTON1/2 事件,验证:
1. 启用状态:侧键被低级钩子拦截并触发对应流程;
2. 暂停状态(runtime.enabled=False):侧键放行、不吞不触发。
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


def press(btn):
    me(XDOWN, 0, 0, btn, 0)
    me(XUP, 0, 0, btn, 0)


# 1) 启用状态:应拦截并触发
press(1)
time.sleep(0.3)
press(2)
time.sleep(1.2)
enabled_ok = runtime.mouse_swallowed["v"] >= 4 and fired[:2] == ["region", "text"]
print("启用状态: swallowed = %s, fired = %s" % (runtime.mouse_swallowed["v"], fired))

# 2) 暂停状态:应放行(不吞、不触发)
runtime.enabled["v"] = False
swallowed_before, fired_before = runtime.mouse_swallowed["v"], len(fired)
press(1)
time.sleep(0.3)
press(2)
time.sleep(1.0)
disabled_ok = (runtime.mouse_swallowed["v"] == swallowed_before
               and len(fired) == fired_before)
print("暂停状态: swallowed = %s (应不变), fired = %s" % (runtime.mouse_swallowed["v"], fired))
runtime.enabled["v"] = True

ok = enabled_ok and disabled_ok
print("MOUSE-HOOK-TEST:", "PASS" if ok else "FAIL",
      "(测试期间请勿触碰鼠标侧键)")
sys.exit(0 if ok else 1)
