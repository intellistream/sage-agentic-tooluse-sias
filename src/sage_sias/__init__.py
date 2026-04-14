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
from .contract import SIAS_CONTRACT_VERSION, SIASConfig, run_selection_contract
from .coreset_selector import CoresetSelector, SelectionSummary
from .experiment_framework import (
    ContinualPhase,
    ExperimentSample,
    ManifestRecord,
    RealBenchmarkConfig,
    build_continual_phases,
    load_real_dataset,
    materialize_real_benchmark,
)
from .importance_scorer import ImportanceScoreBreakdown, ImportanceScorer, ImportanceWeights
from .integration import select_samples_for_agentic_tooluse
from .types import SIASSample, SampleProtocol, wrap_sample

__all__ = [
    "CoresetSelector",
    "ContinualPhase",
    "ExperimentSample",
    "ImportanceScorer",
    "ImportanceWeights",
    "ImportanceScoreBreakdown",
    "ManifestRecord",
    "OnlineContinualLearner",
    "RealBenchmarkConfig",
    "SelectionSummary",
    "SIASConfig",
    "SIAS_CONTRACT_VERSION",
    "build_continual_phases",
    "load_real_dataset",
    "materialize_real_benchmark",
    "run_selection_contract",
    "select_samples_for_agentic_tooluse",
    "SIASSample",
    "SampleProtocol",
    "wrap_sample",
]

__version__ = "0.1.0"
