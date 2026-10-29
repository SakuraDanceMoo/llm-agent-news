# LLM Agent Daily Intelligence

面向大模型智能体（LLM agents）的按需资讯归档。每次更新保留原始来源、排名依据和知识图谱增量。

## 今日状态

- 更新日期：2026-10-29（Asia/Hong_Kong）
- 来源：Hugging Face Blog RSS 与文章页、arXiv 摘要页
- 展示数量：按热门程度、重要性、新鲜度和相关性排名最多前三条；历史和同批次重复过滤后可少于三条或零条，不用旧资讯补足
- 最新有效资讯：`news/2026-10-29.md`，每条按“问题是什么、方法是什么、启发是什么”归纳；快捷入口为 `news/latest.md`
- 图谱：52 个节点、78 条有效关系
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

脚本生成 RSS 候选，保留来源快照，更新结构化数据与知识图谱；中文摘要及综合排名由 `agent-news-push` 技能核验后完成，每条按“问题是什么、方法是什么、启发是什么”归纳。新资讯进入 `nodes.csv` 并与“大模型智能体”主题建立 `covers` 边，文章页中的 arXiv 链接建立 `资讯→论文` 边，再生成 SVG/HTML 信息联系图。网络不可用时保留已有数据并写入运行错误，不伪造资讯。

## 重复资讯处理

URL 规范化后与原始标题、历史结构化数据和图谱交叉比较，包含同日已归档的资讯；同一事件或论文的不同报道由技能核验。只有重复内容的日期摘要直接删除；没有新增资讯时不创建日期摘要或占位说明文件，`news/latest.md` 指向最新有效摘要。混合新旧资讯的摘要只保留新增部分。重复 News 节点合并至最早的节点，关系重定向后去重，保留有效信息联系。去重结果、数量、跳过列表和报告不写入日志，也不另建去重日志。

## 调用边界

本技能只在用户明确调用 `$agent-news-push` 或明确要求推送时运行。`run_daily_update.ps1` 是按需执行的本地入口；不会因打开 Codex、日期变化或后台任务自动推送。

## Zotero

历史三篇论文已写入本机 Zotero 的“大模型智能体”目录（collection key `R98SV4VW`）。本次 NoveltyBench（arXiv:2610.02022）因当前环境未发现 Zotero 写入通道，状态为待写入，见 `logs/zotero_2026-10-29.md`。

