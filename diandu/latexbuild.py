# -*- coding: utf-8 -*-
"""PDF -> LaTeX 重建,并调用本机 xelatex 编译成 PDF。

流程沿用 SuperTranslator(论文翻译模块)的编译规程:
模板化组装 -> xelatex 编译两遍 -> 检查日志中的 undefined。
重建本质是「视觉模型逐页转写」(PDF->LaTeX 属于识别重建,不是格式转换);
拿到 .tex 后,点读机的通读/讲解可以改用 .tex 源,公式质量最高。
"""
import os
import re
import shutil
import subprocess
import threading
import time
import traceback
from datetime import datetime

from . import actions, document, prompts, runtime, windows
from .config import HISTORY_DIR, log_err

_REBUILD = {"v": False}

TEMPLATE = r"""\documentclass[10pt]{article}
\usepackage[margin=2.2cm]{geometry}
\usepackage{amsmath,amssymb,amsfonts}
\usepackage{graphicx}
\usepackage{booktabs}
\usepackage{float}
\usepackage{xeCJK}
\setlength{\parindent}{0pt}
\setlength{\parskip}{4pt}
\title{%(title)s}
\author{由「鲸鲸报点读机」从 PDF 重建 \quad 源文件:%(src)s}
\date{%(date)s}
\begin{document}
\maketitle
%(body)s
\end{document}
"""


def find_xelatex():
    exe = shutil.which("xelatex")
    if exe:
        return exe
    import glob
    cands = glob.glob(r"C:\texlive\*\bin\windows\xelatex.exe") \
        + glob.glob(r"D:\texlive\*\bin\windows\xelatex.exe") \
        + glob.glob(os.path.expandvars(r"%LOCALAPPDATA%\Programs\MiKTeX\miktex\bin\x64\xelatex.exe"))
    return sorted(cands)[-1] if cands else None


def pick_pdf():
    import tkinter as tk
    from tkinter import filedialog
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    path = filedialog.askopenfilename(title="选择要重建为 LaTeX 的 PDF",
                                      filetypes=[("PDF 文件", "*.pdf"), ("所有文件", "*.*")])
    root.destroy()
    return path or None


def rebuild_dialog(cfg):
    p = pick_pdf()
    if p:
        rebuild_flow(cfg, p)


def _tex_escape(s):
    for a, b in (("\\", r"\textbackslash{}"), ("&", r"\&"), ("%", r"\%"), ("$", r"\$"),
                 ("#", r"\#"), ("_", r"\_"), ("{", r"\{"), ("}", r"\}"),
                 ("~", r"\textasciitilde{}"), ("^", r"\textasciicircum{}")):
        s = s.replace(a, b)
    return s


def _clean_tex(s):
    """去掉模型可能加的代码块围栏/导言区残留。"""
    s = (s or "").strip()
    m = re.match(r"^```[a-zA-Z]*\s*\n(.*)\n```\s*$", s, re.S)
    if m:
        s = m.group(1)
    if "\\begin{document}" in s:
        s = s.split("\\begin{document}", 1)[1]
        s = s.replace("\\end{document}", "")
    return s.strip()


def _compile(xelatex, cwd, base):
    """按翻译模块的规程:编译两遍,再查日志。返回 (是否成功, 日志尾部)。"""
    tex = base + ".tex"
    for run in (1, 2):
        try:
            p = subprocess.run([xelatex, "-interaction=nonstopmode", "-halt-on-error", tex],
                               cwd=cwd, capture_output=True, timeout=600)
            out = (p.stdout or b"").decode("utf-8", "ignore")
            if p.returncode != 0:
                return False, "第 %d 遍编译失败:\n%s" % (run, out[-1200:])
        except Exception as e:
            return False, "第 %d 遍编译异常: %s" % (run, e)
    tail = ""
    try:
        with open(os.path.join(cwd, base + ".log"), "r", encoding="utf-8", errors="ignore") as f:
            log = f.read()
        tail = "log 中 undefined 计数: %d" % log.count("undefined")
    except Exception:
        pass
    return True, tail


def rebuild_flow(cfg, path):
    """PDF -> 逐页转写 LaTeX -> 组装 -> xelatex 编译两遍 -> 打开 PDF。"""
    if _REBUILD["v"]:
        windows.popup_new_query("LaTeX 重建", "")
        windows.popup_update("正在重建另一份文档,请稍候。", True)
        return None
    _REBUILD["v"] = True
    try:
        path = os.path.abspath(path)
        if not os.path.isfile(path) or not path.lower().endswith(".pdf"):
            windows.popup_new_query("LaTeX 重建", "")
            windows.popup_update("请选择 PDF 文件。", True)
            return None
        name = os.path.basename(path)
        base = os.path.splitext(name)[0]

        windows.popup_new_query("LaTeX 重建 · " + name, "")
        xelatex = find_xelatex()
        if not xelatex:
            windows.popup_update(
                "未找到 xelatex。请安装 TeX Live / MiKTeX,或把 xelatex 所在目录加入 PATH。",
                True)
            return None

        windows.popup_update("正在渲染页面…", False)
        pages, total, limit, _thumb = document._pdf_pages(path, cfg)

        bodies = []
        for i in range(limit):
            windows.popup_new_query("LaTeX 重建 · %s (%d/%d)" % (name, i + 1, limit), "")
            windows.popup_update("正在转写第 %d 页 …" % (i + 1), False)
            msgs = [{"role": "system", "content": prompts.SYSTEM_PROMPT},
                    {"role": "user", "content": [
                        {"type": "image_url", "image_url": {"url": pages[i]["url"]}},
                        {"type": "text",
                         "text": prompts.PAGE_TEX_PROMPT.replace("%PAGE%", str(i + 1))}]}]
            out = document._chat_sync(cfg, msgs)
            if out is None:
                time.sleep(1.5)
                out = document._chat_sync(cfg, msgs)
            bodies.append("%% ==================== 第 %d 页 ====================\n%s\n\\newpage"
                          % (i + 1, _clean_tex(out) or "%% (本页转写失败)"))

        tex = TEMPLATE % {"title": _tex_escape(base), "src": _tex_escape(name),
                          "date": datetime.now().strftime("%Y-%m-%d"),
                          "body": "\n\n".join(bodies)}
        outdir = os.path.join(HISTORY_DIR, "rebuilt", base)
        os.makedirs(outdir, exist_ok=True)
        tex_path = os.path.join(outdir, base + ".tex")
        with open(tex_path, "w", encoding="utf-8") as f:
            f.write(tex)

        windows.popup_new_query("LaTeX 重建 · %s (编译)" % name, "")
        windows.popup_update("正在用 xelatex 编译(两遍)…", False)
        ok, tail = _compile(xelatex, outdir, base)
        pdf_path = os.path.join(outdir, base + ".pdf")
        api = runtime.api
        if ok and os.path.exists(pdf_path):
            try:
                os.startfile(pdf_path)
            except Exception:
                pass
            msg = ("# LaTeX 重建完成\n\n"
                   "- 源码:`%s`\n- 编译产物:`%s`\n- %s\n\n"
                   "已自动打开编译结果。后续可把 .tex 拖给点读机通读:"
                   "公式是原生 LaTeX,质量最高。" % (tex_path, pdf_path, tail))
            windows.popup_update(msg, True)
            actions.add_card(cfg, int(time.time()) % 1000000, "🧩 " + name + " (LaTeX)",
                             "", msg, "", auto_related=False)
            if api is not None:
                api.display = msg
            return tex_path
        msg = "**编译失败( .tex 已生成 )**\n\n`%s`\n\n```\n%s\n```" % (tex_path, tail[-1200:])
        windows.popup_update(msg, True)
        if api is not None:
            api.display = msg
        return tex_path
    except Exception:
        log_err(traceback.format_exc())
        windows.popup_update("**重建失败**\n\n```\n%s\n```" % traceback.format_exc()[-600:], True)
        return None
    finally:
        _REBUILD["v"] = False
