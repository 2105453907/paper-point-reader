# -*- coding: utf-8 -*-
"""在桌面创建「文献点读机」启动图标(Windows)。

用法:
    python tools/make_shortcut.py

优先创建 .lnk 快捷方式(通过 pywin32,带应用图标、无黑窗闪现);
若 pywin32 不可用,退化为在桌面创建一个 .bat 启动文件。
"""
import os
import sys


def _root():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def pythonw_path():
    exe = sys.executable or "python"
    cand = exe.replace("python.exe", "pythonw.exe")
    return cand if os.path.exists(cand) else exe


def _desktop_fallback():
    return os.path.join(os.environ.get("USERPROFILE", os.path.expanduser("~")), "Desktop")


def make_lnk():
    import win32com.client
    root = _root()
    ws = win32com.client.Dispatch("WScript.Shell")
    desk = ws.SpecialFolders("Desktop")
    path = os.path.join(desk, "文献点读机.lnk")
    lnk = ws.CreateShortcut(path)
    lnk.TargetPath = pythonw_path()
    lnk.Arguments = '"%s"' % os.path.join(root, "main.py")
    lnk.WorkingDirectory = root
    icon = os.path.join(root, "assets", "icon.ico")
    if os.path.exists(icon):
        lnk.IconLocation = icon
    lnk.Description = "文献点读机 —— 哪里不会点哪里"
    lnk.Save()
    return path


def make_bat():
    root = _root()
    path = os.path.join(_desktop_fallback(), "文献点读机.bat")
    with open(path, "w", encoding="utf-8") as f:
        f.write("@echo off\r\n")
        f.write('cd /d "%s"\r\n' % root)
        f.write('start "" "%s" main.py\r\n' % pythonw_path())
    return path


def main():
    try:
        path = make_lnk()
        kind = "快捷方式"
    except Exception as e:
        path = make_bat()
        kind = "启动文件(lnk 失败: %s)" % e
    print("已创建桌面%s: %s" % (kind, path))


if __name__ == "__main__":
    main()
