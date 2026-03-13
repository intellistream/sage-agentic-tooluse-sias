"""SIAS - Streaming Importance-Aware Agent System.

Core components for sample importance scoring and continual learning:
- CoresetSelector: Importance-aware sample selection (loss_topk, diversity, hybrid)
- OnlineContinualLearner: Experience replay with importance weighting
- SelectionSummary: Statistics for selection operations

Usage:
    from sage_sias import CoresetSelector, OnlineContinualLearner, SIASSample

    selector = CoresetSelector(strategy="hybrid")
    selected = selector.select(samples, target_size=1000)

    learner = OnlineContinualLearner(buffer_size=2048, replay_ratio=0.25)
    batch = learner.update_buffer(new_samples)
"""

from .continual_learner import OnlineContinualLearner
from .coreset_selector import CoresetSelector, SelectionSummary
from .types import SIASSample, SampleProtocol, wrap_sample

__all__ = [
    "CoresetSelector",
    "OnlineContinualLearner",
    "SelectionSummary",
    "SIASSample",
    "SampleProtocol",
    "wrap_sample",
]

__version__ = "0.1.0"
