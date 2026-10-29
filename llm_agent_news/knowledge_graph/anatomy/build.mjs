// Anatomy traceable graph builder.
// Input: ../nodes.csv and ../edges.csv. Output: ../graph.svg and ../graph.html.
// Run from any directory with Node 20+: node D:/AgentProject2026/llm_agent_news/knowledge_graph/anatomy/build.mjs
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import * as k from './kit/iso-kit.mjs';

const here = dirname(fileURLToPath(import.meta.url));
const graph = dirname(here);
const read = (name) => readFileSync(join(graph, name), 'utf8');
const csv = (text) => {
  const rows = []; let row = []; let cell = ''; let quoted = false;
  for (let i = 0; i < text.length; i++) { const c = text[i];
    if (c === '"') { if (quoted && text[i + 1] === '"') { cell += '"'; i++; } else quoted = !quoted; }
    else if (c === ',' && !quoted) { row.push(cell); cell = ''; }
    else if ((c === '\n' || c === '\r') && !quoted) { if (c === '\r' && text[i + 1] === '\n') i++; row.push(cell); cell = ''; if (row.some(Boolean)) rows.push(row); row = []; }
    else cell += c;
  }
  if (cell || row.length) { row.push(cell); rows.push(row); }
  const [head, ...body] = rows; return body.map(values => Object.fromEntries(head.map((h, i) => [h, values[i] ?? ''])));
};
const esc = (s) => String(s).replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;').replaceAll('"', '&quot;');
const nodes = csv(read('nodes.csv')); const edges = csv(read('edges.csv'));
const ids = new Set(nodes.map(n => n.id));
if (ids.size !== nodes.length) throw new Error('duplicate node id');
for (const e of edges) if (!ids.has(e.source) || !ids.has(e.target)) throw new Error(`dangling edge ${e.source} -> ${e.target}`);
const edgeKeys = new Set(edges.map(e => `${e.source}|${e.target}|${e.relation}`));
if (edgeKeys.size !== edges.length) throw new Error('duplicate edge');
const types = [...new Set(nodes.map(n => n.type))];
const colors = { Topic:'#a78bfa', News:'#60a5fa', Paper:'#34d399', Benchmark:'#fbbf24', Dataset:'#fb923c', Method:'#f87171', Protocol:'#22d3ee', Organization:'#94a3b8' };
const cols = Math.max(4, Math.ceil(Math.sqrt(nodes.length / 2))); const cardW = 236; const cardH = 72; const gapX = 26; const gapY = 20;
const width = cols * (cardW + gapX) + 100; const rows = Math.ceil(nodes.length / cols); const height = Math.max(720, rows * (cardH + gapY) + 180);
const pos = new Map(nodes.map((n, i) => [n.id, { x: 50 + (i % cols) * (cardW + gapX), y: 110 + Math.floor(i / cols) * (cardH + gapY) }]));
const wires = edges.map((e, i) => { const a = pos.get(e.source), b = pos.get(e.target); const ax = a.x + cardW / 2, ay = a.y + cardH / 2, bx = b.x + cardW / 2, by = b.y + cardH / 2; const mid = (ax + bx) / 2; return `<path class="edge" data-edge-id="e${i}" d="M${ax},${ay} C${mid},${ay} ${mid},${by} ${bx},${by}"/><text class="edge-label" x="${mid}" y="${(ay + by) / 2 - 3}">${esc(e.relation)}</text>`; }).join('');
const cards = nodes.map(n => { const p = pos.get(n.id); const c = colors[n.type] ?? '#d4d4d4'; return `<a class="node" data-node-id="${esc(n.id)}" data-type="${esc(n.type)}" href="${esc(n.source)}" target="_blank" rel="noreferrer"><rect x="${p.x}" y="${p.y}" width="${cardW}" height="${cardH}" rx="10" stroke="${c}"/><text x="${p.x + 14}" y="${p.y + 21}" class="type" fill="${c}">${esc(n.type)}</text><text x="${p.x + 14}" y="${p.y + 46}" class="label">${esc(n.label.length > 29 ? n.label.slice(0, 28) + '…' : n.label)}</text></a>`; }).join('');
const legend = types.map(t => `<span><i style="background:${colors[t] ?? '#d4d4d4'}"></i>${esc(t)}</span>`).join('');
const body = `<title id="title">Agent 资讯可追溯知识图谱</title><desc id="desc">来源、资讯、模型方法、论文、主题和组织的关系图；每个节点可点击打开来源。</desc><style>svg{background:#101114;font-family:system-ui,sans-serif}.title{fill:#f4f4f5;font-size:24px;font-weight:700}.subtitle{fill:#a1a1aa;font-size:13px}.edge{fill:none;stroke:#52525b;stroke-width:1.2;opacity:.65}.edge-label{fill:#71717a;font-size:9px;text-anchor:middle}.node rect{fill:#18181b;stroke-width:2}.node:hover rect,.node:focus rect{fill:#27272a;stroke-width:4}.node .type{font-size:11px}.node .label{fill:#e4e4e7;font-size:13px}</style><text x="34" y="38" class="title">Agent 资讯可追溯知识图谱｜Anatomy</text><text x="34" y="62" class="subtitle">节点可点击来源；边标签对应 CSV relation；完整证据索引见下方 HTML。</text><g class="legend" transform="translate(34,78)">${legend}</g><g>${wires}</g><g>${cards}</g>`;
const svg = k.figureSvg({ width, height, label:'Agent 资讯可追溯知识图谱', body, standalone:true });
writeFileSync(join(graph, 'graph.svg'), svg);
const nodeJson = JSON.stringify(nodes).replaceAll('<','\\u003c'); const edgeJson = JSON.stringify(edges).replaceAll('<','\\u003c');
const rowsHtml = edges.map((e, i) => `<tr><td>${esc(e.source)}</td><td>${esc(e.relation)}</td><td>${esc(e.target)}</td><td>${esc(e.evidence)}</td></tr>`).join('');
const script = `const nodes=${nodeJson}; const edges=${edgeJson}; const select=document.querySelector('#type'); const cards=[...document.querySelectorAll('[data-node-id]')]; select.addEventListener('change',()=>cards.forEach(x=>x.hidden=select.value&&x.dataset.type!==select.value)); document.querySelector('#count').textContent=nodes.length+' nodes · '+edges.length+' relations';`;
const htmlBody = `<section class="hero"><h1>Agent 资讯可追溯知识图谱</h1><p>使用 Anatomy 本地 kit 生成。筛选节点类型，点击节点打开一手来源；关系索引保留原始 evidence。</p><label>节点类型 <select id="type"><option value="">全部</option>${types.map(t => `<option>${esc(t)}</option>`).join('')}</select></label><span id="count"></span></section><div class="figure">${svg}</div><section><h2>关系与证据索引</h2><table><thead><tr><th>source</th><th>relation</th><th>target</th><th>evidence</th></tr></thead><tbody>${rowsHtml}</tbody></table></section>`;
const page = k.pageHtml({ title:'Agent 资讯可追溯知识图谱', theme:'dark', width:1500, body:htmlBody, script });
writeFileSync(join(graph, 'graph.html'), page.replace('<html lang="en">','<html lang="zh-CN">'));
const sha = (file) => createHash('sha256').update(readFileSync(file)).digest('hex');
const provenance = { anatomy:{ upstream:'https://github.com/wheresryan22/anatomy', commit:'1482e8469b0a9e0d8cc18ea2740a01423d29ae80', kit_sha256:sha(join(here,'kit/iso-kit.mjs')) }, build:{ entry:'anatomy/build.mjs', build_sha256:sha(join(here,'build.mjs')), node:process.version, outputs:['../graph.svg','../graph.html'] }, inputs:{ nodes_sha256:sha(join(graph,'nodes.csv')), edges_sha256:sha(join(graph,'edges.csv')) }, scope:{ node_count:nodes.length, edge_count:edges.length, full_index_in_html:true }, nodes:Object.fromEntries(nodes.map(n=>[n.id,{source:n.source,type:n.type}])), edges:edges.map(e=>({source:e.source,target:e.target,relation:e.relation,evidence:e.evidence})) };
writeFileSync(join(here, 'provenance.json'), JSON.stringify(provenance, null, 2) + '\n');
console.log(`Anatomy graph built: ${nodes.length} nodes, ${edges.length} edges`);
