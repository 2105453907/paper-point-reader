# -*- coding: utf-8 -*-
"""生成应用图标 assets/icon.png 与 assets/icon.ico(蓝底圆角 + 白色"读")。"""
import os

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(os.path.dirname(HERE), "assets")
os.makedirs(ASSETS, exist_ok=True)

SIZE = 256
img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
d = ImageDraw.Draw(img)
d.rounded_rectangle([8, 8, SIZE - 8, SIZE - 8], radius=56, fill=(37, 99, 235, 255))
try:
    font = ImageFont.truetype("msyh.ttc", 150)
    d.text((SIZE / 2, SIZE / 2 + 6), "读", font=font, fill="white", anchor="mm")
except Exception:
    d.text((SIZE / 2, SIZE / 2), "DU", fill="white", anchor="mm")
img.save(os.path.join(ASSETS, "icon.png"))
img.save(os.path.join(ASSETS, "icon.ico"),
         sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
print("icon ->", ASSETS)
