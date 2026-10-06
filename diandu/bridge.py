# -*- coding: utf-8 -*-
"""pywebview JS 桥:页面按钮调用的方法(以 python -m webview 的 js_api 暴露)。"""
import os
import threading

import pyperclip

from . import actions, config, prompts, runtime, windows


def _startfile(path):
    try:
        os.startfile(path)
    except Exception:
        pass


class Api:
    def __init__(self, cfg):
        self.cfg = cfg
        self.base_msgs = None      # 本轮问答的原始消息(供「再细讲」续问)
        self.answer = ""           # 最近一次完整讲解(供「复制」)
        self.badge = ""
        self.thumb = ""
        self.card_id = None        # 对应相关小窗里的卡片 id

    # ---- 主弹窗 ----

    def hide(self):
        try:
            runtime.win.hide()
        except Exception:
            pass
        return ""

    def copy_answer(self):
        try:
            pyperclip.copy(self.answer or "")
        except Exception:
            pass
        return ""

    def open_config(self):
        _startfile(config.CONFIG_PATH)
        return ""

    def open_history(self):
        os.makedirs(config.HISTORY_DIR, exist_ok=True)
        _startfile(config.HISTORY_DIR)
        return ""

    def more_detail(self):
        if self.base_msgs:
            msgs = list(self.base_msgs) + [{"role": "user", "content": prompts.MORE_DETAIL_PROMPT}]
            actions.start_chat(self.cfg, msgs, self.badge + " · 细讲", self.thumb,
                               base_msgs=self.base_msgs, update_card=self.card_id)
        return ""

    def read_paper(self):
        from . import document
        threading.Thread(target=document.drop_zone, args=(self.cfg,),
                         daemon=True).start()
        return ""

    # ---- 相关小窗 ----

    def toggle_side(self):
        threading.Thread(target=windows.toggle_side, daemon=True).start()
        return ""

    def side_hide(self):
        threading.Thread(target=windows.hide_side, daemon=True).start()
        return ""

    def side_clear(self):
        with runtime.side_lock:
            del runtime.side_cards[:]
        windows.side_render()
        return ""

    def quit_app(self):
        os._exit(0)
