"""
Validation engine — the core orchestrator.

Reads Manifest graph metadata and dispatches validators in cost order.
This is the graph-driven part: the engine doesn't know about AIS or any
specific domain. It reads the Manifest descriptions and figures out what to check.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from manifest.graph import ManifestGraph
from manifest.model import (
    Attestation,
    ColumnInfo,
    ComputationalProfile,
    DatasetInfo,
    OrderingKeyInfo,
    SemanticTypeInfo,
    ValidationResult,
)
from manifest.validators.aggregation import validate_aggregation_sample
from manifest.validators.ordering import (
    validate_monotonic_within_groups,
    validate_row_ordering,
)
from manifest.validators.schema import validate_column_presence, validate_physical_types
from manifest.validators.values import validate_constant_column, validate_value_ranges


class ValidationEngine:
    """
    Graph-driven validation engine.

    Given a ManifestGraph and a file path, it:
    1. Identifies the dataset the file belongs to
    2. Reads column definitions, semantic types, constraints
    3. Dispatches validators in cost order (cheapest first)
    4. Collects and returns attestations

    The engine is domain-agnostic. All domain knowledge comes from
    the Manifest Turtle files.
    """

    def __init__(self, graph: ManifestGraph) -> None:
        self.graph = graph

    def validate_file(
        self,
        file_path: Path,
        dataset_uri: str,
        *,
        companion_path: Path | None = None,
        companion_dataset_uri: str | None = None,
        max_profile: ComputationalProfile = ComputationalProfile.SEQUENTIAL_SCAN,
        verbose: bool = False,
    ) -> list[Attestation]:
        """
        Validate a file against its Manifest dataset description.

        Parameters
        ----------
        file_path : Path
            Path to the Parquet file to validate.
        dataset_uri : str
            Manifest URI of the dataset (e.g. "ais:DailyBroadcasts").
        companion_path : Path, optional
            Path to a companion file (e.g. corresponding index file).
        companion_dataset_uri : str, optional
            MNF URI of the companion dataset.
        max_profile : ComputationalProfile
            Stop at this cost level. Useful for quick checks.
        verbose : bool
            Print progress.
        """
        dataset = self.graph.get_dataset(dataset_uri)
        attestations: list[Attestation] = []

        if verbose:
            print(f"Validating {file_path}")
            print(f"  Dataset: {dataset.label} ({dataset_uri})")
            print(f"  Columns: {len(dataset.columns)}")
            print(f"  Max profile: {max_profile.name}")
            print()

        # --- Level 0: Schema checks ---
        if max_profile.value >= ComputationalProfile.SCHEMA_CHECK.value:
            if verbose:
                print("  [SCHEMA] Checking physical types...")
            attestations.extend(self._check_schema(file_path, dataset))

        # --- Level 1: Value range checks ---
        if max_profile.value >= ComputationalProfile.PER_VALUE.value:
            if verbose:
                print("  [VALUES] Checking value ranges...")
            attestations.extend(self._check_value_ranges(file_path, dataset))

        # --- Level 2: Full scan checks ---
        if max_profile.value >= ComputationalProfile.FULL_SCAN.value:
            if verbose:
                print("  [SCAN]   Checking constant columns...")
            attestations.extend(self._check_constant_columns(file_path, dataset))

        # --- Level 3: Sequential checks ---
        if max_profile.value >= ComputationalProfile.SEQUENTIAL_SCAN.value:
            if verbose:
                print("  [SEQ]    Checking row ordering...")
            attestations.extend(self._check_ordering(file_path, dataset))
            if verbose:
                print("  [SEQ]    Checking within-group monotonicity...")
            attestations.extend(self._check_monotonicity(file_path, dataset))

        # --- Aggregation checks (if companion provided) ---
        if (
            companion_path is not None
            and companion_dataset_uri is not None
            and max_profile.value >= ComputationalProfile.FULL_SCAN.value
        ):
            if verbose:
                print("  [AGG]    Checking aggregation consistency...")
            attestations.extend(
                self._check_aggregations(
                    file_path, companion_path,
                    dataset_uri, companion_dataset_uri,
                )
            )

        return attestations

    # -----------------------------------------------------------------
    # Validation dispatch methods
    # -----------------------------------------------------------------

    def _check_schema(
        self, file_path: Path, dataset: DatasetInfo
    ) -> list[Attestation]:
        """Dispatch schema-level checks from Manifest column declarations."""
        # Build expected types map from columns that have physical types
        expected_types: dict[str, str] = {
            col.name: col.physical_type
            for col in dataset.columns
            if col.physical_type
        }

        attestations = validate_physical_types(
            file_path,
            dataset_uri=dataset.uri,
            expected_types=expected_types,
        )

        # Also check column presence
        required = [col.name for col in dataset.columns]
        attestations.extend(validate_column_presence(
            file_path,
            dataset_uri=dataset.uri,
            required_columns=required,
        ))

        return attestations

    def _check_value_ranges(
        self, file_path: Path, dataset: DatasetInfo
    ) -> list[Attestation]:
        """Dispatch value range checks from semantic type declarations."""
        range_specs: list[dict[str, Any]] = []

        for col in dataset.columns:
            if col.semantic_type is None:
                continue

            sem_type = self.graph.get_semantic_type(col.semantic_type)
            if sem_type is None:
                continue

            # Check required physical type (semantic type level)
            # This is redundant with schema check but at a different level —
            # it validates the semantic type's own requirement, not just the
            # MNF column declaration.

            # Collect range constraints
            has_range = any(v is not None for v in [
                sem_type.min_inclusive,
                sem_type.max_inclusive,
                sem_type.min_exclusive,
                sem_type.max_exclusive,
            ])
            if has_range:
                range_specs.append({
                    "column_name": col.name,
                    "min_inclusive": sem_type.min_inclusive,
                    "max_inclusive": sem_type.max_inclusive,
                    "min_exclusive": sem_type.min_exclusive,
                    "max_exclusive": sem_type.max_exclusive,
                })

        if not range_specs:
            return []

        return validate_value_ranges(
            file_path,
            dataset_uri=dataset.uri,
            range_specs=range_specs,
        )

    def _check_constant_columns(
        self, file_path: Path, dataset: DatasetInfo
    ) -> list[Attestation]:
        """Check columns declared as redundant partition keys."""
        attestations: list[Attestation] = []
        if dataset.redundant_partition_key:
            attestations.extend(validate_constant_column(
                file_path,
                dataset_uri=dataset.uri,
                column_name=dataset.redundant_partition_key,
            ))
        return attestations

    def _check_ordering(
        self, file_path: Path, dataset: DatasetInfo
    ) -> list[Attestation]:
        """Check row ordering."""
        if not dataset.ordering_keys:
            return []
        return validate_row_ordering(
            file_path,
            dataset_uri=dataset.uri,
            ordering_keys=dataset.ordering_keys,
        )

    def _check_monotonicity(
        self, file_path: Path, dataset: DatasetInfo
    ) -> list[Attestation]:
        """
        Check within-group monotonicity for ordering keys marked
        as MeaningfulSequence that are secondary to a clustering key.
        """
        attestations: list[Attestation] = []
        keys = sorted(dataset.ordering_keys, key=lambda k: k.precedence)

        # Find clustering key (group column) and sequence key
        group_col: str | None = None
        seq_col: str | None = None

        for key in keys:
            if key.semantic == "mnf:ClusteringForIndex":
                group_col = key.column_name
            elif key.semantic == "mnf:MeaningfulSequence":
                seq_col = key.column_name

        if group_col and seq_col:
            attestations.extend(validate_monotonic_within_groups(
                file_path,
                dataset_uri=dataset.uri,
                group_column=group_col,
                value_column=seq_col,
            ))

        return attestations

    def _check_aggregations(
        self,
        source_path: Path,
        target_path: Path,
        source_dataset_uri: str,
        target_dataset_uri: str,
    ) -> list[Attestation]:
        """Check aggregation consistency between source and target datasets."""
        aggregations = self.graph.get_aggregations(target_dataset_uri)
        attestations: list[Attestation] = []

        for agg in aggregations:
            if agg.source_dataset == source_dataset_uri:
                attestations.extend(validate_aggregation_sample(
                    source_path,
                    target_path,
                    dataset_uri=target_dataset_uri,
                    aggregation=agg,
                ))

        return attestations
