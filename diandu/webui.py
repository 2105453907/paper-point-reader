# -*- coding: utf-8 -*-
"""两个 WebView 窗口的内嵌页面(主弹窗 / 相关小窗)。

__VERSION__ 会在导入时替换为真实版本号。
"""
from . import __version__

_MAIN_HTML = """<!DOCTYPE html>
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
  #c{padding:6px 16px 24px;font-size:14px;line-height:1.75;overflow-wrap:break-word;}
  #c h1,#c h2,#c h3{font-size:1.05em;border-bottom:1px solid #eee;padding-bottom:2px;}
  #c pre{background:#f3f4f6;padding:10px;border-radius:8px;overflow:auto;font-size:12.5px;}
  #c code{background:#f3f4f6;padding:1px 4px;border-radius:4px;font-size:12.5px;}
  #c table{border-collapse:collapse;} #c td,#c th{border:1px solid #e5e7eb;padding:4px 8px;}
  .katex{font-size:1.02em;}
  .dots::after{content:"";animation:dots 1.2s steps(4,end) infinite;}
  @keyframes dots{0%{content:""}25%{content:"·"}50%{content:"··"}75%{content:"···"}}
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
<script>
const c = document.getElementById('c');
const status = document.getElementById('status');
function toHtml(t){
  try{ if(window.marked){ return marked.parse(t||''); } }catch(e){}
  return '<pre style="white-space:pre-wrap">'+String(t||'')
    .replace(/&/g,'&amp;').replace(/</g,'&lt;')+'</pre>';
}
function math(el){
  try{ if(window.renderMathInElement){
    renderMathInElement(el,{delimiters:[
      {left:'$$',right:'$$',display:true},
      {left:'\\\\[',right:'\\\\]',display:true},
      {left:'$',right:'$',display:false},
      {left:'\\\\(',right:'\\\\)',display:false}],throwOnError:false});
  } }catch(e){}
}
function newQuery(badge, thumb){
  document.getElementById('badge').textContent = badge;
  const tb = document.getElementById('thumbbox');
  if(thumb){ document.getElementById('thumb').src = thumb; tb.style.display='block'; }
  else { tb.style.display='none'; }
  c.innerHTML=''; status.style.display='block';
}
function update(text, final){
  c.innerHTML = toHtml(text); math(c);
  status.style.display='none';
  c.scrollTop = final ? 0 : c.scrollHeight;
}
window.addEventListener('keydown', e=>{
  if(e.key==='Escape'){ try{pywebview.api.hide();}catch(err){} }
});
window.__pageReady = true;
</script>
</body>
</html>"""

_SIDE_HTML = """<!DOCTYPE html>
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
let data = [];
let maxSeen = 0;
const openIds = new Set();
const list = document.getElementById('list');
function toHtml(t){
  try{ if(window.marked){ return marked.parse(t||''); } }catch(e){}
  return '<pre style="white-space:pre-wrap">'+String(t||'')
    .replace(/&/g,'&amp;').replace(/</g,'&lt;')+'</pre>';
}
function esc(s){ return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;'); }
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
      +'<div class="chead" onclick="toggle('+cd.id+')"><span class="ct">'+esc(cd.title)
      +'</span><span class="ctime">'+esc(cd.time)+'</span></div>'
      +(cd.thumb ? '<img class="timg" src="'+cd.thumb+'" onclick="toggle('+cd.id+')">' : '')
      +'<div class="cbody">'+toHtml(cd.main)+rel+'</div></div>';
  }).join('');
  try{ if(window.renderMathInElement){
    renderMathInElement(list,{delimiters:[
      {left:'$$',right:'$$',display:true},
      {left:'\\\\[',right:'\\\\]',display:true},
      {left:'$',right:'$',display:false},
      {left:'\\\\(',right:'\\\\)',display:false}],throwOnError:false});
  } }catch(e){}
}
window.addEventListener('keydown', function(e){
  if(e.key==='Escape'){ try{pywebview.api.side_hide();}catch(err){} }
});
window.__pageReady = true;
</script>
</body>
</html>"""

MAIN_HTML = _MAIN_HTML.replace("__VERSION__", __version__)
SIDE_HTML = _SIDE_HTML
