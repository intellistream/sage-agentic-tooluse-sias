"""SIAS Core Data Types."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


@dataclass(slots=True)
class SIASSample:
    sample_id: str
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)
    importance_score: float = 0.0

    def __hash__(self) -> int:
        return hash(self.sample_id)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, SIASSample):
            return self.sample_id == other.sample_id
        return False


@runtime_checkable
class SampleProtocol(Protocol):
    @property
    def sample_id(self) -> str: ...

    @property
    def text(self) -> str: ...

    @property
    def metadata(self) -> dict[str, Any]: ...


def wrap_sample(
    sample_id: str,
    text: str,
    metadata: dict[str, Any] | None = None,
    **kwargs: Any,
) -> SIASSample:
    meta = metadata or {}
    meta.update(kwargs)
    return SIASSample(sample_id=sample_id, text=text, metadata=meta)
