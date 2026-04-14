# SAGE SIAS (Sample-Importance-Aware Selection)

**Independent package for sample-importance-aware selection, continual learning, and coreset algorithms**

[![PyPI version](https://badge.fury.io/py/isage-sias.svg)](https://badge.fury.io/py/isage-sias)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 🎯 Overview

`sage-sias` provides Sample-Importance-Aware Selection algorithms for:

- **Continual Learning**: Efficient sample selection for continual/lifelong learning scenarios
- **Coreset Selection**: Select representative subsets from large datasets
- **Active Learning**: Importance-based data selection strategies
- **Tool/Trajectory Curation**: Select important samples for agent training

## 📦 Installation

```bash
# Basic installation
pip install isage-sias

# Development installation
pip install isage-sias[dev]
```

## 🚀 Quick Start

### Continual Learning

```python
from sage_sias import OnlineContinualLearner

# Create continual learner
learner = OnlineContinualLearner(
    buffer_size=1000,
    replay_ratio=0.25,
    # Optional: enable trace/artifacts for reproducible runs
    # trace_dir="artifacts/sias-run-001",
)

# Update with new samples
batch = [
    {"sample_id": "s1", "text": "tool trace 1", "metadata": {"loss": 0.4}},
    {"sample_id": "s2", "text": "tool trace 2", "metadata": {"loss": 0.8}},
]
training_batch = learner.update_buffer(batch)

# Inspect retained samples
important_samples = learner.buffer_snapshot()

# Adaptive signals (issue #5) and reproducibility trace (issue #11)
drift_score = learner.drift_score
forgetting_score = learner.forgetting_score
adaptive_replay_ratio = learner.adaptive_replay_ratio
```

### Coreset Selection

```python
from sage_sias import CoresetSelector

# Create coreset selector
selector = CoresetSelector(strategy="hybrid")

# Select representative samples
coreset = selector.select(samples=dataset, target_size=100)
```

## 📚 Key Components

### 1. **Continual Learner** (`src/sage_sias/continual_learner.py`)

Manages sample selection for continual learning:
- Buffer management with importance-based eviction
- Multiple selection strategies (`loss_topk`, `diversity`, `hybrid`, `random`)
- Support for experience replay

### 2. **Coreset Selector** (`src/sage_sias/coreset_selector.py`)

Selects representative subsets:
- Diversity-aware sampling
- Importance scoring
- Streaming coreset maintenance with short-term/long-term candidate pools
- Support for large-scale datasets

### 3. **Types** (`src/sage_sias/types.py`)

Common data types and protocols:
- Sample representation
- Importance scoring interfaces
- Selection strategies

## Boundary Contract

- This repository is an L3 algorithm library and stays runtime/service-neutral.
- Core algorithms require canonical `sample_id` on every sample.
- No `dialog_id` fallback, object-id fallback, shim, or compatibility alias exists in the core path.
- External adapters must normalize upstream payloads before calling `sage_sias`.

## Streaming And Scoring

```python
from sage_sias import CoresetSelector

selector = CoresetSelector(
    strategy="streaming",
    streaming_window_size=64,
    replacement_temperature=0.5,
)

selected = selector.update_stream(samples=dataset_chunk, target_size=32)
scores = selector.score_samples(selected)
```

- `strategy="streaming"` enables incremental coreset maintenance.
- Selected samples receive `metadata["importance_score"]` and `metadata["importance_breakdown"]`.
- The unified scorer combines loss, diversity, and novelty into one interpretable score.

## Benchmark Contract

```python
from sage_sias import SIASConfig, run_selection_contract

payload = run_selection_contract(
    config=SIASConfig(selector_strategy="streaming"),
    samples=dataset,
    target_size=32,
)
```

- Contract version: `sias-benchmark-v1`
- Minimal adapter example: `examples/benchmark_adapter_minimal.py`
- Integration example: `examples/integration_sage_agentic_tooluse.py`
- Benchmark scripts:
  - `scripts/benchmark_streaming_selector.py`
  - `scripts/run_tooluse_ablation.py`

## 🔧 Architecture

```text
src/sage_sias/
├── continual_learner.py    # Continual learning with buffer management
├── coreset_selector.py     # Coreset selection algorithms
├── types.py                # Common types and protocols
└── __init__.py             # Public API exports
```

## 🎓 Use Cases

1. **Agent Training**: Select important trajectories for fine-tuning
2. **Data Pruning**: Reduce dataset size while maintaining performance
3. **Active Learning**: Query most informative samples
4. **Memory Management**: Maintain representative samples in limited buffers
5. **Transfer Learning**: Select relevant samples for adaptation

## 🔗 Integration with SAGE

This package is part of the SAGE ecosystem but can be used independently:

```python
# Standalone usage
from sage_sias import CoresetSelector, OnlineContinualLearner

# With SAGE agentic (optional)
from sage_agentic import AgentTrainer
from sage_sias import CoresetSelector

trainer = AgentTrainer()
selector = CoresetSelector(strategy="hybrid")
important_trajectories = selector.select(samples=all_trajectories, target_size=100)
trainer.train(important_trajectories)
```

## 📖 Documentation

- **Repository**: https://github.com/intellistream/sage-agentic-tooluse-sias
- **SAGE Documentation**: https://intellistream.github.io/SAGE-Pub/
- **Issues**: https://github.com/intellistream/sage-agentic-tooluse-sias/issues

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

Originally part of the [SAGE](https://github.com/intellistream/SAGE) framework, now maintained as an independent package for broader community use.

## 📧 Contact

- **Team**: IntelliStream Team
- **Email**: shuhao_zhang@hust.edu.cn
- **GitHub**: https://github.com/intellistream
