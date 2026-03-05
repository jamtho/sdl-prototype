"""
Schema-level validators.

These are the cheapest validators — they read only Parquet file metadata
(the footer), not any row data. They check that the physical structure of
the file matches what the Manifest graph declares.

This is the class of validator that catches the MMSI-as-string bug.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pyarrow.parquet as pq

from manifest.model import Attestation, ComputationalProfile, ValidationResult

# Maps MNF physical type URIs to sets of acceptable Arrow type strings.
# Multiple Arrow representations can satisfy a single MNF type.
MNF_TO_ARROW_TYPES: dict[str, set[str]] = {
    "mnf:Boolean": {"bool"},
    "mnf:Integer": {"int32"},
    "mnf:BigInt": {"int64"},
    "mnf:UBigInt": {"uint64"},
    "mnf:Float": {"float", "float32"},
    "mnf:Double": {"double", "float64"},
    "mnf:Varchar": {"string", "utf8", "large_string", "large_utf8"},
    "mnf:Date": {"date32[day]", "date32"},
    "mnf:TimestampTZ": {
        "timestamp[us, tz=UTC]",
        "timestamp[ns, tz=UTC]",
        "timestamp[ms, tz=UTC]",
        "timestamp[s, tz=UTC]",
    },
    "mnf:Blob": {"binary", "large_binary"},
    "mnf:IntegerList": {"list<item: int32>", "large_list<item: int32>"},
    "mnf:DoubleList": {"list<item: double>", "large_list<item: double>"},
    "mnf:VarcharList": {
        "list<item: string>",
        "list<item: utf8>",
        "large_list<item: string>",
        "large_list<item: utf8>",
    },
}


def validate_physical_types(
    file_path: Path,
    *,
    dataset_uri: str,
    expected_types: dict[str, str],
    **kwargs: Any,
) -> list[Attestation]:
    """
    Check that Parquet column types match MNF declarations.

    Reads only the Parquet footer metadata — zero data scan.

    Parameters
    ----------
    file_path : Path
        Path to a Parquet file.
    dataset_uri : str
        MNF URI of the dataset being validated.
    expected_types : dict[str, str]
        Mapping of column_name -> MNF physical type URI.
    """
    attestations: list[Attestation] = []

    try:
        pf = pq.ParquetFile(file_path)
    except Exception as e:
        return [Attestation(
            constraint_uri=f"{dataset_uri}/schema",
            dataset_uri=dataset_uri,
            file_path=str(file_path),
            result=ValidationResult.ERROR,
            details=f"Cannot read Parquet file: {e}",
            profile=ComputationalProfile.SCHEMA_CHECK,
        )]

    schema = pf.schema_arrow

    # Check for expected columns that are missing
    file_columns = {schema.field(i).name for i in range(len(schema))}

    for col_name, mnf_type in expected_types.items():
        constraint_uri = f"{dataset_uri}/column/{col_name}/physicalType"

        if col_name not in file_columns:
            attestations.append(Attestation(
                constraint_uri=constraint_uri,
                dataset_uri=dataset_uri,
                file_path=str(file_path),
                result=ValidationResult.FAIL,
                details=f"Column '{col_name}' not found in file. "
                        f"Available: {sorted(file_columns)}",
                profile=ComputationalProfile.SCHEMA_CHECK,
            ))
            continue

        field_idx = schema.get_field_index(col_name)
        actual_type = str(schema.field(field_idx).type)
        acceptable = MNF_TO_ARROW_TYPES.get(mnf_type, set())

        if actual_type in acceptable:
            attestations.append(Attestation(
                constraint_uri=constraint_uri,
                dataset_uri=dataset_uri,
                file_path=str(file_path),
                result=ValidationResult.PASS,
                details=f"'{col_name}': {actual_type} matches {mnf_type}",
                profile=ComputationalProfile.SCHEMA_CHECK,
            ))
        else:
            attestations.append(Attestation(
                constraint_uri=constraint_uri,
                dataset_uri=dataset_uri,
                file_path=str(file_path),
                result=ValidationResult.FAIL,
                details=f"TYPE MISMATCH: '{col_name}' has type '{actual_type}' "
                        f"but MNF declares {mnf_type} "
                        f"(acceptable: {acceptable})",
                profile=ComputationalProfile.SCHEMA_CHECK,
            ))

    # Check for unexpected columns (informational, not a failure)
    expected_cols = set(expected_types.keys())
    extra = file_columns - expected_cols
    if extra:
        attestations.append(Attestation(
            constraint_uri=f"{dataset_uri}/schema/extraColumns",
            dataset_uri=dataset_uri,
            file_path=str(file_path),
            result=ValidationResult.WARN,
            details=f"File contains undeclared columns: {sorted(extra)}",
            profile=ComputationalProfile.SCHEMA_CHECK,
        ))

    return attestations


def validate_column_presence(
    file_path: Path,
    *,
    dataset_uri: str,
    required_columns: list[str],
    **kwargs: Any,
) -> list[Attestation]:
    """Check that all required columns exist in the file."""
    try:
        pf = pq.ParquetFile(file_path)
    except Exception as e:
        return [Attestation(
            constraint_uri=f"{dataset_uri}/schema/presence",
            dataset_uri=dataset_uri,
            file_path=str(file_path),
            result=ValidationResult.ERROR,
            details=f"Cannot read Parquet file: {e}",
            profile=ComputationalProfile.SCHEMA_CHECK,
        )]

    file_columns = {pf.schema_arrow.field(i).name for i in range(len(pf.schema_arrow))}
    missing = set(required_columns) - file_columns

    if not missing:
        return [Attestation(
            constraint_uri=f"{dataset_uri}/schema/presence",
            dataset_uri=dataset_uri,
            file_path=str(file_path),
            result=ValidationResult.PASS,
            details=f"All {len(required_columns)} required columns present.",
            profile=ComputationalProfile.SCHEMA_CHECK,
        )]
    else:
        return [Attestation(
            constraint_uri=f"{dataset_uri}/schema/presence",
            dataset_uri=dataset_uri,
            file_path=str(file_path),
            result=ValidationResult.FAIL,
            details=f"Missing columns: {sorted(missing)}",
            profile=ComputationalProfile.SCHEMA_CHECK,
        )]
