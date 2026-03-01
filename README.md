# SAGE Tool Use SIAS (Sample-Importance-Aware Selection)

**Tool selection algorithm using sample-importance-aware selection for agent training and tool curation**

[![PyPI version](https://badge.fury.io/py/isage-agentic-tooluse-sias.svg)](https://badge.fury.io/py/isage-agentic-tooluse-sias)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 🎯 Overview

`sage-agentic-tooluse-sias` provides Sample-Importance-Aware Selection algorithms specifically designed for:

- **Tool Selection**: Select important tools for agent use
- **Agent Training**: Select important trajectories for fine-tuning
- **Continual Learning**: Efficient sample selection for continual/lifelong learning
- **Tool/Trajectory Curation**: Curate representative samples for agent development

## 📦 Installation

```bash
# Basic installation
pip install isage-agentic-tooluse-sias

# Development installation
pip install isage-agentic-tooluse-sias[dev]
```

## 🚀 Quick Start

### Continual Learning

```python
from sage_sias import OnlineContinualLearner, SIASSample

# Create continual learner
learner = OnlineContinualLearner(
    buffer_size=1000,
    replay_ratio=0.3,
)

# Add samples
new_samples = [
    SIASSample(sample_id="s1", text="tool call trace A"),
    SIASSample(sample_id="s2", text="tool call trace B"),
]
training_batch = learner.update_buffer(new_samples)

# Inspect replay buffer
important_samples = learner.buffer_snapshot()
```

### Coreset Selection

```python
from sage_sias import CoresetSelector

# Create coreset selector
selector = CoresetSelector(
    strategy="hybrid",
)

# Select representative samples
coreset = selector.select(samples=dataset, target_size=100)
```

## 📚 Key Components

### 1. **Continual Learner** (`continual_learner.py`)

Manages sample selection for continual learning:
- Buffer management with importance-based eviction
- Multiple selection strategies (loss_topk, diversity, hybrid, random)
- Support for experience replay

### 2. **Coreset Selector** (`coreset_selector.py`)

Selects representative subsets:
- Loss/diversity/hybrid/random selection
- Diversity-aware sampling
- Importance scoring
- Support for large-scale datasets

### 3. **Core Types** (`core_types.py`)

Common data types and protocols:
- Sample representation
- Sample protocol
- Selection summary

## 🔧 Architecture

```
sage_sias/
├── continual_learner.py    # Continual learning with buffer management
├── coreset_selector.py      # Coreset selection algorithms
├── core_types.py            # Common types and protocols
└── __init__.py              # Public API exports
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
from sage_sias import OnlineContinualLearner, CoresetSelector, SIASSample

learner = OnlineContinualLearner(buffer_size=2048, replay_ratio=0.25)
selector = CoresetSelector(strategy="hybrid")

samples = [
    SIASSample(sample_id="a", text="query weather"),
    SIASSample(sample_id="b", text="query calendar"),
]
selected = selector.select(samples=samples, target_size=1)
batch = learner.update_buffer(selected)
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
