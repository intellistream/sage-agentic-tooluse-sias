# Issue 状态跟踪

最后更新：2026-04-14

用途：

- 固化当前仓库的 GitHub issue 清单。
- 跟踪每个 issue 的处理状态。
- 每解决一项，就在本文件补充“已完成记录”。

状态约定：

- `todo`：尚未开始
- `in_progress`：正在处理
- `blocked`：被依赖项阻塞
- `done`：已完成

## 总览

| Issue | 标题 | 状态 | 说明 |
| --- | --- | --- | --- |
| #1 | 边界重构（Phase 1） | `done` | 已完成边界文档、依赖收敛、README 收口、根目录旧实现删除、测试切换到 `src` 主路径 |
| #2 | core/external dependency boundary cleanup | `done` | 已完成 `sample_id` 唯一契约收敛、兼容别名删除、fallback 清理、旧路径移除 |
| #3 | Torch 依赖最小化与证据化保留 | `done` | issue 中已标记完成；当前已继续保持依赖声明无 `torch` |
| #5 | 漂移感知 + 动态 replay | `done` | 已完成漂移/遗忘信号、动态 replay_ratio、规则式策略切换与回归测试落地 |
| #6 | Streaming coreset selection | `done` | 已完成 streaming 策略、短/长期候选池、基准脚本与边界测试 |
| #7 | 联合 importance scorer | `done` | 已完成 loss/diversity/novelty 统一评分、解释字段和 learner/selector 接线 |
| #8 | Tool-use benchmark 与消融 | `done` | 已完成最小评测/消融运行器与 markdown/csv 报告生成 |
| #9 | 与 `sage-agentic-tooluse` 集成 | `done` | 已完成稳定集成 helper、示例与 mock 契约测试 |
| #10 | Benchmark-facing contract v1 | `done` | 已完成 `SIASConfig`、v1 schema、最小 adapter 与 contract test |
| #11 | 可复现实验基础设施 | `done` | 已完成 seed 稳定性、trace/artifact 输出与最小可复现验证 |

## 已完成记录

### Issue #1

当前已完成：

- 新增边界文档：`docs/boundary.md`
- 收敛 `pyproject.toml` 依赖声明，移除无代码证据的 heavy/兼容依赖
- 更新 `README.md`，补充 L3 边界与 fail-fast 契约说明
- 修正 `pyproject.toml` 仓库与 issue 链接到当前仓库
- 删除根目录旧实现：`core_types.py`、`continual_learner.py`、`coreset_selector.py`、`__init__.py`
- 将测试引导与边界回归切换到 `src/sage_sias/` 主路径
- 通过 `python -m compileall -q src tests` 与最小 `PYTHONPATH=src` smoke check

### Issue #2

当前已完成：

- 删除 `src/sage_sias/types.py` 中的兼容别名 `Sample = SIASSample`
- 删除 `src/sage_sias/continual_learner.py` 中的 `dialog_id` / `id(...)` fallback
- 删除 `src/sage_sias/coreset_selector.py` 中的 `dialog_id` / `id(...)` fallback
- 将 `sample_id` 设为核心算法唯一主键，缺失时直接抛错
- 在 `select()` / `update_buffer()` 路径前置 fail-fast 校验
- 删除根目录旧版 `core_types.py`、`continual_learner.py`、`coreset_selector.py`、`__init__.py`
- 让回归测试与 `src` 主路径完全一致

说明：

- 当前环境缺少 `pytest` 可执行依赖，尚未做完整 pytest 回归；已完成编译检查与最小功能验证

### Issue #3

当前已完成：

- 维持 `pyproject.toml` 中无 `torch` 依赖声明
- `README.md` 安装说明不再暴露 `torch` 安装路径

说明：

- 该 issue 在 GitHub 讨论中已被标记完成，这里仅做本地追踪留档

### Issue #5

当前已完成：

- 新增漂移/遗忘信号检测（topic/token 分布 + loss 变化），并暴露 `drift_score` / `forgetting_score`
- 引入动态 `adaptive_replay_ratio` 调度（漂移/遗忘强度驱动）
- 支持规则式在线策略切换（`loss_topk` / `diversity` / `hybrid`）
- 新增回归测试：`tests/test_issue5_issue11_adaptive_replay.py`
- 已完成最小功能验证：`compileall` + 直接调用测试函数

### Issue #11

当前已完成：

- 新增统一 trace 输出与 artifact 目录结构：`metrics.jsonl` / `summary.csv` / `config.snapshot.yaml`
- 新增同 seed 稳定性测试（同输入批次，训练 batch 与 trace 输出一致）
- 已完成最小功能验证：`compileall` + 直接调用测试函数

### Issue #6

当前已完成：

- `CoresetSelector` 新增 `strategy="streaming"` 与 `update_stream(...)`
- 增加 short-term / long-term candidate pools 与 reservoir-style 替换逻辑
- 增加 streaming 基准接口与脚本：`scripts/benchmark_streaming_selector.py`
- 新增边界回归测试：空流、重复 `sample_id`、极端 `target_size`

### Issue #7

当前已完成：

- 新增统一评分器：`src/sage_sias/importance_scorer.py`
- 评分由 `loss + diversity + novelty` 组成，可解释输出写入 `importance_breakdown`
- `CoresetSelector` 与 `OnlineContinualLearner` replay 路径都已接入统一评分
- 新增单测覆盖分数单调性与 learner/selector 一致性

### Issue #8

当前已完成：

- 新增最小评测/消融运行器：`src/sage_sias/benchmarking.py`
- 新增一键脚本：`scripts/run_tooluse_ablation.py`
- 自动生成 `ablation_results.csv` 与 `ablation_report.md`
- 覆盖无 replay、固定 replay、动态 replay、无/batch/streaming coreset 场景

### Issue #9

当前已完成：

- 新增稳定集成 helper：`src/sage_sias/integration.py`
- 新增端到端示例：`examples/integration_sage_agentic_tooluse.py`
- 新增 mock 契约测试：`tests/test_issue9_integration_contract.py`
- 新增迁移说明：`docs/integration.md`

### Issue #10

当前已完成：

- 新增 `src/sage_sias/contract.py`
- 定义 `SIASConfig` 与版本字段 `sias-benchmark-v1`
- 固定输入/输出 schema，输出包含 `importance_score` 与 `importance_breakdown`
- 新增最小 adapter 示例：`examples/benchmark_adapter_minimal.py`
- 新增 contract test：`tests/test_issue10_benchmark_contract.py`

## 推荐推进顺序

1. 先彻底收口 `#1/#2`
2. 再并行启动 `#5/#11` 与 `#6/#7`
3. 然后做 `#10`
4. 最后推进 `#8/#9`

## 更新规则

- 每次完成一个 issue，直接把状态改为 `done`
- 每次完成一个关键子项，补一条“当前已完成”
- 如果出现阻塞，在对应 issue 下增加“阻塞原因”
