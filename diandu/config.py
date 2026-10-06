# -*- coding: utf-8 -*-
"""路径、配置加载/保存与错误日志。

源码运行时数据文件在仓库根;PyInstaller 打包后在 exe 同目录(便携使用)。
"""
import json
import os
import shutil
import sys
import traceback
from datetime import datetime

if getattr(sys, "frozen", False):
    APP_DIR = os.path.dirname(os.path.abspath(sys.executable))
else:
    APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CONFIG_PATH = os.path.join(APP_DIR, "config.json")
CONFIG_EXAMPLE = os.path.join(APP_DIR, "config.example.json")
HISTORY_DIR = os.path.join(APP_DIR, "history")
ERR_LOG = os.path.join(APP_DIR, "err.log")
DROP_FILE = os.path.join(APP_DIR, "drop.txt")   # 拖放投递:由新实例写给正在运行的实例

DEFAULT_CONFIG = {
    "api_base": "https://open.bigmodel.cn/api/paas/v4",
    "api_key": "",
    "text_model": "glm-4.6",
    "vision_model": "glm-4.5v",
    "mouse_side1": "region",      # 鼠标侧键1(后退键): region=圈选 / text=划词 / none=不拦截
    "mouse_side2": "text",        # 鼠标侧键2(前进键): 同上
    "hotkey_select_region": "ctrl+alt+q",
    "hotkey_copy_text": "ctrl+alt+e",
    "hotkey_side_window": "ctrl+alt+s",
    "hotkey_toggle": "ctrl+alt+p",
    "hotkey_read_paper": "ctrl+alt+o",   # 通读整篇论文(投递小窗)
    "hotkey_rebuild_tex": "ctrl+alt+l",  # PDF 重建为 LaTeX 并编译
    "read_mode": "auto",                 # auto=能整篇装下就一次读,否则分批 | whole | batch
    "read_context_tokens": 100000,       # 整篇读取的上下文上限(token 估算)
    "read_image_scale": 1.8,             # PDF 页面渲染倍率(越大越清晰、token 越多)
    "read_pages_per_request": 6,         # 分批模式的每批页数
    "read_max_pages": 60,                # 最多读多少页(0=全部)
    "side_window": True,          # 启用「相关小窗」
    "auto_related": True,         # 讲解完成后自动补充"相关概念/前置知识/延伸方向"
    "popup_width": 580,
    "popup_height": 700,
    "side_width": 380,
    "side_height": 680,
    "save_history": True,
    "show_on_start": True,               # 启动时亮出主窗口(显示用法速览)
}


def log_err(text):
    try:
        with open(ERR_LOG, "a", encoding="utf-8") as f:
            f.write("[%s] %s\n" % (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), text))
    except Exception:
        pass


def save_config(cfg):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


def load_config():
    if not os.path.exists(CONFIG_PATH) and os.path.exists(CONFIG_EXAMPLE):
        try:
            shutil.copyfile(CONFIG_EXAMPLE, CONFIG_PATH)
        except Exception:
            pass
    cfg = dict(DEFAULT_CONFIG)
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                user = json.load(f)
            if isinstance(user, dict):
                cfg.update({k: v for k, v in user.items() if v is not None})
        except Exception:
            log_err("config.json 解析失败,使用默认配置\n" + traceback.format_exc())
    else:
        save_config(cfg)
    if not cfg.get("api_key"):
        for env in ("ZHIPUAI_API_KEY", "ZHIPU_API_KEY", "OPENAI_API_KEY"):
            v = os.environ.get(env)
            if v:
                cfg["api_key"] = v
                break
    return cfg
