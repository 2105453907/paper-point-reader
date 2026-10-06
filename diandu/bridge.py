# -*- coding: utf-8 -*-
"""pywebview JS 桥:页面按钮调用的方法(以 python -m webview 的 js_api 暴露)。"""
import os
import threading
import traceback

import pyperclip

from . import actions, config, llm, prompts, runtime, windows
from .config import log_err


def _startfile(path):
    try:
        os.startfile(path)
    except Exception:
        pass


class Api:
    def __init__(self, cfg):
        self.cfg = cfg
        self.base_msgs = None      # 本轮问答的原始消息(供「再细讲」与追问续问)
        self.answer = ""           # 最近一次完整回答(供「复制」)
        self.display = ""          # 主弹窗当前显示的完整文本(追问时作为前缀)
        self.badge = ""
        self.thumb = ""
        self.card_id = None        # 对应相关小窗里的卡片 id

    # ---- 主弹窗 ----

    def hide(self):
        with runtime.win_lock:
            try:
                runtime.win.hide()
            except Exception:
                pass
            runtime.win_visible["v"] = False
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

    # ---- 追问:就用户点的地方提自己的问题 ----

    def ask(self, q):
        q = (q or "").strip()
        if q:
            threading.Thread(target=self._ask_bg, args=(q,), daemon=True).start()
        return ""

    def _ask_bg(self, q):
        try:
            cfg = self.cfg
            prefix = self.display or ""
            if self.base_msgs:
                msgs = list(self.base_msgs) + [{"role": "user", "content": q}]
            else:
                msgs = [{"role": "system", "content": prompts.SYSTEM_PROMPT},
                        {"role": "user", "content": q}]
            head = '**<div class="askq">🗨 %s</div>**\n\n' % q
            composed_head = prefix + "\n\n---\n\n" + head if prefix else head

            def on_delta(buf):
                windows.popup_update(composed_head + buf, False)

            def on_done(buf):
                final = composed_head + (buf or "")
                self.display = final
                self.answer = buf or ""
                self.base_msgs = msgs + [{"role": "assistant", "content": buf or ""}]
                windows.popup_update(final, True)
                actions.save_history(cfg, "追问 · " + q[:24], "", buf or "")
                if self.card_id is not None:
                    actions.update_side_card_main(self.card_id, final)

            def on_err(m):
                windows.popup_update(composed_head + "**出错了**\n\n" + m, True)

            llm.chat_stream(cfg, msgs, on_delta, on_done, on_err)
        except Exception:
            log_err(traceback.format_exc())

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
