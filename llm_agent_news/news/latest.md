# 大模型智能体资讯｜2026-10-14

来源抓取时间：2026-10-14（Asia/Hong_Kong）。本次保留 1 条新的、未与历史归档重复的 Agent 资讯。

## 1. LFM2.5-24B-A2B：让 Agent 在设备上快速、私密地运行

**发布时间**：2026-10-13

**来源**：[Liquid AI / Hugging Face 文章](https://huggingface.co/blog/LiquidAI/lfm25-24b-a2b)｜[模型页面](https://huggingface.co/LiquidAI/LFM2.5-24B-A2B)

### 问题是什么

**事实｜一手来源**：需要持续进行推理、工具调用和多步任务的 Agent，常受云端延迟、隐私和推理成本限制。端侧模型还要在有限硬件上兼顾 Agent 能力、上下文长度和速度。

### 方法是什么

**事实｜一手来源**：Liquid AI 发布 LFM2.5-24B-A2B：总参数 24B、每个 token 仅激活约 2B 参数的 MoE 推理模型，支持显式思考、工具调用和多轮轨迹。文章称其使用 131K 上下文、工具调用与多轮轨迹训练，并经过 SFT、教师专门化、多域 on-policy 蒸馏和 Agentic RL；可通过 llama.cpp、MLX、vLLM、SGLang 和 ONNX 等生态运行。文章报告其在 8 项工具/Agent 基准中的 5 项领先或并列领先，在 Apple M5 Max 上达到 184 tokens/s。

### 启发是什么

**推断与建议**：端侧 Agent 的比较应同时报告工具调用质量、长程任务成功率、端到端延迟、内存占用和隐私边界，不能只比较参数规模或通用知识分数。对知识密集任务，文章也提示需要配合检索或 Web Search；可将“本地小激活参数模型 + 受控检索/工具”作为低延迟 Agent 基线，并单独验证其在真实设备上的状态正确性和重复运行可靠性。

## 证据边界

问题、方法和基准数字来自 Liquid AI 的一手发布文章；性能数字是发布方在其指定推理设置下的报告，尚未在本地复现。启发属于基于来源的研究推断。该资讯不对应本次新增论文，因此未写入 Zotero。

## 知识图谱

本条已加入[信息联系图](../knowledge_graph/graph.html)（SVG：[graph.svg](../knowledge_graph/graph.svg)）。
