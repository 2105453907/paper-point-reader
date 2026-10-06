# -*- coding: utf-8 -*-
"""pywebview JS 桥:页面按钮调用的方法(以 python -m webview 的 js_api 暴露)。"""
import os
import re
import threading
import traceback

import pyperclip

from . import actions, config, llm, prompts, runtime, windows
from .config import log_err

_BINDING_SPECS = [
    ("hotkey_select_region", "圈选讲解(与侧键1同款)"),
    ("hotkey_copy_text", "划词讲解(与侧键2同款)"),
    ("hotkey_read_paper", "通读论文(投递小窗)"),
    ("hotkey_rebuild_tex", "重建为 LaTeX"),
    ("hotkey_side_window", "相关小窗 显示/隐藏"),
    ("hotkey_toggle", "启用 / 暂停"),
]
_MOD_KEYS = {"ctrl", "alt", "shift", "windows"}
_NAMED_KEYS = {"space", "tab", "enter", "backspace", "delete", "insert", "home", "end",
               "up", "down", "left", "right", "page up", "page down", "esc"}


def _validate_combo(combo):
    parts = [p for p in combo.split("+") if p]
    if not parts:
        return "组合键为空"
    main = [p for p in parts if p not in _MOD_KEYS]
    if len(main) != 1:
        return "需要且只需一个主键(不能只按修饰键)"
    k = main[0]
    has_mod = any(p in _MOD_KEYS for p in parts)
    if len(k) == 1 and k.isalnum() and not has_mod:
        return "单独一个字符键会干扰打字,请加 Ctrl/Alt/Shift,或改用 F1–F12"
    if len(k) > 1 and k not in _NAMED_KEYS and not re.fullmatch(r"f([1-9]|1\d|2[0-4])", k):
        return "不支持的按键:%s" % k
    return None


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

    # ---- 键位设置 ----

    def _binding_rows(self):
        return [{"action": a, "label": lab, "combo": str(self.cfg.get(a, ""))}
                for a, lab in _BINDING_SPECS]

    def open_settings(self):
        threading.Thread(target=windows.show_settings, daemon=True).start()
        return ""

    def settings_hide(self):
        threading.Thread(target=windows.hide_settings, daemon=True).start()
        return ""

    def get_bindings(self):
        return {"rows": self._binding_rows(),
                "mouse1": str(self.cfg.get("mouse_side1", "region")),
                "mouse2": str(self.cfg.get("mouse_side2", "text"))}

    def begin_record(self):
        """录制新键位期间临时移除全部热键,避免按到旧组合触发动作。"""
        try:
            from . import inputs
            inputs.suspend_hotkeys()
        except Exception:
            log_err(traceback.format_exc())
        return ""

    def cancel_record(self):
        try:
            from . import inputs
            inputs.register_hotkeys(self.cfg)
        except Exception:
            log_err(traceback.format_exc())
        return ""

    def set_binding(self, action, combo):
        from . import inputs
        combo = str(combo or "").strip().lower()
        labels = dict(_BINDING_SPECS)
        if action not in labels:
            return {"ok": False, "msg": "未知动作", "rows": self._binding_rows()}
        err = _validate_combo(combo)
        if err:
            return {"ok": False, "msg": err, "rows": self._binding_rows()}
        for a, lab in _BINDING_SPECS:
            if a != action and str(self.cfg.get(a, "")).lower() == combo:
                return {"ok": False, "msg": "该组合键已被「%s」占用" % lab,
                        "rows": self._binding_rows()}
        old = self.cfg.get(action)
        self.cfg[action] = combo
        failed = inputs.register_hotkeys(self.cfg)
        if action in failed:      # 系统不接受(被占用/保留键) -> 回滚
            self.cfg[action] = old
            inputs.register_hotkeys(self.cfg)
            return {"ok": False, "msg": "系统不接受这个按键组合(可能被其他程序占用)",
                    "rows": self._binding_rows()}
        config.save_config(self.cfg)
        return {"ok": True, "combo": combo, "rows": self._binding_rows()}

    def set_mouse(self, side, mode):
        from . import inputs
        mode = str(mode or "").lower()
        if mode not in ("region", "text", "none"):
            return {"ok": False, "msg": "无效的侧键功能", "rows": self._binding_rows()}
        self.cfg["mouse_side1" if str(side) == "1" else "mouse_side2"] = mode
        config.save_config(self.cfg)
        inputs.rebuild_mouse_bindings(self.cfg)
        return {"ok": True, "rows": self._binding_rows()}

    def reset_bindings(self):
        from . import inputs
        from .config import DEFAULT_CONFIG
        for a, _lab in _BINDING_SPECS:
            if a in DEFAULT_CONFIG:
                self.cfg[a] = DEFAULT_CONFIG[a]
        self.cfg["mouse_side1"] = DEFAULT_CONFIG["mouse_side1"]
        self.cfg["mouse_side2"] = DEFAULT_CONFIG["mouse_side2"]
        inputs.register_hotkeys(self.cfg)
        inputs.rebuild_mouse_bindings(self.cfg)
        config.save_config(self.cfg)
        return {"ok": True, "rows": self._binding_rows()}

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
