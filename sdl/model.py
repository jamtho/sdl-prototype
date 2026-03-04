"""Core data model types for SDL validation."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class ValidationResult(Enum):
    """Outcome of a single validation check."""
    PASS = "pass"
    FAIL = "fail"
    WARN = "warn"
    ERROR = "error"  # validator itself failed to run


class ComputationalProfile(Enum):
    """How expensive a validation is — used to order checks cheapest-first."""
    SCHEMA_CHECK = 0     # parquet metadata only, no data read
    PER_VALUE = 1        # scan values but no ordering dependency
    FULL_SCAN = 2        # must read all data
    SEQUENTIAL_SCAN = 3  # must read data in order
    EXTERNAL_SERVICE = 4 # needs network / external call

    @classmethod
    def from_uri(cls, uri: str) -> ComputationalProfile:
        mapping: dict[str, ComputationalProfile] = {
            "sdl:SchemaCheckOnly": cls.SCHEMA_CHECK,
            "sdl:PerValueCheck": cls.PER_VALUE,
            "sdl:FullScanRequired": cls.FULL_SCAN,
            "sdl:SequentialScan": cls.SEQUENTIAL_SCAN,
            "sdl:ExternalService": cls.EXTERNAL_SERVICE,
        }
        suffix = uri.rsplit("#", 1)[-1] if "#" in uri else uri.rsplit("/", 1)[-1]
        # Try both full URI and suffix
        return mapping.get(uri, mapping.get(f"sdl:{suffix}", cls.FULL_SCAN))


@dataclass
class ColumnInfo:
    """Resolved column metadata from the SDL graph."""
    uri: str
    name: str
    physical_type: str          # e.g. "sdl:Integer"
    semantic_type: str | None   # e.g. "ais:MMSI"
    nullable: bool = True


@dataclass
class SemanticTypeInfo:
    """Resolved semantic type metadata."""
    uri: str
    label: str
    required_physical_type: str | None = None
    acceptable_physical_types: list[str] = field(default_factory=list)
    min_inclusive: float | None = None
    max_inclusive: float | None = None
    min_exclusive: float | None = None
    max_exclusive: float | None = None
    unit: str | None = None


@dataclass
class DatasetInfo:
    """Resolved dataset metadata."""
    uri: str
    label: str
    columns: list[ColumnInfo] = field(default_factory=list)
    file_format: str = "parquet"
    ordering_keys: list[OrderingKeyInfo] = field(default_factory=list)
    partition_path_template: str | None = None
    partition_granularity: str | None = None
    redundant_partition_key: str | None = None  # column name


@dataclass
class OrderingKeyInfo:
    """A single key in a row ordering."""
    column_name: str
    direction: str  # "ascending" or "descending"
    precedence: int
    semantic: str   # e.g. "sdl:ClusteringForIndex"


@dataclass
class DerivationInfo:
    """A column derivation relationship."""
    uri: str
    derived_column: str     # column name
    source_columns: list[str]
    function_uri: str
    properties: list[str]   # e.g. ["sdl:Deterministic", "sdl:Lossy"]


@dataclass
class AggregatedColumnInfo:
    """How one target column is aggregated from source columns."""
    target_column: str       # column name in target dataset
    source_columns: list[str]  # column name(s) in source dataset
    function_uri: str         # e.g. "sdl:Min", "ais:MaxConsecutiveImpliedSpeed"
    within_group_ordering: str | None = None  # column name for order-dependent aggs


@dataclass
class AggregationInfo:
    """Aggregation relationship between two datasets."""
    uri: str
    source_dataset: str
    target_dataset: str
    group_by_column: str
    aggregated_columns: list[AggregatedColumnInfo] = field(default_factory=list)


@dataclass
class Attestation:
    """
    Result of a validation run, suitable for writing back to the graph.

    Each attestation records: what was checked, against what data, when,
    and what the outcome was.
    """
    constraint_uri: str
    dataset_uri: str
    file_path: str | None = None
    result: ValidationResult = ValidationResult.PASS
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    details: str = ""
    validator_id: str = ""
    profile: ComputationalProfile = ComputationalProfile.FULL_SCAN

    @property
    def passed(self) -> bool:
        return self.result == ValidationResult.PASS

    def to_turtle(self, prefix: str = "_:att") -> str:
        """Serialise as Turtle triples for writing back to the graph."""
        node_id = f"{prefix}_{abs(hash((self.constraint_uri, self.file_path, self.timestamp.isoformat())))}"
        lines = [
            f'{node_id} a sdl:VerificationAttestation ;',
            f'    sdl:verifiedConstraint <{self.constraint_uri}> ;',
            f'    sdl:verifiedDataset <{self.dataset_uri}> ;',
            f'    sdl:verificationTime "{self.timestamp.isoformat()}"^^xsd:dateTime ;',
            f'    sdl:verificationResult sdl:{self.result.value.capitalize()} ;',
        ]
        if self.file_path:
            lines.append(f'    sdl:verifiedFile "{self.file_path}" ;')
        if self.details:
            escaped = self.details.replace('\\', '\\\\').replace('"', '\\"')
            lines.append(f'    sdl:verificationDetails "{escaped}" ;')
        # Close the last semicolon with a period
        lines[-1] = lines[-1].rstrip(" ;") + " ."
        return "\n".join(lines)

    def summary_line(self) -> str:
        icons = {
            ValidationResult.PASS: "✓",
            ValidationResult.FAIL: "✗",
            ValidationResult.WARN: "⚠",
            ValidationResult.ERROR: "!",
        }
        icon = icons[self.result]
        return f"  {icon} [{self.profile.name:15s}] {self.constraint_uri}"
