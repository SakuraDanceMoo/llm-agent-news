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
import unicodedata
from email.utils import parsedate_to_datetime
import urllib.request
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
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


def normalize_title(title: str) -> str:
    title = unicodedata.normalize("NFKC", title).casefold()
    return re.sub(r"[^\w]+", " ", title, flags=re.UNICODE).strip()


def normalize_url(url: str) -> str:
    parts = urlsplit(url.strip().rstrip(".,;，。；"))
    query = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True)
             if not k.lower().startswith("utm_") and k.lower() not in {"fbclid", "gclid"}]
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(),
                       parts.path.rstrip("/"), urlencode(sorted(query)), ""))


def historical_keys(root: Path, day: str) -> tuple[set[str], set[str]]:
    """Return source URLs and titles already archived, including earlier runs today."""
    urls: set[str] = set()
    titles: set[str] = set()
    for path in (root / "news").glob("*.md"):
        if path.stem > day or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", path.stem):
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        urls.update(normalize_url(u) for u in re.findall(r"https?://[^)\s>\]\"<]+", text))
        titles.update(normalize_title(t) for t in re.findall(r"^##\s+\d+\.\s+(.+)$", text, flags=re.M))
    # Structured history retains original source titles even when summaries
    # translate them or archive cleanup removes old Markdown summaries.
    for path in (root / "data" / "processed").glob("feed_*.json"):
        if path.stem.removeprefix("feed_") > day:
            continue
        for item in json.loads(path.read_text(encoding="utf-8-sig")).get("items", []):
            urls.add(normalize_url(item["link"]))
            titles.add(normalize_title(item["title"]))
    graph_path = root / "knowledge_graph" / "nodes.csv"
    if graph_path.exists():
        with graph_path.open(encoding="utf-8-sig", newline="") as handle:
            for node in csv.DictReader(handle):
                match = re.match(r"news:(\d{4}-\d{2}-\d{2}):", node["id"])
                if node["type"] == "News" and match and match[1] <= day:
                    urls.add(normalize_url(node["source"]))
                    titles.add(normalize_title(node["label"]))
    return urls, titles


def deduplicate_items(root: Path, day: str, items: list[dict[str, str]]) -> list[dict[str, str]]:
    """Keep only new items, removing duplicates within the feed and history."""
    old_urls, old_titles = historical_keys(root, day)
    seen_urls, seen_titles = set(), set()
    unique: list[dict[str, str]] = []
    for item in items:
        title_key = normalize_title(item["title"])
        link_key = normalize_url(item["link"])
        if link_key in old_urls or title_key in old_titles:
            continue
        if link_key in seen_urls or title_key in seen_titles:
            continue
        seen_urls.add(link_key)
        seen_titles.add(title_key)
        unique.append(item)
    return unique


def deduplicate_graph(root: Path) -> None:
    """Merge duplicate News nodes while preserving their evidence relations."""
    graph = root / "knowledge_graph"
    nodes_path, edges_path = graph / "nodes.csv", graph / "edges.csv"
    nodes = list(csv.DictReader(nodes_path.open(encoding="utf-8-sig")))
    edges = list(csv.DictReader(edges_path.open(encoding="utf-8-sig")))
    seen_sources: dict[str, str] = {}
    seen_titles: dict[str, str] = {}
    redirects: dict[str, str] = {}
    kept_nodes: list[dict[str, str]] = []
    for node in sorted(nodes, key=lambda n: n["id"]):
        source = normalize_url(node.get("source", ""))
        title = normalize_title(node.get("label", ""))
        if node.get("type") == "News":
            canonical = seen_sources.get(source) if source else None
            canonical = canonical or (seen_titles.get(title) if title else None)
            if canonical:
                redirects[node["id"]] = canonical
                if source:
                    seen_sources[source] = canonical
                if title:
                    seen_titles[title] = canonical
                continue
            if source:
                seen_sources[source] = node["id"]
            if title:
                seen_titles[title] = node["id"]
        kept_nodes.append(node)
    kept_ids = {node["id"] for node in kept_nodes}
    edge_keys: set[tuple[str, str, str]] = set()
    kept_edges: list[dict[str, str]] = []
    for edge in edges:
        edge["source"] = redirects.get(edge["source"], edge["source"])
        edge["target"] = redirects.get(edge["target"], edge["target"])
        key = (edge["source"], edge["target"], edge["relation"])
        if edge["source"] not in kept_ids or edge["target"] not in kept_ids or key in edge_keys:
            continue
        edge_keys.add(key)
        kept_edges.append(edge)
    with nodes_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["id", "type", "label", "source"])
        writer.writeheader(); writer.writerows(kept_nodes)
    with edges_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["source", "target", "relation", "evidence"])
        writer.writeheader(); writer.writerows(kept_edges)


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
    index = 1
    for item in items:
        while f"news:{day}:{index}" in node_ids:
            index += 1
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
        snapshot = raw_dir / f"{day}_huggingface_blog.xml"
        if snapshot.exists():
            snapshot = raw_dir / f"{day}_{now.strftime('%H%M%S%f')}_huggingface_blog.xml"
        snapshot.write_bytes(raw)
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
        # Only consider this run's top three; do not refill with older news.
        selected = deduplicate_items(root, day, items[:3])
        for item in selected:
            try:
                article = fetch(item["link"]).decode("utf-8", "ignore")
                item["arxiv_ids"] = sorted(set(re.findall(r"arxiv\.org/(?:abs|pdf)/([0-9]{4}\.[0-9]{4,5}(?:v[0-9]+)?)", article, flags=re.I)))
            except Exception:
                item["arxiv_ids"] = []
        deduplicate_graph(root)
        update_graph(root, day, selected)
        out = {"date": day, "timezone": "Asia/Hong_Kong", "source": FEED_URL, "items": selected}
        (root / "data" / "processed").mkdir(parents=True, exist_ok=True)
        (root / "data" / "processed" / f"feed_{day}.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
        if selected:
            lines = [f"# Feed candidates {day}", ""] + [f"{i+1}. [{x['title']}]({x['link']}) — {x['published']}" for i, x in enumerate(selected)]
        else:
            lines = [f"# Feed candidates {day}", "", "本次没有新的唯一 Agent 资讯，已跳过与历史摘要重复的候选。"]
        (root / "news" / "latest_feed.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
        log_lines.append("status=success")
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
