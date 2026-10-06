# -*- coding: utf-8 -*-
"""两个 WebView 窗口的内嵌页面(主弹窗 / 相关小窗)。

__VERSION__ 与 __RENDER_JS__ 在导入时替换。
RENDER_JS 是共享的渲染工具(tests/run_render_test.js 会从本文件提取同一份代码做离线测试):
先摘出数学片段并按需转换 LaTeX 环境,再做 Markdown,最后放回并交给 KaTeX——
否则 marked 会把 \\( \\) 转义掉、把 _ 和 * 当作强调,公式就会以乱码形式漏渲染。

界面:鲸鲸蓝主题(深海蓝 -> 亮蓝渐变),圆角卡片、胶囊按钮、自定义滚动条。
"""
from . import __version__

import base64
import os
import re

_ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")


def _vendor_html():
    """内联本地 marked / KaTeX / 字体(离线可用、页面即刻就绪,不依赖 CDN)。

    资源缺失时退回 CDN 引用,保证仍可运行。
    """
    try:
        def read(name):
            with open(os.path.join(_ASSETS, name), encoding="utf-8") as f:
                return f.read()

        css = read("katex.min.css")

        def font_data(m):
            fn = m.group(1)
            try:
                with open(os.path.join(_ASSETS, "fonts", fn), "rb") as f:
                    b64 = base64.b64encode(f.read()).decode()
                return 'url(data:font/woff2;base64,%s) format("woff2")' % b64
            except Exception:
                return m.group(0)

        css = re.sub(r'url\(fonts/([\w\-.]+\.woff2)\)\s*format\("woff2"\)', font_data, css)
        css = re.sub(r',\s*url\(fonts/[\w\-.]+\.(?:woff|ttf)\)\s*format\("[a-z]+"\)', "", css)
        js = "\n".join(read(n) for n in ("marked.min.js", "katex.min.js", "auto-render.min.js"))
        return "<style>%s</style>\n<script>%s</script>" % (css, js)
    except Exception:
        return (
            '<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.css">\n'
            '<script src="https://cdn.jsdelivr.net/npm/marked@12.0.2/marked.min.js"></script>\n'
            '<script src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.js"></script>\n'
            '<script src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/contrib/auto-render.min.js"></script>')


_VENDOR = _vendor_html()

RENDER_JS = r"""/*==RENDER-JS-BEGIN==*/
function escHtml(s){
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}
function convertMath(s){
  var env = s.match(/^\\begin\{([a-zA-Z*]+)\}([\s\S]*)\\end\{\1\}$/);
  if(env){
    var name = env[1], body = env[2];
    if(name === 'equation' || name === 'equation*' || name === 'displaymath')
      return '$$' + body + '$$';
    if(name === 'align' || name === 'align*' || name === 'eqnarray' || name === 'eqnarray*')
      return '$$\\begin{aligned}' + body.replace(/&=&/g, '&=') + '\\end{aligned}$$';
    if(name === 'gather' || name === 'gather*' || name === 'multline' || name === 'multline*')
      return '$$\\begin{gathered}' + body + '\\end{gathered}$$';
  }
  if(s.slice(0, 2) === '\\[') return '$$' + s.slice(2, -2) + '$$';
  if(s.slice(0, 2) === '\\(') return '$' + s.slice(2, -2) + '$';
  return s;
}
var MATH_RE = /\$\$[\s\S]*?\$\$|\\\[[\s\S]*?\\\]|\\\([\s\S]*?\\\)|\$[^$\n]*?\$|\\begin\{(?:equation\*?|align\*?|gather\*?|eqnarray\*?|multline\*?|displaymath)\}[\s\S]*?\\end\{(?:equation\*?|align\*?|gather\*?|eqnarray\*?|multline\*?|displaymath)\}/g;
function toHtml(t){
  t = t || '';
  if(!window.marked){ return '<pre style="white-space:pre-wrap">' + escHtml(t) + '</pre>'; }
  try{
    var store = [];
    var tag = 'MATHX' + Math.floor(Math.random() * 1e9).toString(36) + 'Q';
    var text = t.replace(MATH_RE, function(m){
      var s = convertMath(m)
        .replace(/\\label\{[^}]*\}/g, '')
        .replace(/\\(?:nonumber|notag)\b/g, '');
      store.push(s);
      return tag + (store.length - 1) + 'Q';
    });
    var html = marked.parse(text);
    return html.replace(new RegExp(tag + '(\\d+)Q', 'g'), function(_, i){
      return '<span class="maths">' + escHtml(store[+i]) + '</span>';
    });
  }catch(e){
    return '<pre style="white-space:pre-wrap">' + escHtml(t) + '</pre>';
  }
}
function renderMath(el){
  try{ if(window.renderMathInElement){
    renderMathInElement(el, {delimiters:[
      {left:'$$', right:'$$', display:true},
      {left:'\\[', right:'\\]', display:true},
      {left:'$', right:'$', display:false},
      {left:'\\(', right:'\\)', display:false}], throwOnError:false});
  } }catch(e){}
}
/*==RENDER-JS-END==*/"""

_THEME_CSS = r"""
  :root{
    --bg:#f7f9fc; --card:#ffffff; --ink:#1b2430; --muted:#64748b;
    --brand:#2563eb; --brand-deep:#0b3a8c; --brand-sky:#0ea5e9;
    --line:#e6ebf2; --ring:rgba(37,99,235,.18);
    --shadow:0 6px 24px rgba(15,40,90,.08);
  }
  *{box-sizing:border-box;}
  html,body{margin:0;padding:0;height:100%;background:var(--bg);color:var(--ink);
    font-family:"Microsoft YaHei UI","Microsoft YaHei","PingFang SC","Segoe UI",sans-serif;}
  ::-webkit-scrollbar{width:10px;height:10px;}
  ::-webkit-scrollbar-track{background:transparent;}
  ::-webkit-scrollbar-thumb{background:#c7d2e4;border-radius:8px;border:2px solid transparent;
    background-clip:content-box;}
  ::-webkit-scrollbar-thumb:hover{background:#9fb3d1;background-clip:content-box;}
  .tb{border:none;border-radius:999px;background:rgba(255,255,255,.14);color:#fff;font-size:11.5px;
    padding:5px 11px;cursor:pointer;transition:background .15s,transform .1s;white-space:nowrap;
    font-family:inherit;}
  .tb:hover{background:rgba(255,255,255,.3);}
  .tb:active{transform:scale(.95);}
  .tb.ghost{background:transparent;font-size:13px;padding:5px 8px;}
  .tb.ghost:hover{background:rgba(255,255,255,.22);}
  .katex{font-size:1.02em;}
  .katex-display{overflow-x:auto;overflow-y:hidden;padding:4px 2px;}
  .spin{width:13px;height:13px;border-radius:50%;border:2px solid #cfe0ff;border-top-color:var(--brand);
    animation:spin .9s linear infinite;display:inline-block;vertical-align:-2px;margin-right:8px;}
  @keyframes spin{to{transform:rotate(360deg)}}
  .md h1{font-size:16px;border-left:4px solid var(--brand);padding-left:10px;margin:18px 0 10px;
    color:var(--brand-deep);}
  .md h2{font-size:15px;margin:16px 0 8px;color:var(--brand-deep);}
  .md h3{font-size:14px;margin:14px 0 6px;color:#1e40af;}
  .md p{margin:8px 0;}
  .md ul,.md ol{padding-left:22px;margin:8px 0;}
  .md li{margin:4px 0;}
  .md strong{color:#0f172a;}
  .md a{color:var(--brand);}
  .md hr{border:none;border-top:1px dashed var(--line);margin:16px 0;}
  .md blockquote{margin:10px 0;padding:8px 12px;background:#f4f8ff;
    border-left:3px solid var(--brand);border-radius:0 8px 8px 0;color:#334155;}
  .md table{border-collapse:separate;border-spacing:0;width:100%;margin:10px 0;font-size:12.5px;
    border:1px solid var(--line);border-radius:10px;overflow:hidden;}
  .md th{background:#f1f6ff;color:var(--brand-deep);font-weight:600;text-align:left;}
  .md td,.md th{padding:7px 10px;border-bottom:1px solid var(--line);}
  .md tr:last-child td{border-bottom:none;}
  .md tr:nth-child(even) td{background:#fafcff;}
  .md pre{background:#0f172a;color:#e2e8f0;padding:12px 14px;border-radius:10px;overflow:auto;
    font-size:12px;line-height:1.65;}
  .md pre code{background:transparent;color:inherit;padding:0;font-size:12px;}
  .md code{background:#eef2f7;color:var(--brand-deep);padding:2px 6px;border-radius:6px;
    font-size:12.5px;font-family:Consolas,"Cascadia Mono",monospace;}
  .askq{background:linear-gradient(120deg,#eef4ff,#f6faff);border-left:3px solid var(--brand);
    padding:8px 12px;border-radius:0 10px 10px 0;margin:12px 0;font-weight:600;color:var(--brand-deep);}
"""

_MAIN_HTML = r"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8">
__VENDOR__
<style>
__THEME__
  #bar{display:flex;align-items:center;gap:8px;padding:9px 12px;flex-wrap:wrap;
    background:linear-gradient(120deg,#0b3a8c,#1d4ed8 55%,#0ea5e9);color:#fff;
    box-shadow:0 2px 12px rgba(11,58,140,.28);position:relative;z-index:2;}
  #brand{font-size:13.5px;font-weight:700;letter-spacing:.4px;white-space:nowrap;}
  #badge{font-size:11.5px;padding:3px 10px;border-radius:999px;background:rgba(255,255,255,.18);
    border:1px solid rgba(255,255,255,.28);white-space:nowrap;}
  #bar .sp{flex:1;}
  #thumbbox{display:none;padding:8px 14px 0;}
  #thumb{width:100%;border:1px solid var(--line);border-radius:12px;max-height:150px;
    object-fit:contain;background:#fff;box-shadow:var(--shadow);}
  #status{display:none;padding:14px 16px;color:var(--muted);font-size:13px;}
  #c{padding:6px 16px 92px;font-size:14px;line-height:1.8;overflow-wrap:break-word;}
  #askbar{position:fixed;left:0;right:0;bottom:0;padding:10px 12px 12px;
    background:linear-gradient(to top,rgba(247,249,252,.99),rgba(247,249,252,.86));
    border-top:1px solid var(--line);}
  .askwrap{display:flex;gap:8px;align-items:center;background:#fff;border:1px solid var(--line);
    border-radius:999px;padding:4px 4px 4px 15px;box-shadow:var(--shadow);transition:box-shadow .15s,border-color .15s;}
  .askwrap:focus-within{border-color:var(--brand);box-shadow:0 0 0 4px var(--ring);}
  #ask{flex:1;border:none;outline:none;font-size:13px;padding:7px 0;background:transparent;
    font-family:inherit;min-width:0;color:var(--ink);}
  #askbtn{border:none;border-radius:999px;background:linear-gradient(135deg,#1d4ed8,#0ea5e9);
    color:#fff;font-size:12.5px;padding:8px 18px;cursor:pointer;font-weight:600;
    font-family:inherit;transition:filter .15s,transform .1s;}
  #askbtn:hover{filter:brightness(1.1);}
  #askbtn:active{transform:scale(.96);}
  .maths{display:inline;}
</style>
</head>
<body>
<div id="bar">
  <span id="brand">🐋 鲸鲸报点读机</span>
  <span id="badge">就绪</span>
  <span class="sp"></span>
  <button class="tb" onclick="api('copy_answer')" title="复制完整讲解">复制</button>
  <button class="tb" onclick="api('more_detail')" title="换更基础的方式再讲一遍">细讲</button>
  <button class="tb" onclick="api('read_paper')" title="拖入或选择论文,通读全文">通读</button>
  <button class="tb" onclick="api('toggle_side')" title="显示/隐藏相关小窗">相关</button>
  <button class="tb" onclick="api('open_settings')" title="键位设置 / 快捷键">⌨</button>
  <button class="tb ghost" onclick="api('open_config')" title="打开配置文件 config.json">⚙</button>
  <button class="tb ghost" onclick="api('hide')" title="隐藏(Esc)">✕</button>
</div>
<div id="thumbbox"><img id="thumb" alt=""></div>
<div id="status"><span class="spin"></span>正在讲解,请稍候…</div>
<div id="c" class="md"></div>
<div id="askbar">
  <div class="askwrap">
    <input id="ask" type="text" autocomplete="off"
           placeholder="就这里追问你自己的问题,回车发送(按 / 聚焦)">
    <button id="askbtn" onclick="askSend()">发送</button>
  </div>
</div>
<script>
__RENDER_JS__
const c = document.getElementById('c');
const status = document.getElementById('status');
function api(name){ try{ pywebview.api[name](); }catch(e){} }
function newQuery(badge, thumb){
  document.getElementById('badge').textContent = badge;
  const tb = document.getElementById('thumbbox');
  if(thumb){ document.getElementById('thumb').src = thumb; tb.style.display='block'; }
  else { tb.style.display='none'; }
  c.innerHTML=''; status.style.display='block';
}
function update(text, final){
  c.innerHTML = toHtml(text); renderMath(c);
  status.style.display='none';
  c.scrollTop = final ? 0 : c.scrollHeight;
}
function askSend(){
  const el = document.getElementById('ask');
  const q = (el.value || '').trim();
  if(!q) return;
  el.value = '';
  try{ pywebview.api.ask(q); }catch(e){}
}
document.getElementById('ask').addEventListener('keydown', function(e){
  if(e.key === 'Enter'){ e.preventDefault(); askSend(); }
});
window.addEventListener('keydown', function(e){
  if(e.key==='Escape'){ try{pywebview.api.hide();}catch(err){} }
  if(e.key==='/' && document.activeElement !== document.getElementById('ask')){
    e.preventDefault();
    document.getElementById('ask').focus();
  }
});
window.__pageReady = true;
</script>
</body>
</html>"""

_SIDE_HTML = r"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8">
__VENDOR__
<style>
__THEME__
  #bar{display:flex;align-items:center;gap:8px;padding:9px 12px;
    background:linear-gradient(120deg,#0b3a8c,#1d4ed8 55%,#0ea5e9);color:#fff;
    box-shadow:0 2px 12px rgba(11,58,140,.28);position:sticky;top:0;z-index:2;}
  #sbrand{font-size:13px;font-weight:700;letter-spacing:.4px;}
  #bar .sp{flex:1;}
  #list{padding:12px 12px 16px;overflow-y:auto;height:calc(100% - 41px);
    display:flex;flex-direction:column;gap:10px;}
  .card{background:var(--card);border:1px solid var(--line);border-radius:14px;overflow:hidden;
    box-shadow:0 2px 10px rgba(15,40,90,.05);transition:box-shadow .15s,transform .15s;}
  .card:hover{box-shadow:0 7px 20px rgba(15,40,90,.11);transform:translateY(-1px);}
  .chead{display:flex;justify-content:space-between;align-items:center;gap:8px;padding:10px 12px;
    cursor:pointer;font-size:13px;font-weight:600;color:var(--brand-deep);
    background:linear-gradient(120deg,#eef4ff,#f7faff);border-left:4px solid transparent;
    transition:border-color .15s;}
  .card.open .chead{border-left-color:var(--brand);}
  .ct{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
  .ctime{font-weight:500;color:#94a3b8;font-size:11px;background:#fff;border:1px solid var(--line);
    padding:1px 8px;border-radius:999px;white-space:nowrap;flex:none;}
  .timg{display:block;width:100%;max-height:92px;object-fit:contain;background:#fff;
    border-bottom:1px solid var(--line);cursor:pointer;}
  .cbody{display:none;padding:10px 14px 14px;font-size:12.5px;line-height:1.75;overflow-wrap:break-word;}
  .card.open .cbody{display:block;}
  .rel{border-top:1px dashed var(--line);margin-top:10px;padding-top:8px;}
  .rel-h{font-size:11.5px;color:var(--brand);font-weight:700;margin-bottom:4px;
    display:inline-block;background:#eef4ff;padding:2px 9px;border-radius:999px;}
  .empty{color:#94a3b8;font-size:13px;text-align:center;padding:52px 24px;line-height:2.1;}
  .empty .whale{font-size:42px;display:block;margin-bottom:12px;}
  .maths{display:inline;}
</style>
</head>
<body>
<div id="bar"><span id="sbrand">📌 相关小窗</span><span class="sp"></span>
<button class="tb" onclick="api('side_clear')" title="清空所有卡片">清空</button>
<button class="tb" onclick="api('open_history')" title="打开历史记录文件夹">历史</button>
<button class="tb ghost" onclick="api('side_hide')" title="隐藏(Esc)">✕</button>
</div>
<div id="list"></div>
<script>
__RENDER_JS__
function api(name){ try{ pywebview.api[name](); }catch(e){} }
let data = [];
let maxSeen = 0;
const openIds = new Set();
const list = document.getElementById('list');
function toggle(id){ if(openIds.has(id)){ openIds.delete(id); } else { openIds.add(id); } draw(); }
function render(json){
  data = json || [];
  data.forEach(function(cd){ if(cd.id > maxSeen){ maxSeen = cd.id; openIds.add(cd.id); } });
  draw();
}
function draw(){
  if(!data.length){
    list.innerHTML = '<div class="empty"><span class="whale">🐋</span>'
      + '还没有点读记录。<br>用鼠标侧键或热键圈选/划词后,<br>讲解卡片会累积在这里,'
      + '<br>并自动整理相关概念、前置知识和检索关键词。</div>';
    return;
  }
  list.innerHTML = data.map(function(cd){
    const open = openIds.has(cd.id) ? ' open' : '';
    const rel = cd.related
      ? '<div class="rel"><div class="rel-h">🔗 相关</div>'+toHtml(cd.related)+'</div>'
      : (cd.related_pending ? '<div class="rel"><div class="rel-h">🔗 生成中…</div></div>' : '');
    return '<div class="card'+open+'">'
      +'<div class="chead" onclick="toggle('+cd.id+')"><span class="ct">'+escHtml(cd.title)
      +'</span><span class="ctime">'+escHtml(cd.time)+'</span></div>'
      +(cd.thumb ? '<img class="timg" src="'+cd.thumb+'" onclick="toggle('+cd.id+')">' : '')
      +'<div class="cbody md">'+toHtml(cd.main)+rel+'</div></div>';
  }).join('');
  renderMath(list);
}
window.addEventListener('keydown', function(e){
  if(e.key==='Escape'){ try{pywebview.api.side_hide();}catch(err){} }
});
window.__pageReady = true;
</script>
</body>
</html>"""

_SETTINGS_HTML = r"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8">
<style>
__THEME__
  #bar{display:flex;align-items:center;gap:8px;padding:9px 12px;
    background:linear-gradient(120deg,#0b3a8c,#1d4ed8 55%,#0ea5e9);color:#fff;
    box-shadow:0 2px 12px rgba(11,58,140,.28);}
  #sbrand{font-size:13px;font-weight:700;letter-spacing:.4px;}
  #bar .sp{flex:1;}
  #wrap{padding:14px 16px 22px;}
  .sec{font-size:12.5px;font-weight:700;color:var(--brand-deep);margin:14px 0 8px;
    border-left:3px solid var(--brand);padding-left:8px;}
  .krow{display:flex;align-items:center;gap:10px;padding:8px 10px;border:1px solid var(--line);
    border-radius:10px;margin-bottom:8px;background:#fff;}
  .krow .lab{flex:1;font-size:13px;}
  .combo{font-family:Consolas,monospace;font-size:12px;background:#eef4ff;color:var(--brand-deep);
    padding:3px 9px;border-radius:6px;border:1px solid #dbe7ff;}
  .rec{border:none;border-radius:999px;background:#eef2f7;color:#334155;font-size:12px;
    padding:5px 12px;cursor:pointer;min-width:64px;}
  .rec:hover{background:#dbe7ff;}
  .rec.on{background:#f59e0b;color:#fff;}
  .mrow{display:flex;align-items:center;justify-content:space-between;padding:8px 10px;
    border:1px solid var(--line);border-radius:10px;margin-bottom:8px;background:#fff;font-size:13px;}
  select{border:1px solid var(--line);border-radius:8px;padding:5px 8px;font-size:12.5px;
    background:#fff;color:var(--ink);font-family:inherit;}
  #hint{font-size:12px;color:var(--muted);line-height:1.8;margin-top:10px;}
  #msg{font-size:12.5px;margin-top:8px;min-height:18px;color:#15803d;font-weight:600;}
  #msg.bad{color:#b91c1c;}
  .foot{margin-top:8px;}
  .fbtn{border:none;border-radius:999px;background:#eef2f7;color:#334155;font-size:12.5px;
    padding:7px 16px;cursor:pointer;font-family:inherit;}
  .fbtn:hover{background:#dbe7ff;}
</style>
</head>
<body>
<div id="bar"><span id="sbrand">⌨ 键位设置</span><span class="sp"></span>
<button class="tb" onclick="api('open_config')" title="直接编辑 config.json">config.json</button>
<button class="tb ghost" onclick="api('settings_hide')" title="关闭(Esc)">✕</button></div>
<div id="wrap">
  <div class="sec">键盘快捷键</div>
  <div id="rows"></div>
  <div class="sec">鼠标侧键</div>
  <div class="mrow"><span>侧键1(后退键)</span>
    <select id="m1" onchange="setMouse('1', this.value)">
      <option value="region">圈选讲解</option>
      <option value="text">划词讲解</option>
      <option value="none">不拦截(保留原生后退)</option>
    </select></div>
  <div class="mrow"><span>侧键2(前进键)</span>
    <select id="m2" onchange="setMouse('2', this.value)">
      <option value="region">圈选讲解</option>
      <option value="text">划词讲解</option>
      <option value="none">不拦截(保留原生前进)</option>
    </select></div>
  <div id="hint">修改即时生效,无需重启。点击「录制」后直接按下想用的组合键;建议带
    Ctrl / Alt 或使用 F1–F12;Esc 取消录制。想手工编辑可点右上角 config.json。</div>
  <div id="msg"></div>
  <div class="foot"><button class="fbtn" onclick="resetAll()">恢复默认键位</button></div>
</div>
<script>
function api(name){ try{ pywebview.api[name](); }catch(e){} }
function esc(s){ return String(s == null ? '' : s)
  .replace(/&/g,'&amp;').replace(/</g,'&lt;'); }
function msg(t, bad){
  const m = document.getElementById('msg');
  m.textContent = t || '';
  m.className = bad ? 'bad' : '';
}
let rowsData = [];
function render(rows, m1, m2){
  if(rows){ rowsData = rows; }
  document.getElementById('rows').innerHTML = rowsData.map(function(r){
    return '<div class="krow"><span class="lab">' + esc(r.label) + '</span>'
      + '<span class="combo">' + esc(r.combo) + '</span>'
      + '<button class="rec" id="b-' + r.action + '" onclick="rec(\'' + r.action + '\')">录制</button></div>';
  }).join('');
  if(m1){ document.getElementById('m1').value = m1; }
  if(m2){ document.getElementById('m2').value = m2; }
}
let recording = null;
function rec(action){
  if(recording === action){ stopRec(); msg('已取消录制'); return; }
  recording = action;
  const b = document.getElementById('b-' + action);
  if(b){ b.textContent = '按下中…'; b.className = 'rec on'; }
  msg('请按下新的组合键…(Esc 取消)');
  try{ pywebview.api.begin_record(); }catch(e){}
}
function stopRec(){
  if(recording){
    const b = document.getElementById('b-' + recording);
    if(b){ b.textContent = '录制'; b.className = 'rec'; }
  }
  recording = null;
  try{ pywebview.api.cancel_record(); }catch(e){}
}
function buildCombo(e){
  const mods = [];
  if(e.ctrlKey){ mods.push('ctrl'); }
  if(e.altKey){ mods.push('alt'); }
  if(e.shiftKey){ mods.push('shift'); }
  if(e.metaKey){ mods.push('windows'); }
  let k = String(e.key || '').toLowerCase();
  if(['control','alt','shift','meta'].indexOf(k) >= 0){ return ''; }
  if(k === ' '){ k = 'space'; }
  const map = {arrowup:'up', arrowdown:'down', arrowleft:'left', arrowright:'right',
               pageup:'page up', pagedown:'page down'};
  k = map[k] || k;
  if(mods.length === 0 && !/^f([1-9]|1\d|2[0-4])$/.test(k)){ return ''; }
  return mods.concat([k]).join('+');
}
window.addEventListener('keydown', function(e){
  if(!recording){
    if(e.key === 'Escape'){ try{pywebview.api.settings_hide();}catch(err){} }
    return;
  }
  e.preventDefault();
  e.stopPropagation();
  if(e.key === 'Escape'){ stopRec(); msg('已取消录制'); return; }
  const combo = buildCombo(e);
  if(!combo){ msg('需要至少一个修饰键(或使用 F1–F24)', true); return; }
  const action = recording;
  recording = null;
  pywebview.api.set_binding(action, combo).then(function(res){
    const b = document.getElementById('b-' + action);
    if(b){ b.textContent = '录制'; b.className = 'rec'; }
    if(res && res.ok){
      msg('✓ 已保存:' + res.combo + '(即时生效)');
    } else {
      msg('✗ ' + ((res && res.msg) || '保存失败,已还原旧键位'), true);
      try{ pywebview.api.cancel_record(); }catch(err){}
    }
    render(res && res.rows ? res.rows : null);
  });
});
function setMouse(side, mode){
  pywebview.api.set_mouse(side, mode).then(function(res){
    msg(res && res.ok ? '✓ 侧键设置已保存' : ('✗ ' + ((res && res.msg) || '保存失败')),
        !(res && res.ok));
    render(res && res.rows ? res.rows : null);
  });
}
function resetAll(){
  pywebview.api.reset_bindings().then(function(res){
    msg('✓ 已恢复默认键位');
    pywebview.api.get_bindings().then(function(d){ render(d.rows, d.mouse1, d.mouse2); });
  });
}
function applyData(data){ render(data.rows, data.mouse1, data.mouse2); }
window.__pageReady = true;
</script>
</body>
</html>"""

MAIN_HTML = (_MAIN_HTML
             .replace("__VENDOR__", _VENDOR)
             .replace("__THEME__", _THEME_CSS)
             .replace("__RENDER_JS__", RENDER_JS)
             .replace("__VERSION__", __version__))
SIDE_HTML = (_SIDE_HTML
             .replace("__VENDOR__", _VENDOR)
             .replace("__THEME__", _THEME_CSS)).replace("__RENDER_JS__", RENDER_JS)
SETTINGS_HTML = _SETTINGS_HTML.replace("__THEME__", _THEME_CSS)
