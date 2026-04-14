# Paper Baselines And Real Datasets

最后更新：2026-04-14

## 论文主题定位

本文的核心主题不是泛化的 LLM tool use，也不是泛化的 continual learning，
而是：

- agent tool 调用场景下的持续学习
- 在分布漂移、工具集合变化、任务顺序变化下，保持工具选择与工具调用能力
- 通过 replay / coreset / adaptive policy 减少遗忘

因此，实验设计建议采用“两轴 baseline”：

- Tool-use / function-calling baseline
- Continual-learning baseline

直接和纯 function-calling SOTA 对比不够，因为它们大多不是 continual setting。
直接和传统 continual learning 方法对比也不够，因为它们不在 tool-calling environment 上评测。

## 推荐 Baseline 结构

### A. Tool-Use / Function-Calling Baselines

这些工作用于回答：

- 你的方法在真实工具调用任务上是否有效？
- 数据筛选 / replay 后，是否仍保持真实 agent tool 调用质量？

推荐优先纳入：

1. BFCL (ICML 2025)
   - 论文：The Berkeley Function Calling Leaderboard (BFCL): From Tool Use to Agentic Evaluation of Large Language Models
   - 价值：覆盖 serial / parallel / stateful multi-step agentic evaluation，和你的主题最贴近
   - 用法：作为函数调用与多步 agentic 工具调用主 benchmark

2. StableToolBench (Findings ACL 2024)
   - 论文：StableToolBench: Towards Stable Large-Scale Benchmarking on Tool Learning of Large Language Models
   - 价值：相对 ToolBench 更稳定，适合作为可复现工具调用数据与评测环境
   - 用法：作为大规模 API/tool 调用 benchmark

3. UltraTool (Findings ACL 2024)
   - 论文：Planning, Creation, Usage: Benchmarking LLMs for Comprehensive Tool Utilization in Real-World Complex Scenarios
   - 价值：强调 planning + usage + real-world complexity
   - 用法：作为复杂多步工具使用与规划能力补充评测

4. API-BLEND (ACL 2024)
   - 论文：API-BLEND: A Comprehensive Corpora for Training and Benchmarking API LLMs
   - 价值：强调 API detection / slot filling / sequencing，可作为训练与测试数据来源
   - 用法：构造 continual sequence 时很好用

5. CToolEval (Findings ACL 2024)
   - 论文：CToolEval: A Chinese Benchmark for LLM-Powered Agent Evaluation in Real-World API Interactions
   - 价值：如果你的投稿考虑中文或多语言 agent，可作为中文工具调用补充实验

### B. Continual-Learning Baselines

这些 baseline 用于回答：

- 你的 SIAS 比经典 continual learning 策略更适合 tool-calling 场景吗？
- 动态 replay / coreset 是否真的降低 forgetting？

建议必须包含：

1. Sequential Fine-Tuning
   - 最基本下界
   - 不做 replay / memory / regularization

2. Mixed Training / Joint Oracle
   - 上界
   - 将所有阶段数据混合训练

3. Experience Replay (ER)
   - 你当前 issue 设计中已经明确出现
   - 应作为最核心传统 baseline

4. Fixed-Ratio Replay
   - 作为你动态 replay 的直接对照

5. EWC / A-GEM / MIR / DER++（至少选 2 个）
   - 虽然这些方法不一定都来自近两年，但 reviewer 对 continual learning 基线会默认期望看到
   - 推荐优先：
     - EWC：代表正则化类 baseline
     - MIR 或 DER++：代表 memory/replay 强 baseline

## 近两年最相关论文

### 最相关的 tool-use / agent benchmark

- BFCL, ICML 2025
- StableToolBench, Findings ACL 2024
- UltraTool, Findings ACL 2024
- API-BLEND, ACL 2024
- CToolEval, Findings ACL 2024

### 最相关的 continual-learning / lifelong agent benchmark

1. LifelongAgentBench
   - 关键词：lifelong learning, continual learning, LLM agent
   - 价值：这是目前和你论文主题最贴近的 benchmark 方向之一
   - 注意：当前检索结果来自 OpenReview 页面，需要在投稿时再确认最终会议信息与正式版本

2. TRACE: A Comprehensive Benchmark for Continual Learning in Large Language Models
   - 价值：不是 tool-calling 专项，但可借其 forgetting / retention 指标与 protocol

3. Towards Practical Tool Usage for Continually Learning LLMs
   - 价值：不是明确顶会版本，但和你的题目交集非常高
   - 建议：即使不用作“顶会 baseline”，也应在 related work 中讨论

## 真实 Dataset 推荐

### 第一优先级：真实工具调用 / API 调用数据

1. BFCL
   - 理由：现实函数调用任务丰富，包含 serial / parallel / stateful multi-step agentic setting
   - 用途：主评测集
   - 当前决定：作为本文主评测 benchmark

2. StableToolBench
   - 理由：真实 API 语义，评测更稳定
   - 用途：次主评测集或补充实验

3. API-BLEND
   - 理由：更像“真实 API 任务语料库”
   - 用途：训练集 / continual sequence 构造源 / 辅助测试集

4. UltraTool
   - 理由：强调真实复杂场景下的多步工具使用
   - 用途：复杂任务泛化评测

5. CToolEval
   - 理由：中文真实应用 API 场景
   - 用途：多语言或中文补充实验

### 第二优先级：真实 agent environment

如果你要强调“agent tool 调用持续学习”，不应只停留在函数调用 JSON 层。
建议至少增加 1 个真实交互 environment：

1. AgentBench FC
   - OS / DB / KG / ALFWorld / WebShop 等真实环境任务
   - 适合构造跨阶段任务流和长期 skill accumulation
   - 当前决定：作为本文真实环境评测主 benchmark

2. WebShop / Mind2Web / OSWorld 类环境
   - 作为 environment-level 补充
   - 更能体现“工具调用成功率”而不只是 function-call 格式正确率

## 推荐实验矩阵

### Dataset 组合

当前建议固定为：

- 主实验：
  - BFCL
- 真实环境实验：
  - AgentBench FC
- 补充训练/分析数据：
  - API-BLEND 或 StableToolBench

### Baseline 组合

建议最少做：

- SFT / sequential FT
- Joint training oracle
- ER
- Fixed replay ratio
- EWC
- MIR 或 DER++
- 你的方法：SIAS

### 评测指标

建议统一报告：

- Tool-call success / pass rate
- Task completion rate
- Forgetting rate
- Forward transfer
- Backward transfer
- Sample efficiency
- Runtime / memory overhead

## 最适合你这篇论文的叙事

如果目标是顶会论文，最稳的叙事不是“我们只是发明了一个 coreset 算法”，
而是：

1. 问题定义：
   - agent tool 调用在长序列任务中会遗忘旧工具、旧参数模式和旧规划能力

2. 方法：
   - SIAS 通过 importance scoring + streaming coreset + adaptive replay
     在 tool-calling continual learning 中保留关键经验

3. 证据：
   - 在 BFCL / AgentBench FC 上
     比 sequential FT、ER、EWC、MIR/DER++ 更低 forgetting、更高 task success

4. 消融：
   - 无 replay
   - 固定 replay
   - 动态 replay
   - 无 coreset
   - batch coreset
   - streaming coreset
   - 无 unified scorer

## 当前建议

下一步最值得补的不是继续写算法代码，而是：

1. 把 BFCL 与 AgentBench FC 转成统一 continual-learning 输入格式
2. 固定 phase 构造规则：
   - BFCL：按 `test_category` 或 `domain` 形成阶段
   - AgentBench FC：按 `environment/task_name` 形成阶段
3. 增加与 ER / EWC / MIR/DER++ 的基线 runner
4. 固定 continual sequence 切分协议与 forgetting 指标

## 已生成的实验代码框架

当前仓库已新增可直接扩展到真实数据的实验框架：

- `src/sage_sias/experiment_framework.py`
  - BFCL 本地 JSON/JSONL 适配
  - AgentBench FC 本地 JSON/JSONL 适配
  - continual phase 构造
  - baseline manifest 生成：
    - `sequential_ft`
    - `fixed_replay`
    - `sias`
    - `joint_oracle`
- `scripts/run_real_dataset_experiment.py`
  - 统一生成真实数据实验 manifest

建议运行方式：

```bash
PYTHONPATH=src python scripts/run_real_dataset_experiment.py \
  --dataset bfcl \
  --input-path path/to/bfcl.jsonl \
  --output-dir artifacts/bfcl_continual \
  --phase-field phase_source
```

```bash
PYTHONPATH=src python scripts/run_real_dataset_experiment.py \
  --dataset agentbench_fc \
  --input-path path/to/agentbench_fc.jsonl \
  --output-dir artifacts/agentbench_fc_continual \
  --phase-field phase_source \
  --eval-split-field split
```
