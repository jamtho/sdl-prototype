"""
Validator registry — connects Manifest constraint declarations to executable validators.

Validators register themselves against Manifest URIs (physical types, semantic types,
constraint types, etc.). The engine queries the registry to find which validators
apply to a given dataset.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Protocol

from manifest.model import Attestation, ComputationalProfile


class ValidatorKind(Enum):
    """What aspect of the data does this validator check?"""
    SCHEMA = "schema"           # physical types, column presence
    VALUE_RANGE = "value_range"  # per-value constraints from semantic types
    ORDERING = "ordering"        # row ordering within files
    DERIVATION = "derivation"    # column derivation consistency
    AGGREGATION = "aggregation"  # index/summary consistency
    CUSTOM = "custom"            # anything else


class ValidatorFunc(Protocol):
    """Protocol for validator callables."""
    def __call__(
        self,
        file_path: Path,
        *,
        dataset_uri: str,
        **kwargs: Any,
    ) -> list[Attestation]:
        ...


@dataclass
class RegisteredValidator:
    """A validator registered in the registry."""
    name: str
    kind: ValidatorKind
    profile: ComputationalProfile
    func: ValidatorFunc
    description: str = ""


class ValidatorRegistry:
    """
    Central registry mapping Manifest concepts to validators.

    Validators can be registered:
    - By kind (schema, value_range, ordering, etc.)
    - By semantic type URI (e.g. "ais:MMSI" -> custom MMSI validator)
    - By constraint URI (e.g. "ais:MonotonicallyNonDecreasing" -> custom check)

    The engine queries the registry to build a validation plan for a dataset.
    """

    def __init__(self) -> None:
        self._by_kind: dict[ValidatorKind, list[RegisteredValidator]] = defaultdict(list)
        self._by_uri: dict[str, list[RegisteredValidator]] = defaultdict(list)

    def register(
        self,
        name: str,
        kind: ValidatorKind,
        profile: ComputationalProfile,
        func: ValidatorFunc,
        description: str = "",
        *,
        uri: str | None = None,
    ) -> None:
        """Register a validator."""
        rv = RegisteredValidator(
            name=name,
            kind=kind,
            profile=profile,
            func=func,
            description=description,
        )
        self._by_kind[kind].append(rv)
        if uri:
            self._by_uri[uri].append(rv)

    def get_by_kind(self, kind: ValidatorKind) -> list[RegisteredValidator]:
        """Return all validators of a given kind."""
        return self._by_kind.get(kind, [])

    def get_by_uri(self, uri: str) -> list[RegisteredValidator]:
        """Return all validators registered for a specific URI."""
        return self._by_uri.get(uri, [])

    def get_all(self) -> list[RegisteredValidator]:
        """Return all registered validators, sorted by computational cost."""
        seen: set[str] = set()
        all_validators: list[RegisteredValidator] = []
        for validators in self._by_kind.values():
            for v in validators:
                if v.name not in seen:
                    seen.add(v.name)
                    all_validators.append(v)
        return sorted(all_validators, key=lambda v: v.profile.value)

    def summary(self) -> str:
        """Human-readable summary of registered validators."""
        lines: list[str] = ["Registered validators:"]
        for v in self.get_all():
            lines.append(f"  [{v.profile.name:15s}] {v.name} ({v.kind.value})")
            if v.description:
                lines.append(f"    {v.description}")
        return "\n".join(lines)
