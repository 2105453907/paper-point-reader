// 公式渲染管线离线测试(Node):从 diandu/webui.py 提取 RENDER_JS(与打包运行的是同一份代码),
// 验证:\(..\) 不被 marked 吃掉、_ 和 * 不破坏公式、$$ 与 \\ 换行保留、LaTeX 环境可转换、HTML 转义安全。
// 运行: node tests/run_render_test.js
const fs = require('fs');
const path = require('path');

const root = path.join(__dirname, '..');
const py = fs.readFileSync(path.join(root, 'diandu', 'webui.py'), 'utf8');
const m = py.match(/\/\*==RENDER-JS-BEGIN==\*\/([\s\S]*?)\/\*==RENDER-JS-END==\*\//);
if (!m) { console.log('RENDER-TEST: FAIL 未在 webui.py 中找到 RENDER_JS 块'); process.exit(1); }
const js = m[1];

const { marked } = require('./marked.min.js');
const api = new Function('window', 'marked',
  js + '\nreturn {toHtml: toHtml, escHtml: escHtml, MATH_RE: MATH_RE};')({ marked }, marked);

let pass = 0, fail = 0;
function check(name, cond, extra) {
  if (cond) { pass++; console.log('  PASS  ' + name); }
  else { fail++; console.log('  FAIL  ' + name + (extra ? '  -> ' + extra : '')); }
}

// 0) 先复现旧行为(证据)
const rawOld = marked.parse('能量为 \\(E=mc^2\\),且 \\(f_l\\) 是激活。');
console.log('[对照] marked 直接处理 \\(..\\) 的结果:', JSON.stringify(rawOld.slice(0, 60)));
check('旧管线确实会破坏 \\(..\\)(证明问题存在)', rawOld.indexOf('\\(') < 0);

// 1) \\(..\\) 保护后规范化为 $..$(KaTeX 两种都认,规范化为 $ 便于统一)
let h = api.toHtml('能量为 \\(E=mc^2\\),其中 \\(m\\) 是质量。');
check('\\(E=mc^2\\) 内容保留(规范化为 $..$)', h.indexOf('$E=mc^2$') >= 0, h.slice(0, 100));
check('不会被降级成裸括号', h.indexOf('(E=mc^2)') < 0);
check('\$m\$ 保留', h.indexOf('$m$') >= 0);

// 2) 下划线与多个公式共存
h = api.toHtml('设 \\(f_l\\) 与 \\(W_1, W_2\\)、\\(b_l\\) 为第 l 层参数,激活 \\(\\sigma_l(z)\\)。');
check('$f_l$ 完整保留', h.indexOf('$f_l$') >= 0, h.slice(0, 120));
check('未生成伪 <em> 标签', h.indexOf('<em>') < 0, h.slice(0, 120));
check('$W_1, W_2$ 完整保留', h.indexOf('$W_1, W_2$') >= 0);
check('$\\sigma_l(z)$ 保留', h.indexOf('$\\sigma_l(z)$') >= 0);

// 3) $$ 块与 \\ 换行
h = api.toHtml('$$\na &= b \\\\\nc &= d\n$$');
check('$$ 块保留', h.indexOf('$$') >= 0);
check('LaTeX 换行 \\\\ 保留', h.indexOf('\\\\') >= 0, JSON.stringify(h.slice(0, 80)));

// 4) LaTeX 环境转换
h = api.toHtml('\\begin{equation}E=mc^2\\end{equation}');
check('equation 环境 -> $$..$$', h.indexOf('$$E=mc^2$$') >= 0, h.slice(0, 80));
h = api.toHtml('\\begin{align}a &= b \\\\ c &= d\\end{align}');
check('align 环境 -> aligned', h.indexOf('\\begin{aligned}') >= 0, h.slice(0, 120));
check('align 的 &= 修正为 &=', h.indexOf('&=&') < 0);

// 5) 单 $ 行内公式
h = api.toHtml('公式 $f_l(x)$ 的值');
check('$f_l(x)$ 保留', h.indexOf('$f_l(x)$') >= 0, h.slice(0, 80));

// 6) HTML 转义安全(公式里的 < > &)
h = api.toHtml('条件 \\(a < b \\& c > d\\) 成立');
check('公式内 < 被转义', h.indexOf('&lt;') >= 0, h.slice(0, 120));
check('公式内 & 被转义', h.indexOf('&amp;') >= 0);

// 7) 真实通读报告:数学片段数量守恒、无伪标签、片段内无 HTML 注入
const files = fs.readdirSync(path.join(root, 'history')).filter(f => f.startsWith('通读-') && f.endsWith('.md')).sort();
if (files.length) {
  const src = fs.readFileSync(path.join(root, 'history', files[files.length - 1]), 'utf8');
  const oldHtml = marked.parse(src);
  const newHtml = api.toHtml(src);
  const count = (s, t) => s.split(t).length - 1;
  const segCount = (src.match(api.MATH_RE) || []).length;
  const spans = [...newHtml.matchAll(/<span class="maths">([\s\S]*?)<\/span>/g)].map(x => x[1]);
  check('真实报告数学片段数量守恒(' + segCount + ' 段)', spans.length === segCount,
        'spans=' + spans.length + ' seg=' + segCount);
  check('数学片段内无 HTML 注入', spans.every(s => s.indexOf('<') < 0),
        (spans.find(s => s.indexOf('<') >= 0) || '').slice(0, 60));
  check('数学片段非空', spans.every(s => s.trim().length > 0));
  console.log('  [对照] 旧管线该报告产生 <em> 伪标签:', count(oldHtml, '<em>'),
              '个;新管线:', count(newHtml, '<em>'), '个');
  check('新管线无伪 <em> 破坏', count(newHtml, '<em>') === 0);
}

console.log('RENDER-TEST: ' + (fail === 0 ? 'PASS' : 'FAIL') + '  (' + pass + ' 通过 / ' + fail + ' 失败)');
process.exit(fail === 0 ? 0 : 1);
