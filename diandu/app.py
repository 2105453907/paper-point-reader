# -*- coding: utf-8 -*-
"""应用装配:命令行入口、窗口创建、输入/托盘线程启动。"""
import ctypes
import json
import os
import sys
import threading
import time
import traceback

try:
    import webview
except Exception:
    webview = None

from . import APP_NAME, __version__
from . import bridge, config, inputs, runtime, trayicon, webui, win32util, windows
from .config import load_config, log_err
from .llm import test_api

_MUTEX = None  # 命名互斥体句柄,保持存活以标记"已有实例在运行"


def _single_instance_guard():
    """创建命名互斥体;已有实例在运行时返回 False。"""
    global _MUTEX
    ERROR_ALREADY_EXISTS = 183
    _MUTEX = ctypes.windll.kernel32.CreateMutexW(None, False, "PaperPointReader_SingleInstance")
    return ctypes.windll.kernel32.GetLastError() != ERROR_ALREADY_EXISTS


def _notice_already_running():
    try:
        ctypes.windll.user32.MessageBoxTimeoutW(
            0,
            "文献点读机已经在运行啦,请看系统托盘(蓝色“读”图标)。\n"
            "想让它停下:托盘右键「启用点读机」取消勾选,或按 Ctrl+Alt+P。",
            APP_NAME,
            0x40 | 0x10000 | 0x40000,  # 信息图标 | 置前 | 置顶
            0, 8000)                   # 8 秒后自动消失,不挡事
    except Exception:
        pass


def _deliver_drop(path):
    """把拖入的文件路径交给正在运行的实例(写入 drop.txt,由对方拾取)。"""
    try:
        with open(config.DROP_FILE, "w", encoding="utf-8") as f:
            json.dump({"path": os.path.abspath(path), "ts": time.time()}, f)
    except Exception:
        log_err("投递失败:\n" + traceback.format_exc())
        _notice_already_running()


def _start_drop_watcher(cfg):
    """轮询 drop.txt:收到别的实例投递的论文路径就自动开始通读。"""
    def loop():
        from . import document
        while True:
            try:
                if os.path.exists(config.DROP_FILE):
                    time.sleep(0.3)  # 等写入完成
                    with open(config.DROP_FILE, "r", encoding="utf-8") as f:
                        info = json.load(f)
                    os.remove(config.DROP_FILE)
                    path = (info or {}).get("path", "")
                    if path and os.path.isfile(path):
                        document.read_document_flow(cfg, path)
            except Exception:
                log_err("拾取投递失败:\n" + traceback.format_exc())
            time.sleep(1.2)
    threading.Thread(target=loop, daemon=True).start()


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
    print("论文通读: 热键=%s, 模式=%s(上限 %s k tokens), 分批每批 %s 页, 最多 %s 页"
          % (cfg.get("hotkey_read_paper"), cfg.get("read_mode"),
             int(cfg.get("read_context_tokens") or 0) // 1000,
             cfg.get("read_pages_per_request"), cfg.get("read_max_pages")))
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

    # 支持把论文文件直接拖到桌面图标/程序上:python main.py 论文.pdf
    pending_file = None
    for a in argv:
        if os.path.isfile(a) and os.path.splitext(a)[1].lower() in (".pdf", ".tex", ".md", ".txt"):
            pending_file = a
            break

    if not _single_instance_guard():
        if pending_file:                 # 已有实例:把文件投递给它
            _deliver_drop(pending_file)
        else:
            _notice_already_running()
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
    _start_drop_watcher(cfg)
    trayicon.make_tray(cfg)

    if runtime.win is not None:
        try:
            def on_ready():
                runtime.ready.set()
                runtime.webview_ok["v"] = True
                if pending_file:
                    from . import document
                    threading.Thread(target=document.read_document_flow,
                                     args=(cfg, pending_file), daemon=True).start()
            webview.start(on_ready)
            return
        except Exception:
            runtime.webview_ok["v"] = False
            log_err("WebView 启动失败,回退基础模式:\n" + traceback.format_exc())
    if pending_file:
        from . import document
        threading.Thread(target=document.read_document_flow,
                         args=(cfg, pending_file), daemon=True).start()
    windows.run_fallback_gui(cfg)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        log_err(traceback.format_exc())
        raise
