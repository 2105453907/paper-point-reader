# -*- coding: utf-8 -*-
"""点读动作:圈选/划词两条流程、问答编排、相关小窗卡片与历史记录。"""
import base64
import io
import time
import traceback
from datetime import datetime

from PIL import Image

from . import capture, llm, prompts, runtime, windows
from .config import log_err

MAX_CARDS = 30  # 相关小窗最多保留的卡片数(防缩略图积累过大)

# 触发冷却:鼠标侧键连按/键盘热键长按自动连发时,避免多次弹窗互相打断(闪来闪去)
_TRIGGER_TS = {"region": 0.0, "text": 0.0}
TRIGGER_COOLDOWN = 1.0


def _trigger_ok(name):
    now = time.time()
    if now - _TRIGGER_TS[name] < TRIGGER_COOLDOWN:
        return False
    _TRIGGER_TS[name] = now
    return True


def region_flow(cfg):
    """侧键1/热键:遮罩圈选 -> 截图 -> 视觉模型讲解。"""
    if not _trigger_ok("region") or runtime.region_open["v"]:
        return
    runtime.region_open["v"] = True
    try:
        rect = capture.choose_region_blocking()
        if not rect:
            return
        time.sleep(0.25)  # 等遮罩完全消失再截图
        img = capture.grab_region(rect)

        buf = io.BytesIO()
        img.save(buf, "PNG")
        data_url = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()

        small = img.copy()          # 相关小窗用小缩略图,避免卡片体积过大
        small.thumbnail((320, 240))
        sb = io.BytesIO()
        small.convert("RGB").save(sb, "JPEG", quality=60)
        side_url = "data:image/jpeg;base64," + base64.b64encode(sb.getvalue()).decode()

        msgs = [
            {"role": "system", "content": prompts.SYSTEM_PROMPT},
            {"role": "user", "content": [
                {"type": "image_url", "image_url": {"url": data_url}},
                {"type": "text", "text": prompts.REGION_PROMPT},
            ]},
        ]
        start_chat(cfg, msgs, "圈选讲解", data_url,
                   title="截图 · " + datetime.now().strftime("%H:%M"), side_thumb=side_url)
    except Exception:
        log_err(traceback.format_exc())
        windows.popup_update("**出错了**\n\n```\n%s\n```" % traceback.format_exc()[-800:], True)
    finally:
        runtime.region_open["v"] = False


def text_flow(cfg):
    """侧键2/热键:模拟 Ctrl+C 取选中文字 -> 文本模型讲解。"""
    if not _trigger_ok("text"):
        return
    try:
        time.sleep(0.15)
        text = capture.get_selected_text()
        if not text:
            windows.popup_new_query("划词讲解", "")
            windows.popup_update("没有获取到选中的文字。请先在 PDF 里用鼠标选中内容,"
                                 "再按划词热键/侧键。\n\n提示:个别 PDF 禁止复制,这种情况请改用"
                                 "圈选(侧键1 或 Ctrl+Alt+Q)框选后讲解。", True)
            return
        msgs = [
            {"role": "system", "content": prompts.SYSTEM_PROMPT},
            {"role": "user", "content": prompts.TEXT_PROMPT.format(text=text[:4000])},
        ]
        start_chat(cfg, msgs, "划词讲解", "",
                   title=text[:38], source_note=text[:1500])
    except Exception:
        log_err(traceback.format_exc())


def start_chat(cfg, msgs, badge, thumb="", base_msgs=None, title="", source_note="",
               side_thumb="", update_card=None):
    """发起一次问答:弹窗流式显示,完成后写入相关小窗与历史。"""
    with runtime.chat_lock:
        runtime.chat_seq["v"] += 1
        seq = runtime.chat_seq["v"]

    def guard(fn):
        """只让最新一次问答更新界面,避免并发串台。"""
        def call(*a):
            if runtime.chat_seq["v"] == seq:
                fn(*a)
        return call

    api = runtime.api
    api.base_msgs = base_msgs or msgs
    api.badge = badge
    api.thumb = thumb
    api.card_id = update_card if update_card is not None else seq
    api.display = ""            # 新一轮点读:追问前缀清零
    windows.popup_new_query(badge, thumb)

    def on_done(buf):
        api.answer = buf
        api.display = buf
        windows.popup_update(buf, True)
        save_history(cfg, badge, thumb, buf)
        if update_card is not None and update_side_card_main(update_card, buf):
            pass
        else:
            add_card(cfg, seq, title or badge, side_thumb, buf, source_note)

    llm.chat_stream(cfg, msgs,
                    guard(lambda buf: windows.popup_update(buf, False)),
                    guard(on_done),
                    guard(lambda msg: windows.popup_update("**出错了**\n\n" + msg, True)))


# ---------------------------------------------------------------- 相关小窗卡片

def add_card(cfg, card_id, title, thumb, main_md, source_note, auto_related=None):
    if runtime.side is None or not cfg.get("side_window", True):
        return
    card = {"id": card_id, "title": title, "time": datetime.now().strftime("%H:%M"),
            "thumb": thumb, "main": main_md, "related": "", "related_pending": False}
    with runtime.side_lock:
        runtime.side_cards.insert(0, card)
        del runtime.side_cards[MAX_CARDS:]
    do_rel = cfg.get("auto_related", True) if auto_related is None else auto_related
    if do_rel:
        fetch_related(cfg, card, source_note)
    windows.side_render()
    if not runtime.side_visible["v"]:
        windows.show_side()


def update_side_card_main(card_id, main_md):
    """「再细讲」更新已有卡片而非新建。"""
    with runtime.side_lock:
        card = next((c for c in runtime.side_cards if c["id"] == card_id), None)
        if card is None:
            return False
        card["main"] = main_md
    windows.side_render()
    return True


def fetch_related(cfg, card, source_note):
    """讲解完成后,补充相关概念/前置知识/延伸方向/检索关键词。"""
    card["related_pending"] = True
    windows.side_render()
    ctx = ""
    if source_note:
        ctx += "我在论文中遇到的内容:\n" + str(source_note)[:1200] + "\n\n"
    ctx += "助手刚才给出的讲解:\n" + (card["main"] or "")[:3000] + "\n\n" + prompts.RELATED_PROMPT
    msgs = [{"role": "system", "content": prompts.SYSTEM_PROMPT},
            {"role": "user", "content": ctx}]

    def done(b):
        card["related"] = (b or "").strip() or "*(未获取到相关内容)*"
        card["related_pending"] = False
        windows.side_render()

    def err(m):
        card["related"] = "*(相关内容获取失败)*"
        card["related_pending"] = False
        windows.side_render()

    llm.chat_stream(cfg, msgs, lambda b: None, done, err)


# ---------------------------------------------------------------- 历史记录

def save_history(cfg, badge, thumb, answer):
    if not cfg.get("save_history") or not answer:
        return
    try:
        import os
        os.makedirs(config_history_dir(), exist_ok=True)
        path = os.path.join(config_history_dir(),
                            datetime.now().strftime("%Y-%m-%d") + ".md")
        with open(path, "a", encoding="utf-8") as f:
            f.write("\n\n---\n\n## %s · %s\n\n" % (datetime.now().strftime("%H:%M"), badge))
            if thumb:
                f.write("*(截图讲解)*\n\n")
            f.write(answer.strip() + "\n")
    except Exception:
        log_err(traceback.format_exc())


def config_history_dir():
    from .config import HISTORY_DIR
    return HISTORY_DIR
