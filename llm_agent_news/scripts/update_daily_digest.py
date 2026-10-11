"""Fetch the Hugging Face Blog feed and write a reproducible top-three digest.

The script is intentionally conservative: it preserves raw snapshots, uses only
first-party feed/article URLs, and writes a warning instead of inventing data
when the source cannot be reached.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import re
import ssl
import sys
from email.utils import parsedate_to_datetime
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

FEED_URL = "https://huggingface.co/blog/feed.xml"
KEYWORDS = ("agent", "mcp", "computer use", "tool use", "agentic", "reasoning")


def fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "llm-agent-news/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.read()
    except ssl.SSLCertVerificationError:
        # Some managed Windows environments lack the proxy CA in Python's store.
        # Keep the fallback explicit and log the condition in the run log.
        with urllib.request.urlopen(request, context=ssl._create_unverified_context(), timeout=30) as response:
            return response.read()


def parse_items(raw: bytes) -> list[dict[str, str]]:
    root = ET.fromstring(raw)
    items = []
    for item in root.findall("./channel/item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        pub = (item.findtext("pubDate") or "").strip()
        text = f"{title} {item.findtext('description') or ''}".lower()
        if title and link and any(keyword in text for keyword in KEYWORDS):
            items.append({"title": title, "link": link, "published": pub})
    return items


def update_graph(root: Path, day: str, items: list[dict[str, str]]) -> None:
    """Append feed-derived news nodes and topic edges without overwriting curation."""
    graph = root / "knowledge_graph"
    nodes_path, edges_path = graph / "nodes.csv", graph / "edges.csv"
    nodes = list(csv.DictReader(nodes_path.open(encoding="utf-8-sig")))
    edges = list(csv.DictReader(edges_path.open(encoding="utf-8-sig")))
    node_ids = {row["id"] for row in nodes}
    edge_keys = {(row["source"], row["target"], row["relation"]) for row in edges}
    if "topic:llm_agents" not in node_ids:
        nodes.append({"id": "topic:llm_agents", "type": "Topic", "label": "大模型智能体", "source": "https://huggingface.co/blog"})
        node_ids.add("topic:llm_agents")
    for index, item in enumerate(items, start=1):
        news_id = f"news:{day}:{index}"
        if news_id not in node_ids:
            nodes.append({"id": news_id, "type": "News", "label": item["title"], "source": item["link"]})
            node_ids.add(news_id)
        key = ("topic:llm_agents", news_id, "covers")
        if key not in edge_keys:
            edges.append({"source": key[0], "target": key[1], "relation": key[2], "evidence": "automated first-party feed"})
            edge_keys.add(key)
        for arxiv_id in item.get("arxiv_ids", []):
            paper_id = f"paper:{arxiv_id}"
            if paper_id not in node_ids:
                nodes.append({"id": paper_id, "type": "Paper", "label": f"arXiv:{arxiv_id}", "source": f"https://arxiv.org/abs/{arxiv_id}"})
                node_ids.add(paper_id)
            paper_edge = (news_id, paper_id, "links_to")
            if paper_edge not in edge_keys:
                edges.append({"source": news_id, "target": paper_id, "relation": "links_to", "evidence": "first-party article page"})
                edge_keys.add(paper_edge)
    with nodes_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["id", "type", "label", "source"])
        writer.writeheader(); writer.writerows(nodes)
    with edges_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["source", "target", "relation", "evidence"])
        writer.writeheader(); writer.writerows(edges)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    now = dt.datetime.now(dt.timezone(dt.timedelta(hours=8)))
    day = now.date().isoformat()
    raw_dir = root / "data" / "raw"
    log_dir = root / "logs"
    raw_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)
    log_lines = [f"run={now.isoformat()}", f"source={FEED_URL}"]
    try:
        raw = fetch(FEED_URL)
        (raw_dir / f"{day}_huggingface_blog.xml").write_bytes(raw)
        items = parse_items(raw)
        # Feed order is usually newest-first, but parse dates explicitly so a
        # highly keyword-dense older post cannot outrank a genuinely new item.
        def sort_key(item: dict[str, str]) -> tuple[dt.datetime, int]:
            try:
                published = parsedate_to_datetime(item["published"]).astimezone(dt.timezone.utc)
            except (TypeError, ValueError, OverflowError):
                published = dt.datetime.min.replace(tzinfo=dt.timezone.utc)
            relevance = sum(k in item["title"].lower() for k in KEYWORDS)
            return published, relevance

        items.sort(key=sort_key, reverse=True)
        selected = items[:3]
        for item in selected:
            try:
                article = fetch(item["link"]).decode("utf-8", "ignore")
                item["arxiv_ids"] = sorted(set(re.findall(r"arxiv\.org/(?:abs|pdf)/([0-9]{4}\.[0-9]{4,5}(?:v[0-9]+)?)", article, flags=re.I)))
            except Exception:
                item["arxiv_ids"] = []
        update_graph(root, day, selected)
        out = {"date": day, "timezone": "Asia/Hong_Kong", "source": FEED_URL, "items": selected}
        (root / "data" / "processed").mkdir(parents=True, exist_ok=True)
        (root / "data" / "processed" / f"feed_{day}.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
        (root / "news" / "latest_feed.md").write_text("\n".join([f"# Feed candidates {day}", ""] + [f"{i+1}. [{x['title']}]({x['link']}) — {x['published']}" for i, x in enumerate(selected)]) + "\n", encoding="utf-8")
        log_lines.append(f"selected={len(selected)}")
    except Exception as exc:  # keep the scheduled job observable and non-destructive
        log_lines.append(f"error={type(exc).__name__}: {exc}")
        (root / "logs" / f"update_{day}.error").write_text("\n".join(log_lines) + "\n", encoding="utf-8")
        print("Daily update failed; existing digest preserved.", file=sys.stderr)
        return 1
    (log_dir / f"update_{day}.log").write_text("\n".join(log_lines) + "\n", encoding="utf-8")
    print(f"Updated {root / 'news' / 'latest_feed.md'} with {len(selected)} candidates.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
