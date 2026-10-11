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

## 每日更新

在 PowerShell 中运行：

```powershell
Set-Location D:\AgentProject2026
& .\llm_agent_news\scripts\run_daily_update.ps1
```

脚本会把当天摘要写入 `news/`，把来源快照写入 `data/raw/`，并更新 `data/processed/` 与知识图谱；每条新资讯至少进入 `nodes.csv` 并与“大模型智能体”主题建立 `covers` 边，再由图谱构建器生成 `graph.svg` 和 `graph.html`。网络不可用时保留已有数据并写入日志，不伪造资讯。

## 自动化边界

当前 Codex 会话没有暴露 `automation_update` 工具，因而不能直接注册“打开 Codex 即向对话推送”的产品级自动化。`run_daily_update.ps1` 是可执行的本地入口；如需系统级每日运行，可在 Windows 任务计划程序中调用它。Codex 打开后读取 `news/latest.md` 即可获得当天前三条。

已注册当前用户任务 `Codex-LLM-Agent-News`，触发器为用户登录和每天 08:00；任务会更新 `news/latest_feed.md`，不会替换带人工证据边界的每日中文摘要。

## Zotero

本次三篇相关 arXiv 论文已写入本机 Zotero 的“大模型智能体”目录（collection key `R98SV4VW`），并附加了公开 PDF。条目键和附件校验记录见每日摘要与 `logs/zotero_2026-10-11.md`。

