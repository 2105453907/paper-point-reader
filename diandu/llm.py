# -*- coding: utf-8 -*-
"""OpenAI 兼容接口的流式调用(文本与视觉)。

部分网关(如 OpenCode Zen)有 Cloudflare 防护,会拦截 python-requests
默认 UA,因此统一携带浏览器 User-Agent。另外支持 fallback_model:
主模型返回 402(余额不足)或免费层限制时,自动降级重试一次。
"""
import json
import threading
import time
import traceback

import requests

from .config import log_err

BROWSER_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")


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

    base = cfg["api_base"].rstrip("/")
    url = base + "/chat/completions"
    headers = {"Authorization": "Bearer " + cfg["api_key"],
               "Content-Type": "application/json",
               "User-Agent": BROWSER_UA}
    start_model = cfg["vision_model"] if has_image(msgs) else cfg["text_model"]

    def run():
        model = start_model
        tried_fallback = False
        buf = ""
        last = 0.0
        while True:
            payload = {"model": model, "messages": msgs, "stream": True}
            try:
                with requests.post(url, headers=headers, json=payload,
                                   stream=True, timeout=(15, 600)) as r:
                    if r.status_code != 200:
                        body = r.text[:400]
                        low = body.lower()
                        can_fallback = (cfg.get("fallback_model")
                                        and cfg["fallback_model"] != model
                                        and not tried_fallback
                                        and (r.status_code == 402
                                             or "freetier" in low
                                             or "insufficient" in low))
                        if can_fallback:
                            tried_fallback = True
                            model = cfg["fallback_model"]
                            continue
                        hint = ""
                        if r.status_code == 401:
                            hint = "\n\n(密钥无效,请检查 api_key)"
                        elif r.status_code == 402:
                            hint = ("\n\n(账户余额不足;已在 config.json 配置 fallback_model=%s"
                                    " 时会自动降级)" % cfg.get("fallback_model", "无"))
                        elif "model" in low:
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
                return
            except Exception as e:
                log_err(traceback.format_exc())
                on_error("请求失败:%s\n\n请检查网络与 api_base 配置,或运行 "
                         "python main.py --test-api 自检。" % e)
                return

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
            headers={"Authorization": "Bearer " + cfg["api_key"],
                     "Content-Type": "application/json",
                     "User-Agent": BROWSER_UA},
            json={"model": cfg["text_model"],
                  "messages": [{"role": "user", "content": "请只回复:OK"}]},
            timeout=90)
        if r.status_code == 200:
            print("✓ 连通正常,模型回复:", r.json()["choices"][0]["message"]["content"][:50])
        else:
            print("✗ HTTP %s: %s" % (r.status_code, r.text[:300]))
            if r.status_code == 402 and cfg.get("fallback_model"):
                print("(余额不足 —— 正式使用时会自动降级到 fallback_model=%s,再测一次)"
                      % cfg["fallback_model"])
                r2 = requests.post(
                    cfg["api_base"].rstrip("/") + "/chat/completions",
                    headers={"Authorization": "Bearer " + cfg["api_key"],
                             "Content-Type": "application/json",
                             "User-Agent": BROWSER_UA},
                    json={"model": cfg["fallback_model"],
                          "messages": [{"role": "user", "content": "请只回复:OK"}]},
                    timeout=90)
                if r2.status_code == 200:
                    print("✓ fallback_model 可用,回复:", r2.json()["choices"][0]["message"]["content"][:50])
                else:
                    print("✗ fallback_model 也不可用: HTTP %s: %s" % (r2.status_code, r2.text[:200]))
    except Exception as e:
        print("✗ 请求失败:", e)
