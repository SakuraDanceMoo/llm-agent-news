"""Build a deterministic, clickable SVG/HTML information relationship graph."""
from __future__ import annotations

import argparse
import csv
import html
import json
from pathlib import Path

COLORS = {
    "Topic": "#7c3aed", "News": "#2563eb", "Paper": "#059669",
    "Benchmark": "#d97706", "Dataset": "#ea580c", "Method": "#dc2626",
    "Protocol": "#0891b2", "Organization": "#475569",
}


def wrap(text: str, width: int = 18) -> list[str]:
    lines: list[str] = []
    line = ""
    for token in text.split():
        if len(line) + len(token) + 1 > width and line:
            lines.append(line)
            line = token
        else:
            line = f"{line} {token}".strip()
    if line:
        lines.append(line)
    return lines or [text]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    graph = root / "knowledge_graph"
    nodes = list(csv.DictReader((graph / "nodes.csv").open(encoding="utf-8-sig")))
    edges = list(csv.DictReader((graph / "edges.csv").open(encoding="utf-8-sig")))
    grouped: dict[str, list[dict[str, str]]] = {}
    for node in nodes:
        grouped.setdefault(node["type"], []).append(node)

    x_by_type = {"Topic": 120, "News": 350, "Paper": 580, "Benchmark": 820,
                 "Dataset": 820, "Method": 1050, "Protocol": 1050, "Organization": 1280}
    positions: dict[str, tuple[int, int]] = {}
    for kind, group in grouped.items():
        x = x_by_type.get(kind, 120)
        for i, node in enumerate(group):
            positions[node["id"]] = (x, 90 + i * 86)

    def esc(value: str) -> str:
        return html.escape(value, quote=True)

    svg = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="1450" height="900" viewBox="0 0 1450 900">',
        '<defs><marker id="arrow" markerWidth="10" markerHeight="10" refX="9" refY="3" orient="auto"><path d="M0,0 L0,6 L9,3 z" fill="#64748b"/></marker></defs>',
        '<rect width="100%" height="100%" fill="#f8fafc"/>',
        '<text x="28" y="34" font-family="Segoe UI,Arial" font-size="22" font-weight="700" fill="#0f172a">大模型智能体资讯知识图谱｜信息联系图</text>',
        '<text x="28" y="60" font-family="Segoe UI,Arial" font-size="13" fill="#475569">节点=资讯/论文/主题/方法/基准/组织；箭头=证据支持的关系；点击节点打开来源</text>',
    ]
    for edge in edges:
        if edge["source"] not in positions or edge["target"] not in positions:
            continue
        x1, y1 = positions[edge["source"]]
        x2, y2 = positions[edge["target"]]
        svg.append(f'<path d="M{x1 + 82},{y1} C{(x1+x2)//2},{y1} {(x1+x2)//2},{y2} {x2 - 82},{y2}" fill="none" stroke="#94a3b8" stroke-width="1.4" marker-end="url(#arrow)" opacity=".72"/>')
        svg.append(f'<text x="{(x1+x2)//2}" y="{(y1+y2)//2-4}" text-anchor="middle" font-family="Segoe UI,Arial" font-size="10" fill="#475569">{esc(edge["relation"])}</text>')
    for node in nodes:
        x, y = positions[node["id"]]
        color = COLORS.get(node["type"], "#64748b")
        label = wrap(node["label"])
        svg.append(f'<a href="{esc(node.get("source") or "#")}" target="_blank"><g class="node"><title>{esc(node["label"])} | {esc(node["type"])}</title><rect x="{x-82}" y="{y-30}" width="164" height="60" rx="12" fill="white" stroke="{color}" stroke-width="3"/><circle cx="{x-67}" cy="{y-14}" r="6" fill="{color}"/><text x="{x-55}" y="{y-10}" font-family="Segoe UI,Arial" font-size="10" fill="{color}">{esc(node["type"])}</text>')
        for j, line in enumerate(label[:3]):
            svg.append(f'<text x="{x}" y="{y+7+j*13}" text-anchor="middle" font-family="Segoe UI,Arial" font-size="11" fill="#0f172a">{esc(line)}</text>')
        svg.append('</g></a>')
    svg.append('</svg>')
    svg_text = "\n".join(svg)
    (graph / "graph.svg").write_text(svg_text, encoding="utf-8")
    payload = json.dumps({"nodes": nodes, "edges": edges}, ensure_ascii=False, indent=2)
    page = f'''<!doctype html><meta charset="utf-8"><title>Agent资讯推送知识图谱</title><style>body{{margin:0;background:#f8fafc;font-family:Segoe UI,Arial}}.wrap{{padding:18px}}svg{{max-width:100%;height:auto;border:1px solid #cbd5e1;border-radius:12px;background:white}}.node:hover rect{{fill:#eff6ff;stroke-width:5}}</style><div class="wrap">{svg_text}<details><summary>机器可读数据</summary><pre>{html.escape(payload)}</pre></details></div>'''
    (graph / "graph.html").write_text(page, encoding="utf-8")
    print(f"built {graph / 'graph.svg'} and {graph / 'graph.html'} ({len(nodes)} nodes, {len(edges)} edges)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
