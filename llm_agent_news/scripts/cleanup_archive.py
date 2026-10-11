"""Prune old, low-importance news artifacts after the archive exceeds 1 GiB.

The default mode is a dry run. Scheduled jobs pass ``--apply``. The script
never removes the current digest, graph, scripts, manifests, or Zotero logs.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
from pathlib import Path

GIB = 1024 ** 3
PROTECTED_NAMES = {"README.md", "latest.md", "latest_feed.md", "MANIFEST.csv"}
PROTECTED_DIRS = {"knowledge_graph", "scripts"}


def archive_files(root: Path) -> list[Path]:
    return [p for p in root.rglob("*") if p.is_file()]


def importance(root: Path, path: Path) -> tuple[int, float, str]:
    """Lower importance is deleted first; newer files survive ties."""
    rel = path.relative_to(root)
    name = path.name
    if "__pycache__" in rel.parts or path.suffix in {".pyc", ".tmp", ".bak"}:
        return (0, path.stat().st_mtime, "cache")
    if name in PROTECTED_NAMES or rel.parts[0] in PROTECTED_DIRS:
        return (10_000, path.stat().st_mtime, "protected")
    if rel.parts[0] == "knowledge_graph":
        return (10_000, path.stat().st_mtime, "graph")
    if rel.parts[0] == "logs" and name.startswith("zotero_"):
        return (9_000, path.stat().st_mtime, "zotero-verification")
    if rel.parts[0] == "data" and len(rel.parts) > 1 and rel.parts[1] == "raw":
        return (100, path.stat().st_mtime, "raw-source")
    if rel.parts[0] == "data" and len(rel.parts) > 1 and rel.parts[1] == "processed":
        return (250, path.stat().st_mtime, "processed-digest")
    if rel.parts[0] == "news":
        return (350, path.stat().st_mtime, "daily-summary")
    if rel.parts[0] == "logs":
        return (200, path.stat().st_mtime, "run-log")
    return (500, path.stat().st_mtime, "other")


def update_manifest(root: Path) -> None:
    manifest = root / "data" / "raw" / "MANIFEST.csv"
    if not manifest.exists():
        return
    rows = list(csv.DictReader(manifest.open(encoding="utf-8-sig")))
    kept = [row for row in rows if (root / "data" / "raw" / row["path"]).exists()]
    with manifest.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["path", "source", "captured_at", "encoding", "bytes", "sha256"])
        writer.writeheader(); writer.writerows(kept)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--limit-gib", type=float, default=1.0)
    parser.add_argument("--apply", action="store_true", help="Actually delete selected files")
    args = parser.parse_args()
    root = args.root.resolve()
    files = archive_files(root)
    before = sum(p.stat().st_size for p in files)
    threshold = int(args.limit_gib * GIB)
    report = {"time": dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).isoformat(), "root": str(root), "threshold_bytes": threshold, "before_bytes": before, "mode": "apply" if args.apply else "dry-run", "deleted": [], "after_bytes": before}
    if before > threshold:
        need = before - threshold
        candidates = sorted((p for p in files if importance(root, p)[0] < 10_000), key=lambda p: (importance(root, p)[0], importance(root, p)[1]))
        reclaimed = 0
        for path in candidates:
            if reclaimed >= need:
                break
            score, _, category = importance(root, path)
            size = path.stat().st_size
            report["deleted"].append({"path": str(path.relative_to(root)), "bytes": size, "importance": score, "category": category})
            reclaimed += size
            if args.apply:
                path.unlink()
        if args.apply:
            update_manifest(root)
            report["after_bytes"] = sum(p.stat().st_size for p in archive_files(root))
        else:
            report["after_bytes"] = before - reclaimed
    stamp = dt.date.today().isoformat()
    log_path = root / "logs" / f"cleanup_{stamp}.json"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
