# -*- coding: utf-8 -*-
"""论文通读:把整篇论文(PDF / LaTeX / Markdown / 文本)交给大模型,
逐部分产出「公式清单 + 每个符号的含义 + 公式的作用」,最后汇总符号总表。

PDF 走「整页截图 -> 视觉模型」路线:公式原样进模型,不依赖 PDF->LaTeX 转换;
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

from . import actions, llm, prompts, runtime, windows
from .config import HISTORY_DIR, log_err

SUPPORTED = (".pdf", ".tex", ".md", ".txt")
BATCH_TIMEOUT = 900      # 单批最长等待(秒)
TEXT_CHUNK_SIZE = 24000  # 文本分块大小(字符)


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


# ---------------------------------------------------------------- 文件解析

def _pdf_chunks(path, cfg):
    """PDF -> 分批的页面截图(每批 read_pages_per_request 页)。"""
    import pypdfium2 as pdfium
    doc = pdfium.PdfDocument(path)
    total = len(doc)
    max_pages = int(cfg.get("read_max_pages") or 0)
    limit = min(total, max_pages) if max_pages > 0 else total
    per = max(1, int(cfg.get("read_pages_per_request") or 3))
    chunks = []
    thumb = ""
    for start in range(0, limit, per):
        end = min(start + per, limit)
        images = []
        for i in range(start, end):
            pil = doc[i].render(scale=2.0).to_pil().convert("RGB")
            if i == 0 and not thumb:
                small = pil.copy()
                small.thumbnail((320, 460))
                sb = io.BytesIO()
                small.save(sb, "JPEG", quality=70)
                thumb = "data:image/jpeg;base64," + base64.b64encode(sb.getvalue()).decode()
            buf = io.BytesIO()
            pil.save(buf, "JPEG", quality=82)
            images.append("data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode())
        if end == limit and limit < total:
            label = "第 %d-%d 页(全文共 %d 页,本次通读前 %d 页)" % (start + 1, end, total, limit)
        else:
            label = "第 %d-%d 页" % (start + 1, end) if per > 1 else "第 %d 页" % (start + 1)
        chunks.append({"label": label, "images": images})
    doc.close()
    info = "PDF · 共 %d 页(通读 %d 页)" % (total, limit)
    return chunks, info, thumb


def _text_chunks(path):
    """LaTeX / Markdown / 文本 -> 按段落边界分块。"""
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        text = f.read()
    if path.lower().endswith(".tex"):
        text = re.sub(r"(?<!\\)%.*", "", text)      # 去 LaTeX 注释
        text = re.sub(r"\n{3,}", "\n\n", text)
    n = len(text)
    chunks = []
    i = 0
    part = 1
    while i < n and part <= 20:
        j = min(i + TEXT_CHUNK_SIZE, n)
        if j < n:
            k = text.rfind("\n\n", i + TEXT_CHUNK_SIZE // 2, j)
            if k > 0:
                j = k
        chunks.append({"label": "第 %d 段" % part, "text": text[i:j]})
        i = j
        part += 1
    return chunks, "文本 · 共 %d 字符" % n, ""


def _batch_messages(mode, ck):
    if mode == "images":
        content = [{"type": "image_url", "image_url": {"url": u}} for u in ck["images"]]
        content.append({"type": "text",
                        "text": prompts.READ_BATCH_PROMPT_IMAGE.format(label=ck["label"])})
    else:
        content = prompts.READ_BATCH_PROMPT_TEXT.format(label=ck["label"], text=ck["text"])
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
        log_err("论文通读批次失败: " + str(box["err"])[:500])
        return None
    return box["text"]


def read_document_flow(cfg, path):
    """通读整篇文档:分批解析 -> 汇总 -> 写入相关小窗与 history。返回完整文本。"""
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
            chunks, info, thumb = _pdf_chunks(path, cfg)
            mode = "images"
        else:
            chunks, info, thumb = _text_chunks(path)
            mode = "text"
        n = len(chunks)
        if n == 0:
            windows.popup_update("文件里没有可读内容。", True)
            return None

        results = []
        for idx, ck in enumerate(chunks, 1):
            windows.popup_new_query("论文通读 · %s (%d/%d)" % (name, idx, n), "")
            windows.popup_update("正在阅读 %s …" % ck["label"], False)
            out = _chat_sync(cfg, _batch_messages(mode, ck))
            if out is None:  # 单批失败后稍等重试一次
                time.sleep(1.5)
                out = _chat_sync(cfg, _batch_messages(mode, ck))
            results.append("## %s\n\n%s" % (ck["label"], out or "*(本批解析失败)*"))

        joined = "\n\n".join(results)
        body = joined if len(joined) <= 26000 else joined[:26000] + "\n\n*(此处截断,完整内容见下方历史文件)*"

        windows.popup_new_query("论文通读 · %s (汇总)" % name, "")
        windows.popup_update("正在汇总符号总表…", False)
        final = _chat_sync(cfg, [
            {"role": "system", "content": prompts.SYSTEM_PROMPT},
            {"role": "user", "content": prompts.READ_FINAL_PROMPT.format(name=name)
                                       + "\n\n" + body},
        ])

        full = ("# 论文通读:《%s》\n\n> %s · 共 %d 批 · %s\n\n"
                "## 总览\n\n%s\n\n---\n\n# 分批细读\n\n%s"
                % (name, info, n, datetime.now().strftime("%Y-%m-%d %H:%M"),
                   final or "*(汇总失败)*", joined))
        windows.popup_update(full, True)

        saved = _save_reading(name, full)
        if saved:
            windows.popup_update(full + "\n\n---\n\n*(完整结果已保存:%s,并已放入「相关小窗」)*"
                                  % saved, True)
        actions.add_card(cfg, int(time.time()) % 1000000, "📄 " + name, thumb, full,
                         "", auto_related=False)
        return full
    except Exception:
        log_err(traceback.format_exc())
        windows.popup_update("**通读失败**\n\n```\n%s\n```" % traceback.format_exc()[-600:], True)
        return None


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
