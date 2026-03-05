"""
Value-level validators.

These scan data values using DuckDB. More expensive than schema checks
but still relatively cheap (DuckDB is very efficient at predicate scans
on Parquet).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import duckdb

from manifest.model import Attestation, ComputationalProfile, ValidationResult


def validate_value_ranges(
    file_path: Path,
    *,
    dataset_uri: str,
    range_specs: list[dict[str, Any]],
    **kwargs: Any,
) -> list[Attestation]:
    """
    Check that column values fall within declared ranges.

    Parameters
    ----------
    range_specs : list of dict
        Each dict has keys: column_name, and optionally
        min_inclusive, max_inclusive, min_exclusive, max_exclusive.
    """
    attestations: list[Attestation] = []
    con = duckdb.connect()

    for spec in range_specs:
        col = spec["column_name"]
        constraint_uri = f"{dataset_uri}/column/{col}/valueRange"

        conditions: list[str] = []
        desc_parts: list[str] = []

        if spec.get("min_inclusive") is not None:
            conditions.append(f'"{col}" >= {spec["min_inclusive"]}')
            desc_parts.append(f">= {spec['min_inclusive']}")
        if spec.get("max_inclusive") is not None:
            conditions.append(f'"{col}" <= {spec["max_inclusive"]}')
            desc_parts.append(f"<= {spec['max_inclusive']}")
        if spec.get("min_exclusive") is not None:
            conditions.append(f'"{col}" > {spec["min_exclusive"]}')
            desc_parts.append(f"> {spec['min_exclusive']}")
        if spec.get("max_exclusive") is not None:
            conditions.append(f'"{col}" < {spec["max_exclusive"]}')
            desc_parts.append(f"< {spec['max_exclusive']}")

        if not conditions:
            attestations.append(Attestation(
                constraint_uri=constraint_uri,
                dataset_uri=dataset_uri,
                file_path=str(file_path),
                result=ValidationResult.PASS,
                details=f"'{col}': no range constraints declared.",
                profile=ComputationalProfile.PER_VALUE,
            ))
            continue

        where = " AND ".join(conditions)
        query = f"""
            SELECT
                COUNT(*) AS total_non_null,
                COUNT(*) FILTER (WHERE NOT ({where})) AS violations,
                MIN("{col}") AS actual_min,
                MAX("{col}") AS actual_max
            FROM read_parquet('{file_path}')
            WHERE "{col}" IS NOT NULL
        """

        try:
            result = con.execute(query).fetchone()
            assert result is not None
            total, violations, actual_min, actual_max = result

            if violations == 0:
                attestations.append(Attestation(
                    constraint_uri=constraint_uri,
                    dataset_uri=dataset_uri,
                    file_path=str(file_path),
                    result=ValidationResult.PASS,
                    details=f"'{col}': all {total} values in range "
                            f"({', '.join(desc_parts)}). "
                            f"Actual: [{actual_min}, {actual_max}]",
                    profile=ComputationalProfile.PER_VALUE,
                ))
            else:
                attestations.append(Attestation(
                    constraint_uri=constraint_uri,
                    dataset_uri=dataset_uri,
                    file_path=str(file_path),
                    result=ValidationResult.FAIL,
                    details=f"'{col}': {violations}/{total} values out of range "
                            f"({', '.join(desc_parts)}). "
                            f"Actual: [{actual_min}, {actual_max}]",
                    profile=ComputationalProfile.PER_VALUE,
                ))
        except Exception as e:
            attestations.append(Attestation(
                constraint_uri=constraint_uri,
                dataset_uri=dataset_uri,
                file_path=str(file_path),
                result=ValidationResult.ERROR,
                details=f"'{col}': query failed: {e}",
                profile=ComputationalProfile.PER_VALUE,
            ))

    con.close()
    return attestations


def validate_constant_column(
    file_path: Path,
    *,
    dataset_uri: str,
    column_name: str,
    **kwargs: Any,
) -> list[Attestation]:
    """Check that a column has a single distinct non-null value (partition key)."""
    constraint_uri = f"{dataset_uri}/column/{column_name}/constant"
    con = duckdb.connect()

    try:
        result = con.execute(f"""
            SELECT
                COUNT(DISTINCT "{column_name}") AS n_distinct,
                MIN("{column_name}") AS the_value,
                COUNT(*) FILTER (WHERE "{column_name}" IS NULL) AS n_null
            FROM read_parquet('{file_path}')
        """).fetchone()
        assert result is not None
        n_distinct, the_value, n_null = result

        if n_distinct == 1 and n_null == 0:
            return [Attestation(
                constraint_uri=constraint_uri,
                dataset_uri=dataset_uri,
                file_path=str(file_path),
                result=ValidationResult.PASS,
                details=f"'{column_name}' is constant: {the_value}",
                profile=ComputationalProfile.FULL_SCAN,
            )]
        elif n_distinct == 1 and n_null > 0:
            return [Attestation(
                constraint_uri=constraint_uri,
                dataset_uri=dataset_uri,
                file_path=str(file_path),
                result=ValidationResult.WARN,
                details=f"'{column_name}' has one value ({the_value}) "
                        f"but {n_null} nulls.",
                profile=ComputationalProfile.FULL_SCAN,
            )]
        else:
            return [Attestation(
                constraint_uri=constraint_uri,
                dataset_uri=dataset_uri,
                file_path=str(file_path),
                result=ValidationResult.FAIL,
                details=f"'{column_name}' has {n_distinct} distinct values, "
                        f"expected 1.",
                profile=ComputationalProfile.FULL_SCAN,
            )]
    except Exception as e:
        return [Attestation(
            constraint_uri=constraint_uri,
            dataset_uri=dataset_uri,
            file_path=str(file_path),
            result=ValidationResult.ERROR,
            details=f"Query failed: {e}",
            profile=ComputationalProfile.FULL_SCAN,
        )]
    finally:
        con.close()
