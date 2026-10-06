# -*- coding: utf-8 -*-
"""修复因响应解码错误产生的乱码(UTF-8 字节被按 Latin-1 读出)。

逐行处理:能被 Latin-1 编码、且能按 UTF-8 解回的行,判定为乱码行并还原;
本来就是正常中文/ASCII 的行(无法 Latin-1 编码)原样保留。

用法:
    python tools/fix_mojibake.py [目录...]     # 默认修 history/
"""
import os
import sys


def fix_line(line):
    try:
        raw = line.encode("latin-1")
    except UnicodeEncodeError:
        return None                       # 含真正的中文等非 Latin-1 字符:本来就正常
    try:
        fixed = raw.decode("utf-8")
    except UnicodeDecodeError:
        return None                       # 不是"UTF-8 被当 Latin-1"的形态
    return fixed if fixed != line else None


def fix_file(path):
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        lines = f.read().splitlines(keepends=True)
    changed = 0
    out = []
    for ln in lines:
        new = fix_line(ln)
        if new is not None:
            out.append(new)
            changed += 1
        else:
            out.append(ln)
    if changed:
        with open(path, "w", encoding="utf-8") as f:
            f.write("".join(out))
    return changed


def main():
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    roots = sys.argv[1:] or [os.path.join(here, "history")]
    total_files = total_lines = 0
    for root in roots:
        for dirpath, _, names in os.walk(root):
            for n in names:
                if not n.lower().endswith((".md", ".tex", ".txt")):
                    continue
                p = os.path.join(dirpath, n)
                c = fix_file(p)
                if c:
                    total_files += 1
                    total_lines += c
                    print("fixed %4d lines  %s" % (c, p))
    print("done: %d files / %d lines repaired" % (total_files, total_lines))


if __name__ == "__main__":
    main()
