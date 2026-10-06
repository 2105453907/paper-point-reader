@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo 正在安装 PyInstaller...
python -m pip install -q pyinstaller
echo 正在打包(约 1-3 分钟)...
python -m PyInstaller --noconfirm --clean --windowed --onefile ^
  --name PaperPointReader --icon assets\icon.ico ^
  --hidden-import webview.platforms.winforms --hidden-import webview.platforms.edgechromium ^
  --collect-all clr_loader --collect-all pypdfium2 --collect-all tkinterdnd2 ^
  --exclude-module PyQt5 --exclude-module PyQt6 --exclude-module PySide2 --exclude-module PySide6 ^
  --exclude-module qtpy ^
  --exclude-module webview.platforms.qt --exclude-module webview.platforms.cef ^
  --exclude-module webview.platforms.gtk --exclude-module webview.platforms.android ^
  --exclude-module webview.platforms.cocoa ^
  --exclude-module numpy --exclude-module scipy --exclude-module pandas ^
  --exclude-module matplotlib --exclude-module torch --exclude-module IPython ^
  main.py
if errorlevel 1 (
  echo.
  echo 打包失败,请把上面的报错发到 Issues。
  pause
  exit /b 1
)
if exist "dist\PaperPointReader.exe" ren "dist\PaperPointReader.exe" "鲸鲸报点读机.exe"
echo.
echo 完成: dist\鲸鲸报点读机.exe  (可搭配 config.example.json 一起分发)
pause
