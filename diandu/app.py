# -*- coding: utf-8 -*-
"""应用装配:命令行入口、窗口创建、输入/托盘线程启动。"""
import sys
import threading
import traceback

try:
    import webview
except Exception:
    webview = None

from . import APP_NAME, __version__
from . import bridge, config, inputs, runtime, trayicon, webui, win32util, windows
from .config import load_config, log_err
from .llm import test_api


def check(cfg):
    """--check:打印配置摘要。"""
    print("%s v%s" % (APP_NAME, __version__))
    print("配置文件 :", config.CONFIG_PATH)
    print("api_base :", cfg["api_base"])
    if cfg.get("api_key"):
        print("api_key  : 已配置(尾号 %s)" % cfg["api_key"][-4:])
    else:
        print("api_key  : 未配置  <- 请编辑 config.json 填入")
    print("text_model   :", cfg["text_model"])
    print("vision_model :", cfg["vision_model"])
    print("鼠标侧键: 侧键1(后退)=%s  侧键2(前进)=%s"
          % (cfg.get("mouse_side1"), cfg.get("mouse_side2")))
    print("热键: 圈选=%s  划词=%s  相关小窗=%s  总开关=%s"
          % (cfg["hotkey_select_region"], cfg["hotkey_copy_text"],
             cfg.get("hotkey_side_window"), cfg.get("hotkey_toggle")))
    print("相关小窗: %s, 自动补充相关内容=%s"
          % ("开启" if cfg.get("side_window", True) else "关闭",
             "是" if cfg.get("auto_related", True) else "否"))


def main(argv=None):
    cfg = load_config()
    win32util.enable_dpi_awareness()
    argv = sys.argv[1:] if argv is None else argv
    if "--version" in argv:
        print("%s v%s" % (APP_NAME, __version__))
        return
    if "--check" in argv:
        check(cfg)
        return
    if "--test-api" in argv:
        test_api(cfg)
        return

    runtime.api = bridge.Api(cfg)

    if webview is not None:
        try:
            runtime.win = webview.create_window(
                APP_NAME, html=webui.MAIN_HTML, js_api=runtime.api,
                width=int(cfg["popup_width"]), height=int(cfg["popup_height"]),
                on_top=True, hidden=True, min_size=(360, 300))
        except Exception:
            runtime.win = None
            log_err("创建窗口失败:\n" + traceback.format_exc())
        try:
            runtime.side = webview.create_window(
                "相关小窗", html=webui.SIDE_HTML, js_api=runtime.api,
                width=int(cfg["side_width"]), height=int(cfg["side_height"]),
                on_top=True, hidden=True, min_size=(280, 240))
        except Exception:
            runtime.side = None
            log_err("创建相关小窗失败:\n" + traceback.format_exc())

    threading.Thread(target=inputs.hotkey_loop, args=(cfg,), daemon=True).start()
    threading.Thread(target=inputs.install_mouse_hooks, args=(cfg,), daemon=True).start()
    trayicon.make_tray(cfg)

    if runtime.win is not None:
        try:
            def on_ready():
                runtime.ready.set()
                runtime.webview_ok["v"] = True
            webview.start(on_ready)
            return
        except Exception:
            runtime.webview_ok["v"] = False
            log_err("WebView 启动失败,回退基础模式:\n" + traceback.format_exc())
    windows.run_fallback_gui(cfg)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        log_err(traceback.format_exc())
        raise
