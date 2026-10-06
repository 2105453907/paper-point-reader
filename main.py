# -*- coding: utf-8 -*-
"""鲸鲸报点读机 —— 哪里不会点哪里。

入口脚本,实现见 diandu/ 包(README.md 有完整说明)。
    python main.py --check      查看配置
    python main.py --test-api   测试 API 连通性
"""
import sys

if __name__ == "__main__":
    try:
        from diandu.app import main
        main()
    except ImportError as e:
        print("缺少依赖库:", e)
        print("请先运行: python -m pip install -r requirements.txt")
        try:
            input("按回车退出...")
        except Exception:
            pass
    except Exception:
        try:
            from diandu.config import log_err
            import traceback
            log_err(traceback.format_exc())
        except Exception:
            pass
        raise
