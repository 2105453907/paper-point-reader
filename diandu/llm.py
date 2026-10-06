# -*- coding: utf-8 -*-
"""OpenAI 兼容接口的流式调用(文本与视觉)。"""
import json
import threading
import time
import traceback

import requests

from .config import log_err


def has_image(msgs):
    return any(isinstance(m.get("content"), list) for m in msgs if m.get("role") == "user")


def chat_stream(cfg, msgs, on_delta, on_done, on_error):
    """流式对话;on_delta 收到累计文本,on_done 收到完整文本。"""
    if not cfg.get("api_key"):
        on_error("还没有配置 API Key。\n\n"
                 "1. 点击窗口上方「设置」打开 config.json;\n"
                 "2. 在 \"api_key\" 填入你的密钥(智谱开放平台 https://open.bigmodel.cn 可免费申请);\n"
                 "3. 保存后重新圈选/划词即可。")
        return
    model = cfg["vision_model"] if has_image(msgs) else cfg["text_model"]
    url = cfg["api_base"].rstrip("/") + "/chat/completions"
    headers = {"Authorization": "Bearer " + cfg["api_key"], "Content-Type": "application/json"}
    payload = {"model": model, "messages": msgs, "stream": True}

    def run():
        buf = ""
        last = 0.0
        try:
            with requests.post(url, headers=headers, json=payload,
                               stream=True, timeout=(15, 600)) as r:
                if r.status_code != 200:
                    body = r.text[:400]
                    hint = ""
                    if r.status_code == 401:
                        hint = "\n\n(密钥无效,请检查 api_key)"
                    elif "model" in body.lower():
                        hint = ("\n\n(模型名可能不可用,请在 config.json 里把 text_model / "
                                "vision_model 换成你账号支持的模型)")
                    on_error("HTTP %s\n\n%s%s" % (r.status_code, body, hint))
                    return
                for line in r.iter_lines(decode_unicode=True):
                    if not line or not line.startswith("data:"):
                        continue
                    data = line[len("data:"):].strip()
                    if data == "[DONE]":
                        break
                    try:
                        piece = json.loads(data)["choices"][0].get("delta", {}).get("content")
                    except Exception:
                        piece = None
                    if piece:
                        buf += piece
                        now = time.time()
                        if now - last > 0.3:
                            last = now
                            on_delta(buf)
            on_done(buf)
        except Exception as e:
            log_err(traceback.format_exc())
            on_error("请求失败:%s\n\n请检查网络与 api_base 配置,或运行 "
                     "python main.py --test-api 自检。" % e)

    threading.Thread(target=run, daemon=True).start()


def test_api(cfg):
    """命令行自检:发一条最小请求验证密钥与模型可用。"""
    if not cfg.get("api_key"):
        print("api_key 未配置,请先编辑 config.json")
        return
    print("正在测试文本模型 %s ..." % cfg["text_model"])
    try:
        r = requests.post(
            cfg["api_base"].rstrip("/") + "/chat/completions",
            headers={"Authorization": "Bearer " + cfg["api_key"]},
            json={"model": cfg["text_model"],
                  "messages": [{"role": "user", "content": "请只回复:OK"}]},
            timeout=60)
        if r.status_code == 200:
            print("✓ 连通正常,模型回复:", r.json()["choices"][0]["message"]["content"][:50])
        else:
            print("✗ HTTP %s: %s" % (r.status_code, r.text[:300]))
    except Exception as e:
        print("✗ 请求失败:", e)
