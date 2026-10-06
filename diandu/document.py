# -*- coding: utf-8 -*-
"""论文通读:把整篇论文(PDF / LaTeX / Markdown / 文本)交给大模型,
产出「公式清单 + 每个符号的含义 + 公式的作用」,并汇总符号总表。

读取策略(config.read_mode):
  auto : 估算 token 能装进 read_context_tokens(默认 10 万)就整篇一次读,
         装不下自动分批(整篇读取若被模型拒绝也会自动降级分批);
  whole: 总是整篇一次读;
  batch: 总是分批读。

PDF 走「整页截图 -> 视觉模型」,公式原样进模型,不依赖 PDF->LaTeX 转换;
.tex 源码直读时公式质量最高(arXiv 等可直接下载源码)。
"""
import base64
import io
import os
import re
import threading
import time
import traceback
from datetime import datetime

from . import actions, llm, prompts, runtime, win32util, windows
from .config import HISTORY_DIR, log_err

SUPPORTED = (".pdf", ".tex", ".md", ".txt")
BATCH_TIMEOUT = 1200     # 单次请求最长等待(秒);整篇一次读可能较久
TEXT_CHUNK_SIZE = 24000  # 分批模式的文本块大小(字符)

_READING = {"v": False}  # 通读进行中标记(避免并发通读互相打断)


# ---------------------------------------------------------------- 入口

def pick_file():
    """弹系统文件选择框(独立 tk 实例,可在工作线程中调用)。"""
    import tkinter as tk
    from tkinter import filedialog
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    path = filedialog.askopenfilename(
        title="选择论文文件(PDF / LaTeX / Markdown / 文本)",
        filetypes=[("论文文件", "*.pdf *.tex *.md *.txt"), ("所有文件", "*.*")])
    root.destroy()
    return path or None


def read_paper_dialog(cfg):
    """入口:选文件后通读。"""
    path = pick_file()
    if path:
        read_document_flow(cfg, path)


def drop_zone(cfg):
    """投递小窗:把论文文件拖进来即开始通读(拖放不可用时退回文件选择框)。"""
    try:
        from tkinterdnd2 import DND_FILES, TkinterDnD
    except Exception:
        read_paper_dialog(cfg)
        return
    import tkinter as tk

    root = TkinterDnD.Tk()
    root.title("投递论文")
    W, H = 460, 268
    sw, sh = win32util.screen_size()
    root.geometry("%dx%d+%d+%d" % (W, H, (sw - W) // 2, (sh - H) // 2))
    root.attributes("-topmost", True)
    root.configure(bg="#0b3a8c")

    cv = tk.Canvas(root, width=W, height=H, highlightthickness=0, bg="#0b3a8c")
    cv.pack(fill="both", expand=True)

    # 深海蓝 -> 亮蓝 垂直渐变
    c1, c2 = (11, 58, 140), (29, 78, 216)
    for y in range(H):
        t = y / max(1, H - 1)
        cv.create_line(0, y, W, y, fill="#%02x%02x%02x" % (
            int(c1[0] + (c2[0] - c1[0]) * t),
            int(c1[1] + (c2[1] - c1[1]) * t),
            int(c1[2] + (c2[2] - c1[2]) * t)))

    def round_rect(x1, y1, x2, y2, r, **kw):
        pts = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2,
               x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
        return cv.create_polygon(pts, smooth=True, **kw)

    pad = 22
    card = round_rect(pad, pad, W - pad, H - pad, 20, fill="#ffffff", outline="")

    cv.create_text(W / 2, pad + 52, text="🐋  鲸鲸报点读机 · 通读",
                   font=("Microsoft YaHei UI", 13, "bold"), fill="#0b3a8c")
    cv.create_text(W / 2, pad + 88, text="把论文拖到这里,自动通读全文",
                   font=("Microsoft YaHei UI", 15, "bold"), fill="#1b2430")
    cv.create_text(W / 2, pad + 118, text="支持 PDF / .tex / .md / .txt · 也可直接拖到桌面图标上",
                   font=("Microsoft YaHei UI", 9), fill="#64748b")

    def make_button(cx, cy, bw, bh, text, base, hover, fg, cmd):
        x1, y1, x2, y2 = cx - bw / 2, cy - bh / 2, cx + bw / 2, cy + bh / 2
        rr = round_rect(x1, y1, x2, y2, bh / 2, fill=base, outline="")
        label = cv.create_text(cx, cy, text=text, font=("Microsoft YaHei UI", 10), fill=fg)
        for item in (rr, label):
            cv.tag_bind(item, "<Enter>", lambda e: cv.itemconfig(rr, fill=hover))
            cv.tag_bind(item, "<Leave>", lambda e: cv.itemconfig(rr, fill=base))
            cv.tag_bind(item, "<Button-1>", lambda e: cmd())

    by = H - pad - 42
    make_button(W / 2 - 62, by, 132, 34, "选择文件…", "#2563eb", "#1d4ed8", "#ffffff",
                lambda: (root.destroy(), read_paper_dialog(cfg)))
    make_button(W / 2 + 76, by, 96, 34, "取消", "#eef2f7", "#dbe3ee", "#475569", root.destroy)

    def on_drop(e):
        try:
            paths = root.tk.splitlist(e.data)
        except Exception:
            paths = [str(e.data).strip("{}")]
        root.destroy()
        if paths:
            threading.Thread(target=read_document_flow, args=(cfg, paths[0]),
                             daemon=True).start()

    root.drop_target_register(DND_FILES)
    root.dnd_bind("<<Drop>>", on_drop)
    try:   # 拖入时给卡片描边高亮
        root.dnd_bind("<<DropEnter>>", lambda e: cv.itemconfig(card, outline="#0ea5e9", width=3))
        root.dnd_bind("<<DropLeave>>", lambda e: cv.itemconfig(card, outline="", width=0))
    except Exception:
        pass
    root.bind("<Escape>", lambda e: root.destroy())
    root.mainloop()


# ---------------------------------------------------------------- 文件解析与读取方案

def _pdf_pages(path, cfg):
    """渲染 PDF 页面为图片,并估算每页 token。返回 (pages, total, limit, thumb)。"""
    import pypdfium2 as pdfium
    doc = pdfium.PdfDocument(path)
    try:
        total = len(doc)
        max_pages = int(cfg.get("read_max_pages") or 0)
        limit = min(total, max_pages) if max_pages > 0 else total
        scale = float(cfg.get("read_image_scale") or 1.8)
        pages = []
        thumb = ""
        for i in range(limit):
            pil = doc[i].render(scale=scale).to_pil().convert("RGB")
            if i == 0:
                small = pil.copy()
                small.thumbnail((320, 460))
                sb = io.BytesIO()
                small.save(sb, "JPEG", quality=70)
                thumb = "data:image/jpeg;base64," + base64.b64encode(sb.getvalue()).decode()
            buf = io.BytesIO()
            pil.save(buf, "JPEG", quality=82)
            pages.append({
                "url": "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode(),
                "tokens": (pil.width * pil.height) // 750,
            })
        return pages, total, limit, thumb
    finally:
        doc.close()


def _pdf_plan(pages, total, limit, cfg, force_batch=False):
    ctx = int(cfg.get("read_context_tokens") or 100000)
    mode = str(cfg.get("read_mode") or "auto").lower()
    est = sum(p["tokens"] for p in pages)
    whole = (not force_batch) and (mode == "whole" or (mode == "auto" and est <= ctx))
    if whole:
        label = ("全文共 %d 页" % limit) if limit == total \
            else ("全文前 %d 页(共 %d 页)" % (limit, total))
        chunks = [{"label": label, "images": [p["url"] for p in pages], "whole": True}]
        info = "PDF · 共 %d 页(通读 %d 页) · 整篇一次读取(约 %d k tokens)" % (total, limit, est // 1000)
    else:
        per = max(1, int(cfg.get("read_pages_per_request") or 6))
        chunks = []
        for start in range(0, limit, per):
            end = min(start + per, limit)
            chunks.append({"label": "第 %d-%d 页" % (start + 1, end),
                           "images": [pages[i]["url"] for i in range(start, end)]})
        info = "PDF · 共 %d 页(通读 %d 页) · 分 %d 批读取" % (total, limit, len(chunks))
    return chunks, info


def _read_text(path):
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        text = f.read()
    if path.lower().endswith(".tex"):
        text = re.sub(r"(?<!\\)%.*", "", text)      # 去 LaTeX 注释
        text = re.sub(r"\n{3,}", "\n\n", text)
    return text


def _text_plan(text, cfg, force_batch=False):
    ctx = int(cfg.get("read_context_tokens") or 100000)
    mode = str(cfg.get("read_mode") or "auto").lower()
    est = len(text) // 3          # 英文约 3 字符/token 的保守估算
    whole = (not force_batch) and (mode == "whole" or (mode == "auto" and est <= ctx))
    if whole:
        chunks = [{"label": "全文", "text": text, "whole": True}]
        info = "文本 · %d 字符 · 整篇一次读取(约 %d k tokens)" % (len(text), est // 1000)
    else:
        chunks = []
        i, part, n = 0, 1, len(text)
        while i < n and part <= 20:
            j = min(i + TEXT_CHUNK_SIZE, n)
            if j < n:
                k = text.rfind("\n\n", i + TEXT_CHUNK_SIZE // 2, j)
                if k > 0:
                    j = k
            chunks.append({"label": "第 %d 段" % part, "text": text[i:j]})
            i = j
            part += 1
        info = "文本 · %d 字符 · 分 %d 批读取" % (n, len(chunks))
    return chunks, info


def _batch_messages(mode, ck):
    whole = bool(ck.get("whole"))
    if mode == "images":
        content = [{"type": "image_url", "image_url": {"url": u}} for u in ck["images"]]
        tpl = prompts.READ_WHOLE_PROMPT_IMAGE if whole else prompts.READ_BATCH_PROMPT_IMAGE
        content.append({"type": "text", "text": tpl.format(label=ck["label"])})
    else:
        tpl = prompts.READ_WHOLE_PROMPT_TEXT if whole else prompts.READ_BATCH_PROMPT_TEXT
        content = tpl.format(label=ck["label"], text=ck["text"])
    return [{"role": "system", "content": prompts.SYSTEM_PROMPT},
            {"role": "user", "content": content}]


# ---------------------------------------------------------------- 流程

def _chat_sync(cfg, msgs):
    """同步等待一次完整回答;流式内容显示在主弹窗。失败返回 None。"""
    done = threading.Event()
    box = {"text": None, "err": None}

    def on_delta(b):
        windows.popup_update(b, False)

    def on_done(b):
        box["text"] = b
        done.set()

    def on_err(m):
        box["err"] = m
        done.set()

    llm.chat_stream(cfg, msgs, on_delta, on_done, on_err)
    if not done.wait(BATCH_TIMEOUT):
        return None
    if box["err"]:
        log_err("论文通读请求失败: " + str(box["err"])[:500])
        return None
    return box["text"]


def read_document_flow(cfg, path):
    """通读整篇文档:整篇一次读(可装下时)或分批 -> 写入相关小窗与 history。"""
    if _READING["v"]:
        windows.popup_new_query("论文通读", "")
        windows.popup_update("正在通读另一篇论文,请等它读完再投递。", True)
        return None
    _READING["v"] = True
    try:
        path = os.path.abspath(path)
        if not os.path.isfile(path):
            windows.popup_new_query("论文通读", "")
            windows.popup_update("找不到文件:\n\n`%s`" % path, True)
            return None
        name = os.path.basename(path)
        ext = os.path.splitext(path)[1].lower()
        if ext not in SUPPORTED:
            windows.popup_new_query("论文通读", "")
            windows.popup_update("暂不支持 %s 格式,目前支持 PDF / .tex / .md / .txt。" % ext, True)
            return None

        windows.popup_new_query("论文通读 · " + name, "")
        windows.popup_update("正在解析文件…", False)

        if ext == ".pdf":
            pages, total, limit, thumb = _pdf_pages(path, cfg)
            mode = "images"
            plan = lambda fb: _pdf_plan(pages, total, limit, cfg, fb)
        else:
            text = _read_text(path)
            mode = "text"
            plan = lambda fb: _text_plan(text, cfg, fb)

        chunks, info = plan(False)
        if not chunks:
            windows.popup_update("文件里没有可读内容。", True)
            return None

        whole = bool(chunks[0].get("whole"))
        attempt = 0
        results = []
        while True:
            attempt += 1
            n = len(chunks)
            results = []
            failed = 0
            for idx, ck in enumerate(chunks, 1):
                windows.popup_new_query("论文通读 · %s (%d/%d)" % (name, idx, n), "")
                windows.popup_update("正在阅读 %s …" % ck["label"], False)
                out = _chat_sync(cfg, _batch_messages(mode, ck))
                if out is None:
                    time.sleep(1.5)
                    out = _chat_sync(cfg, _batch_messages(mode, ck))
                if out is None:
                    failed += 1
                results.append("## %s\n\n%s" % (ck["label"], out or "*(本部分解析失败)*"))
            if whole and failed and attempt == 1:
                # 整篇一次读失败(可能超出模型上下文/图片数限制)-> 自动降级分批
                log_err("整篇读取失败,自动降级为分批模式")
                windows.popup_update("整篇一次读取未成功,自动改为分批读取…", False)
                chunks, info = plan(True)
                whole = False
                continue
            break

        joined = "\n\n".join(results)
        if whole:
            full = ("# 论文通读:《%s》\n\n> %s · %s\n\n%s"
                    % (name, info, datetime.now().strftime("%Y-%m-%d %H:%M"), joined))
        else:
            body = joined if len(joined) <= 26000 \
                else joined[:26000] + "\n\n*(此处截断,完整内容见历史文件)*"
            windows.popup_new_query("论文通读 · %s (汇总)" % name, "")
            windows.popup_update("正在汇总符号总表…", False)
            final = _chat_sync(cfg, [
                {"role": "system", "content": prompts.SYSTEM_PROMPT},
                {"role": "user", "content": prompts.READ_FINAL_PROMPT.format(name=name)
                                           + "\n\n" + body},
            ])
            full = ("# 论文通读:《%s》\n\n> %s · 共 %d 批 · %s\n\n"
                    "## 总览\n\n%s\n\n---\n\n# 分批细读\n\n%s"
                    % (name, info, len(chunks), datetime.now().strftime("%Y-%m-%d %H:%M"),
                       final or "*(汇总失败)*", joined))

        windows.popup_update(full, True)
        saved = _save_reading(name, full)
        shown = full
        if saved:
            shown = full + "\n\n---\n\n*(完整结果已保存:%s,并已放入「相关小窗」)*" % saved
            windows.popup_update(shown, True)
        cid = int(time.time()) % 1000000
        actions.add_card(cfg, cid, "📄 " + name, thumb, full, "", auto_related=False)
        api = runtime.api
        if api is not None:   # 通读完成后可直接在输入框里追问整篇论文
            api.display = shown
            api.card_id = cid
            api.base_msgs = [
                {"role": "system", "content": prompts.SYSTEM_PROMPT},
                {"role": "user", "content":
                 "下面是我对论文《%s》的通读报告,请基于它回答我接下来的问题:\n\n%s"
                 % (name, full[:20000])}]
        return full
    except Exception:
        log_err(traceback.format_exc())
        windows.popup_update("**通读失败**\n\n```\n%s\n```" % traceback.format_exc()[-600:], True)
        return None
    finally:
        _READING["v"] = False


def _save_reading(name, full):
    try:
        os.makedirs(HISTORY_DIR, exist_ok=True)
        base = os.path.splitext(name)[0]
        path = os.path.join(HISTORY_DIR, "通读-%s-%s.md"
                            % (base, datetime.now().strftime("%Y%m%d-%H%M")))
        with open(path, "w", encoding="utf-8") as f:
            f.write(full)
        return path
    except Exception:
        log_err(traceback.format_exc())
        return None
