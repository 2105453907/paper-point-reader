@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo 正在安装依赖(优先使用清华镜像)...
python -m pip install -r requirements.txt -q -i https://pypi.tuna.tsinghua.edu.cn/simple
if errorlevel 1 python -m pip install -r requirements.txt -q
echo.
echo 完成!以后双击 启动点读机.bat 运行。
pause
