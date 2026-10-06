# 🐋 鲸鲸报点读机

**哪里不会点哪里** —— 看论文时遇到看不懂的公式、术语、图表,按一下**鼠标侧键**,AI 立刻弹窗讲解,无需复制粘贴、无需切换窗口。

![platform](https://img.shields.io/badge/platform-Windows%2010%2B-blue) ![python](https://img.shields.io/badge/python-3.10%2B-green) ![license](https://img.shields.io/badge/license-MIT-orange)

> PaperPointReader: select (or box-select) any formula / term / figure in a paper and get an instant AI explanation in a floating window — mouse side-button driven, LaTeX-rendered, with a companion panel that collects related concepts & keywords. Windows only.

## ✨ 功能

- **🖱️ 鼠标侧键点读**:侧键1(后退键)圈选截图讲解,侧键2(前进键)划词讲解;侧键被低级钩子接管,不会触发浏览器后退/前进。也支持键盘热键 `Ctrl+Alt+Q` / `Ctrl+Alt+E`
- **🎯 公式圈选走视觉模型**:从 PDF 复制公式必然乱码,圈选截图交给视觉模型(默认 GLM-4.5V)是最稳的路线;公式逐符号拆解,LaTeX 实时渲染
- **📌 相关小窗**:屏幕右侧常驻侧栏,每次点读自动补充**相关概念、前置知识、延伸方向、中英文检索关键词**,卡片式累积,读文献时顺手建立知识网
- **📄 论文通读**:把整篇论文(PDF/.tex/.md/.txt)**直接拖进来**,模型通读全文后输出**每个公式的 LaTeX、每个符号的含义、公式的作用**,并汇总**符号总表 + 公式地图 + 阅读建议**。默认**整篇一次读取**(上下文上限 10 万 token),装不下才自动分批;PDF 走「整页截图 → 视觉模型」,公式原样进模型
- **🧩 PDF 重建为 LaTeX**:把 PDF 逐页转写成 LaTeX 源码,并用本机 xelatex 编译回 PDF(编译两遍 + 查日志,规程与 SuperTranslator 翻译模块一致)。重建后的 .tex 公式是原生 LaTeX,再拖给点读机通读/查阅时质量最高
- **⏸️ 一键开关**:`Ctrl+Alt+P` 或托盘勾选,随时暂停/启用;暂停后侧键原生功能立即恢复,图标变灰一眼可见
- **💬 追问**:弹窗底部常驻输入框——讲解出来后,直接输入你自己的问题(如「这个平方为什么要平方?」);模型会带着你**圈选的原图 / 划选的原文 + 已有讲解**回答,连续追问有上下文记忆,问答自动进相关小窗卡片与历史记录
- **🔁 再细讲**:还是不懂?一键换成更基础直觉的解释
- **🗂️ 历史记录**:每次问答自动存入 `history/日期.md`
- **⚡ 流式输出 + 任意 OpenAI 兼容接口**:智谱 / DeepSeek / OpenAI… 改两行配置即可

## 🚀 快速开始

### 方式一:下载 exe(推荐)

到 [Releases](https://github.com/2105453907/paper-point-reader/releases) 下载 `鲸鲸报点读机-win64.zip`,解压后:

1. 把 `config.example.json` 重命名为 `config.json`,填入 `api_key`([智谱开放平台](https://open.bigmodel.cn)注册即得,也支持任意 OpenAI 兼容接口)
2. 双击 `鲸鲸报点读机.exe`,托盘出现蓝色"读"图标即成功

### 方式二:源码运行

```bash
git clone https://github.com/2105453907/paper-point-reader.git
cd paper-point-reader
python -m pip install -r requirements.txt
copy config.example.json config.json   # 然后编辑填入 api_key
python main.py
```

Windows 下也可直接双击 `安装依赖.bat` 和 `启动点读机.bat`。

### 自检

```bash
python main.py --check      # 查看配置摘要
python main.py --test-api   # 测试 API 密钥连通性
python tests/test_mousehook.py     # 测试鼠标侧键钩子(Windows)
python main.py tests/sample_paper.pdf   # 论文通读流程自测(会消耗少量 API 额度)
```

## 🕹️ 使用

| 操作 | 效果 |
|---|---|
| 鼠标侧键1 / `Ctrl+Alt+Q` | **圈选讲解**:屏幕变暗,拖拽框选公式/图表/术语;直接单击则取光标附近一整条;`Esc` 取消 |
| 鼠标侧键2 / `Ctrl+Alt+E` | **划词讲解**:先在 PDF 里选中文字,再按键,自动复制并讲解(英文先翻译,缩写给全称,公式逐符号解释) |
| `Ctrl+Alt+S` | 显示/隐藏**相关小窗** |
| `Ctrl+Alt+P` | **启用/暂停点读机**:暂停后鼠标侧键立刻恢复浏览器原生后退/前进,讲解热键失效,托盘图标变灰;再按恢复 |
| `Ctrl+Alt+O` | **通读整篇论文**:唤出投递小窗,把文件拖进去即可;也可把文件**直接拖到桌面图标上**(程序没开就顺手启动,开着就自动投递给它),或用托盘菜单 / 弹窗工具栏「通读」按钮 |
| `Ctrl+Alt+L` | **PDF 重建为 LaTeX 并编译**:选一个 PDF,逐页转写为 `.tex`,用本机 xelatex 编译两遍产出同名 PDF(也可用托盘菜单「重建为 LaTeX 并编译…」) |
| `Esc` | 隐藏弹窗(程序退到托盘继续运行) |
| 托盘右键 | 启用/暂停(勾选项) · 显示窗口 · 相关小窗 · 设置 · 历史 · 退出 |

**桌面启动图标**:运行 `python tools/make_shortcut.py` 即可在桌面创建带图标的「鲸鲸报点读机」快捷方式(源码运行方式);打包版直接右键 exe 发送到桌面即可。重复启动不会双开——程序已在运行时,再双击图标会**直接把它的窗口叫到前台**;拖入文件则自动交给它通读。启动时默认亮出主窗口(显示用法速览),不想要就把 `show_on_start` 改为 `false`。

弹窗按钮:**复制** / **再细讲** / **通读** / **相关**(开关侧窗) / **设置** / **隐藏**。

**追问输入框**:弹窗底部,按 `/` 快速聚焦(或直接点击),输入问题后回车发送;可以连续追问,模型记得圈选/划选的内容和前面的对话。通读/重建完成后也可以直接在这里追问整篇论文。

## 📄 论文通读

学习一篇新论文之前,先把文件「扔进来」,让模型替你通读全文并整理好一切:

- **怎么拖**:把 PDF **直接拖到桌面「鲸鲸报点读机」图标上**(程序已在运行也没关系,会自动投递给它);或按 `Ctrl+Alt+O` 唤出**投递小窗**拖进去;或托盘菜单「通读论文(拖入 / 选择文件)…」、弹窗工具栏「通读」按钮。支持 **PDF、.tex、.md、.txt**
- **怎么读**:默认**整篇一次读取**——把全文(含页面截图)一次性交给模型,上下文上限 10 万 token(可调);超出上限或模型拒绝时自动降级为分批读取,单批失败还会自动重试
- **输出什么**:**论文主题**、**公式清单**(每条公式的 LaTeX 形式 + 每个字母/符号的含义 + 它在论文里的作用)、**符号总表**(跨全文统一)、**公式地图**(按章节定位)、**阅读建议**
- **结果去哪**:实时流式显示在弹窗,完整结果自动保存到 `history/通读-<论文名>-<时间>.md`,并作为一张卡片放进「相关小窗」

### 关于「PDF 转 LaTeX」的说明

本机安装的 LaTeX(MiKTeX/TeX Live)是 **.tex → PDF** 的正向编译器,无法把 PDF 反编译回 LaTeX,所以工具**不需要**这一步,而是走了更可靠的路线:

| 输入 | 路线 | 公式质量 |
|---|---|---|
| PDF | 整页高清截图 → 视觉模型识别 | 好:公式原样进模型,不受 PDF 文本层乱码影响 |
| .tex 源码 | 直接读取(去掉注释后分块) | 最好:拿到的是真实 LaTeX 公式 |

如果你的论文有 LaTeX 源码(arXiv 论文可在页面选 "TeX Source" 直接下载),优先扔 .tex,效果最佳。

## 🧩 PDF 重建为 LaTeX(调用本机 xelatex)

需要一步到位拿到"干净 LaTeX"时用这个:`Ctrl+Alt+L` 或托盘菜单「重建为 LaTeX 并编译(选择 PDF)…」。

- **机制**:视觉模型**逐页把 PDF 转写为 LaTeX**(章节、正文、行内/独立公式环境,公式保留原编号;图表用注释占位)→ 套用 article + amsmath 模板组装 → **本机 xelatex 编译两遍** → 检查日志 undefined → 自动打开编译好的 PDF
- **产出**:`history/rebuilt/<文件名>/` 下的 `<文件名>.tex`(源码)与 `<文件名>.pdf`(编译结果)
- **要求**:本机安装 TeX Live / MiKTeX(xelatex 在 PATH 中,或放在 `C:\texlive\*\bin\windows\`);未安装时程序会明确提示
- **说明**:PDF→LaTeX 本质是**识别重建**,不是格式转换——所以质量取决于模型;若你已有官方 .tex 源码,不需要重建,直接用它。编译规程(模板化/编译两遍/查日志)与同作者的 SuperTranslator 论文翻译模块完全一致

## ⚙️ 配置(`config.json`)

| 字段 | 说明 |
|---|---|
| `api_base` | OpenAI 兼容接口地址。DeepSeek:`https://api.deepseek.com/v1`;OpenAI:`https://api.openai.com/v1` |
| `api_key` | 密钥(留空时自动读取环境变量 `ZHIPUAI_API_KEY` / `OPENAI_API_KEY`) |
| `extra_headers` | 可选。附加请求头,某些网关需要。如 OpenCode Go 套餐端点要求 `{"x-opencode-session": "<任意稳定UUID>"}` |
| `text_model` / `vision_model` | 划词用文本模型 / 圈选用视觉模型 |
| `fallback_model` | 可选。主模型返回 402(余额不足)或免费层限制时自动降级到这个模型再试一次 |
| `mouse_side1` / `mouse_side2` | 侧键功能:`region` / `text` / `none`(不拦截,还原原生功能) |
| `hotkey_*` | 键盘热键,如 `f9`、`alt+z`;默认 Ctrl+Alt 组合是为避开 Adobe 等软件的 Alt 菜单键 |
| `hotkey_read_paper` | 通读论文的投递小窗热键(默认 `ctrl+alt+o`) |
| `read_mode` | 通读策略:`auto`(默认,能整篇装下就一次读,否则分批)/ `whole`(总是整篇)/ `batch`(总是分批) |
| `read_context_tokens` | 整篇一次读取的上下文上限,默认 100000 |
| `read_image_scale` / `read_pages_per_request` / `read_max_pages` | PDF 页面渲染倍率(默认 1.8)/ 分批模式每批页数(默认 6)/ 最多读多少页(默认 60,0=全部) |
| `side_window` / `auto_related` | 启用相关小窗 / 自动补充相关内容(关掉省 API 费用) |
| `popup_*` / `side_*` | 两个窗口的大小 |
| `save_history` | 自动保存问答记录 |
| `show_on_start` | 启动时是否亮出主窗口(默认 `true`,显示用法速览;放启动项嫌吵可改 `false`) |

## 🧩 项目结构

```
main.py                 入口
diandu/
  app.py                装配:窗口创建、线程/托盘启动、--check/--test-api
  config.py             配置加载与路径(打包后数据文件跟随 exe)
  runtime.py            共享运行时状态
  prompts.py            提示词
  llm.py                OpenAI 兼容流式调用(文本/视觉)
  webui.py              两个窗口的内嵌 HTML(WebSocket 免了,直接 evaluate_js)
  windows.py            弹窗/侧窗的显示更新 + 无 WebView2 时的兜底
  bridge.py             JS 桥(页面按钮 → Python)
  actions.py            圈选/划词流程、问答编排、卡片、历史
  document.py           论文通读:文件解析(PDF/LaTeX/文本)、分批公式解析、汇总
  capture.py            遮罩圈选、mss 截图、模拟 Ctrl+C 划词
  inputs.py             WH_MOUSE_LL 侧键钩子 + 键盘热键
  trayicon.py           托盘
tools/make_icon.py      生成图标
tools/make_shortcut.py  在桌面创建启动快捷方式
tests/test_mousehook.py 侧键钩子自测
build_exe.bat           一键 PyInstaller 打包
.github/workflows/      推 tag 自动构建 exe 并附到 Release
```

## 🔨 自己打包 exe

```bat
build_exe.bat
```

产物为 `dist/鲸鲸报点读机.exe`(单文件)。推送 `v*` 标签时 CI 会自动构建并附到 GitHub Release。

## ❓ 常见问题

- **讲解/历史记录出现乱码(åè¯´æ˜Ž…)**:v0.1.0 早期版本存在响应解码 bug(无 charset 的 SSE 被按 Latin-1 解码),已修复;旧的历史文件可用 `python tools/fix_mojibake.py` 一键还原。
- **窗口闪来闪去 / 讲解弹窗打不开**:已修复(窗口操作串行化 + 可见性跟踪 + 1 秒触发冷却)。如果你的版本还出现:双击桌面图标把窗口叫到前台,或托盘右键「显示窗口」;仍不行就重启程序。
- **提示模型不存在 / 400**:把 `text_model`、`vision_model` 换成你账号实际可用的模型名。
- **401**:密钥填错或没保存。
- **划词拿不到文字**:该 PDF 禁止复制,改用圈选(侧键1)。
- **侧键按下后浏览器还是后退**:钩子未装上,看 `err.log` 后重启程序。
- **多显示器**:目前圈选/弹窗只支持主屏;高分屏已做 DPI 适配。
- **开机自启**:`Win+R` → `shell:startup`,把桌面上的「鲸鲸报点读机」快捷方式(或 `启动点读机.bat`)放进去即可。

## ⚠️ 已知限制与说明

- 划词模式会临时改写剪贴板,读取后自动恢复你之前的内容。
- 圈选截图要求画面在主显示器上。
- 需要联网(模型 API 与公式渲染脚本来自 CDN)。
- 侧键全局接管后,浏览器后退/前进会失效(`"none"` 可还原)。
- 自建exe 若被杀毒软件误报,请加白名单(全局钩子类程序的常见待遇),或用源码运行。

## 📄 License

[MIT](LICENSE)
