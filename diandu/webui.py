# -*- coding: utf-8 -*-
"""两个 WebView 窗口的内嵌页面(主弹窗 / 相关小窗)。

__VERSION__ 与 __RENDER_JS__ 在导入时替换。
RENDER_JS 是共享的渲染工具(tests/run_render_test.js 会从本文件提取同一份代码做离线测试):
先摘出数学片段并按需转换 LaTeX 环境,再做 Markdown,最后放回并交给 KaTeX——
否则 marked 会把 \\( \\) 转义掉、把 _ 和 * 当作强调,公式就会以乱码形式漏渲染。
"""
from . import __version__

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

_MAIN_HTML = r"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.css">
<script src="https://cdn.jsdelivr.net/npm/marked@12.0.2/marked.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/contrib/auto-render.min.js"></script>
<style>
  html,body{margin:0;padding:0;height:100%;background:#fafaf9;color:#1f2937;
    font-family:"Microsoft YaHei","PingFang SC","Segoe UI",sans-serif;}
  #bar{display:flex;align-items:center;gap:8px;padding:8px 12px;background:#2563eb;color:#fff;}
  #badge{font-size:13px;font-weight:600;}
  #bar .sp{flex:1}
  .btn{border:none;border-radius:6px;background:rgba(255,255,255,.18);color:#fff;
    font-size:12px;padding:4px 10px;cursor:pointer;}
  .btn:hover{background:rgba(255,255,255,.35);}
  #status{padding:10px 14px;color:#6b7280;font-size:13px;display:none;}
  #thumbbox{display:none;padding:0 14px 6px;}
  #thumb{width:100%;border:1px solid #e5e7eb;border-radius:8px;max-height:140px;
    object-fit:contain;background:#fff;}
  #c{padding:6px 16px 84px;font-size:14px;line-height:1.75;overflow-wrap:break-word;}
  #c h1,#c h2,#c h3{font-size:1.05em;border-bottom:1px solid #eee;padding-bottom:2px;}
  #c pre{background:#f3f4f6;padding:10px;border-radius:8px;overflow:auto;font-size:12.5px;}
  #c code{background:#f3f4f6;padding:1px 4px;border-radius:4px;font-size:12.5px;}
  #c table{border-collapse:collapse;} #c td,#c th{border:1px solid #e5e7eb;padding:4px 8px;}
  .katex{font-size:1.02em;}
  .maths{display:inline;}
  .dots::after{content:"";animation:dots 1.2s steps(4,end) infinite;}
  @keyframes dots{0%{content:""}25%{content:"·"}50%{content:"··"}75%{content:"···"}}
  #askbar{position:fixed;left:0;right:0;bottom:0;display:flex;gap:8px;padding:10px 12px;
    background:#ffffff;border-top:1px solid #e5e7eb;box-sizing:border-box;}
  #ask{flex:1;border:1px solid #d1d5db;border-radius:8px;padding:8px 10px;font-size:13px;
    font-family:inherit;outline:none;min-width:0;}
  #ask:focus{border-color:#2563eb;box-shadow:0 0 0 3px rgba(37,99,235,.15);}
  #askbtn{border:none;border-radius:8px;background:#2563eb;color:#fff;font-size:13px;
    padding:8px 16px;cursor:pointer;white-space:nowrap;}
  #askbtn:hover{background:#1d4ed8;}
  .askq{background:#eff6ff;border-left:3px solid #2563eb;padding:6px 10px;border-radius:6px;
    margin:10px 0;font-weight:600;color:#1e3a8a;}
</style>
</head>
<body>
<div id="bar">
  <span id="badge">点读机 v__VERSION__</span><span class="sp"></span>
  <button class="btn" onclick="try{pywebview.api.copy_answer()}catch(e){}">复制</button>
  <button class="btn" onclick="try{pywebview.api.more_detail()}catch(e){}">再细讲</button>
  <button class="btn" onclick="try{pywebview.api.read_paper()}catch(e){}">通读</button>
  <button class="btn" onclick="try{pywebview.api.toggle_side()}catch(e){}">相关</button>
  <button class="btn" onclick="try{pywebview.api.open_config()}catch(e){}">设置</button>
  <button class="btn" onclick="try{pywebview.api.hide()}catch(e){}">隐藏</button>
</div>
<div id="thumbbox"><img id="thumb" alt=""></div>
<div id="status">正在讲解<span class="dots"></span></div>
<div id="c"></div>
<div id="askbar">
  <input id="ask" type="text" autocomplete="off"
         placeholder="就这里追问,例如:这个平方为什么要平方?(回车发送,按 / 聚焦)">
  <button id="askbtn" onclick="askSend()">问</button>
</div>
<script>
__RENDER_JS__
const c = document.getElementById('c');
const status = document.getElementById('status');
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
window.addEventListener('keydown', e=>{
  if(e.key==='Escape'){ try{pywebview.api.hide();}catch(err){} }
});
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
  if(e.key === '/' && document.activeElement !== document.getElementById('ask')){
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
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.css">
<script src="https://cdn.jsdelivr.net/npm/marked@12.0.2/marked.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/contrib/auto-render.min.js"></script>
<style>
  html,body{margin:0;padding:0;height:100%;background:#f5f7fb;color:#1f2937;
    font-family:"Microsoft YaHei","PingFang SC","Segoe UI",sans-serif;}
  #bar{display:flex;align-items:center;gap:8px;padding:8px 12px;background:#1e40af;color:#fff;}
  #bar b{font-size:13px;} #bar .sp{flex:1}
  .btn{border:none;border-radius:6px;background:rgba(255,255,255,.18);color:#fff;
    font-size:12px;padding:4px 10px;cursor:pointer;}
  .btn:hover{background:rgba(255,255,255,.35);}
  #list{padding:10px;overflow-y:auto;height:calc(100% - 37px);box-sizing:border-box;}
  .card{background:#fff;border:1px solid #e5e7eb;border-radius:10px;margin-bottom:10px;overflow:hidden;}
  .chead{display:flex;justify-content:space-between;align-items:center;gap:6px;padding:8px 10px;
    cursor:pointer;font-size:13px;font-weight:600;background:#eef2ff;color:#1e3a8a;}
  .chead:hover{background:#e0e7ff;}
  .ct{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
  .ctime{font-weight:400;color:#94a3b8;font-size:11px;white-space:nowrap;}
  .timg{display:block;width:100%;max-height:90px;object-fit:contain;background:#fff;cursor:pointer;}
  .cbody{display:none;padding:4px 12px 10px;font-size:12.5px;line-height:1.7;overflow-wrap:break-word;}
  .card.open .cbody{display:block;}
  .rel{border-top:1px dashed #e5e7eb;margin-top:8px;padding-top:6px;}
  .rel-h{font-size:12px;color:#1d4ed8;font-weight:600;margin-bottom:2px;}
  .empty{color:#94a3b8;font-size:13px;text-align:center;padding:40px 20px;line-height:2;}
  .cbody pre{background:#f3f4f6;padding:8px;border-radius:6px;overflow:auto;font-size:11.5px;}
  .cbody code{background:#f3f4f6;padding:1px 4px;border-radius:4px;font-size:11.5px;}
  .cbody table{border-collapse:collapse;} .cbody td,.cbody th{border:1px solid #e5e7eb;padding:3px 6px;}
  .katex{font-size:1.0em;}
  .maths{display:inline;}
</style>
</head>
<body>
<div id="bar"><b>📌 相关小窗</b><span class="sp"></span>
<button class="btn" onclick="try{pywebview.api.side_clear()}catch(e){}">清空</button>
<button class="btn" onclick="try{pywebview.api.open_history()}catch(e){}">历史</button>
<button class="btn" onclick="try{pywebview.api.side_hide()}catch(e){}">隐藏</button>
</div>
<div id="list"></div>
<script>
__RENDER_JS__
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
    list.innerHTML = '<div class="empty">还没有点读记录。<br><br>用鼠标侧键或热键圈选/划词后,<br>'
      +'这里会累积每次的讲解卡片,<br>并自动整理相关概念、前置知识和检索关键词。</div>';
    return;
  }
  list.innerHTML = data.map(function(cd){
    const open = openIds.has(cd.id) ? ' open' : '';
    const rel = cd.related
      ? '<div class="rel"><div class="rel-h">🔗 相关</div>'+toHtml(cd.related)+'</div>'
      : (cd.related_pending ? '<div class="rel"><div class="rel-h">🔗 相关内容生成中…</div></div>' : '');
    return '<div class="card'+open+'">'
      +'<div class="chead" onclick="toggle('+cd.id+')"><span class="ct">'+escHtml(cd.title)
      +'</span><span class="ctime">'+escHtml(cd.time)+'</span></div>'
      +(cd.thumb ? '<img class="timg" src="'+cd.thumb+'" onclick="toggle('+cd.id+')">' : '')
      +'<div class="cbody">'+toHtml(cd.main)+rel+'</div></div>';
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

MAIN_HTML = _MAIN_HTML.replace("__RENDER_JS__", RENDER_JS).replace("__VERSION__", __version__)
SIDE_HTML = _SIDE_HTML.replace("__RENDER_JS__", RENDER_JS)
