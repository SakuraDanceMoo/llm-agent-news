# LLM Agent Daily Intelligence

面向大模型智能体（LLM agents）的每日资讯归档。每次更新保留原始来源、排名依据和知识图谱增量。

## 今日状态

- 更新日期：2026-10-11（Asia/Hong_Kong）
- 来源：Hugging Face Blog RSS 与文章页、arXiv 摘要页
- 展示数量：按相关性、重要性和新鲜度综合排名前三条
- 证据标签：`一手来源` 表示原始机构/作者页面；`事实`、`推断`、`建议` 分开记录

## 目录

- `data/raw/`：原始 RSS 快照，不覆盖历史文件
- `data/processed/`：结构化资讯 JSON
- `news/`：面向阅读的每日中文摘要
- `knowledge_graph/`：节点、边、可点击 SVG/HTML 信息联系图和 Mermaid 图
- `scripts/`：每日更新入口
- `logs/`：运行日志与校验结果

## 归档容量策略

归档以 1 GiB（`1024^3` 字节）为阈值。按需更新时若超限，按“缓存 → 最旧原始快照 → 低重要度旧处理结果/运行日志 → 较旧每日摘要”的顺序清理；知识图谱、脚本、README、当前摘要、`MANIFEST.csv` 和 Zotero 核验日志受保护。清理记录写入 `logs/cleanup_YYYY-MM-DD.json`。手动预览：

```powershell
uv run python .\llm_agent_news\scripts\cleanup_archive.py --root .\llm_agent_news
```

## 按需更新

在 PowerShell 中运行：

```powershell
Set-Location D:\AgentProject2026
& .\llm_agent_news\scripts\run_daily_update.ps1
```

脚本会把当天摘要写入 `news/`，把来源快照写入 `data/raw/`，并更新 `data/processed/` 与知识图谱；每条新资讯至少进入 `nodes.csv` 并与“大模型智能体”主题建立 `covers` 边，文章页中的 arXiv 链接还会自动建立 `资讯→论文` 边，再由图谱构建器生成 `graph.svg` 和 `graph.html`。网络不可用时保留已有数据并写入日志，不伪造资讯。

## 调用边界

本技能只在用户明确调用 `$agent-news-push` 或明确要求推送时运行。`run_daily_update.ps1` 是按需执行的本地入口；不会因打开 Codex、日期变化或后台任务自动推送。

## Zotero

本次三篇相关 arXiv 论文已写入本机 Zotero 的“大模型智能体”目录（collection key `R98SV4VW`），并附加了公开 PDF。条目键和附件校验记录见每日摘要与 `logs/zotero_2026-10-11.md`。

