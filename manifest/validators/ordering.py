"""
Ordering validators.

These verify physical row ordering and within-group monotonicity.
They require sequential access to the data.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import duckdb

from manifest.model import Attestation, ComputationalProfile, OrderingKeyInfo, ValidationResult


def validate_row_ordering(
    file_path: Path,
    *,
    dataset_uri: str,
    ordering_keys: list[OrderingKeyInfo],
    **kwargs: Any,
) -> list[Attestation]:
    """
    Verify that the file is physically sorted according to declared ordering.

    Uses DuckDB LAG window function to check that each row is >= the previous
    row on the declared sort keys with correct precedence.
    """
    if not ordering_keys:
        return [Attestation(
            constraint_uri=f"{dataset_uri}/ordering",
            dataset_uri=dataset_uri,
            file_path=str(file_path),
            result=ValidationResult.PASS,
            details="No ordering declared.",
            profile=ComputationalProfile.SEQUENTIAL_SCAN,
        )]

    # Sort by precedence
    keys = sorted(ordering_keys, key=lambda k: k.precedence)
    con = duckdb.connect()

    # Build violation check. For a composite sort (A, B):
    # violation if A < prev_A, or (A = prev_A and B < prev_B)
    lag_cols: list[str] = []
    select_parts: list[str] = []
    for i, key in enumerate(keys):
        col = f'"{key.column_name}"'
        lag = f"prev_{i}"
        lag_cols.append(f"LAG({col}) OVER (ORDER BY rowid) AS {lag}")
        select_parts.append((col, lag, key.direction))

    lag_select = ", ".join(lag_cols)

    # Build the violation condition
    conditions: list[str] = []
    for i, (col, lag, direction) in enumerate(select_parts):
        if direction == "descending":
            op_wrong = ">"
        else:
            op_wrong = "<"

        # violation at level i: all higher-precedence keys are equal,
        # and this key is in the wrong direction
        equal_prefix = " AND ".join(
            f"{select_parts[j][0]} = {select_parts[j][1]}"
            for j in range(i)
        )
        violation = f"{col} {op_wrong} {lag}"
        if equal_prefix:
            conditions.append(f"({equal_prefix} AND {violation})")
        else:
            conditions.append(f"({violation})")

    violation_where = " OR ".join(conditions)

    query = f"""
        WITH lagged AS (
            SELECT
                {', '.join(f'"{k.column_name}"' for k in keys)},
                {lag_select}
            FROM read_parquet('{file_path}')
        )
        SELECT COUNT(*) AS violations
        FROM lagged
        WHERE {' AND '.join(f'{s[1]} IS NOT NULL' for s in select_parts)}
          AND ({violation_where})
    """

    try:
        result = con.execute(query).fetchone()
        assert result is not None
        violations = result[0]

        key_desc = ", ".join(f"{k.column_name} {k.direction}" for k in keys)

        if violations == 0:
            return [Attestation(
                constraint_uri=f"{dataset_uri}/ordering",
                dataset_uri=dataset_uri,
                file_path=str(file_path),
                result=ValidationResult.PASS,
                details=f"File correctly ordered by ({key_desc}).",
                profile=ComputationalProfile.SEQUENTIAL_SCAN,
            )]
        else:
            return [Attestation(
                constraint_uri=f"{dataset_uri}/ordering",
                dataset_uri=dataset_uri,
                file_path=str(file_path),
                result=ValidationResult.FAIL,
                details=f"{violations} ordering violations for ({key_desc}).",
                profile=ComputationalProfile.SEQUENTIAL_SCAN,
            )]
    except Exception as e:
        return [Attestation(
            constraint_uri=f"{dataset_uri}/ordering",
            dataset_uri=dataset_uri,
            file_path=str(file_path),
            result=ValidationResult.ERROR,
            details=f"Ordering check failed: {e}",
            profile=ComputationalProfile.SEQUENTIAL_SCAN,
        )]
    finally:
        con.close()


def validate_monotonic_within_groups(
    file_path: Path,
    *,
    dataset_uri: str,
    group_column: str,
    value_column: str,
    strict: bool = False,
    **kwargs: Any,
) -> list[Attestation]:
    """
    Verify that value_column is monotonically non-decreasing (or strictly
    increasing) within each group defined by group_column.

    Assumes the file is already sorted by (group_column, value_column).
    """
    constraint_uri = f"{dataset_uri}/monotonic/{group_column}/{value_column}"
    con = duckdb.connect()

    op = "<" if strict else "<="
    op_desc = "strictly increasing" if strict else "non-decreasing"

    query = f"""
        WITH windowed AS (
            SELECT
                "{group_column}",
                "{value_column}",
                LAG("{value_column}") OVER (
                    PARTITION BY "{group_column}"
                    ORDER BY rowid
                ) AS prev_val
            FROM read_parquet('{file_path}')
        )
        SELECT
            COUNT(*) AS violations,
            COUNT(DISTINCT "{group_column}") AS affected_groups
        FROM windowed
        WHERE prev_val IS NOT NULL
          AND "{value_column}" {op} prev_val
    """

    try:
        result = con.execute(query).fetchone()
        assert result is not None
        violations, affected_groups = result

        if violations == 0:
            return [Attestation(
                constraint_uri=constraint_uri,
                dataset_uri=dataset_uri,
                file_path=str(file_path),
                result=ValidationResult.PASS,
                details=f"'{value_column}' is {op_desc} within all "
                        f"'{group_column}' groups.",
                profile=ComputationalProfile.SEQUENTIAL_SCAN,
            )]
        else:
            return [Attestation(
                constraint_uri=constraint_uri,
                dataset_uri=dataset_uri,
                file_path=str(file_path),
                result=ValidationResult.FAIL,
                details=f"{violations} monotonicity violations across "
                        f"{affected_groups} '{group_column}' groups.",
                profile=ComputationalProfile.SEQUENTIAL_SCAN,
            )]
    except Exception as e:
        return [Attestation(
            constraint_uri=constraint_uri,
            dataset_uri=dataset_uri,
            file_path=str(file_path),
            result=ValidationResult.ERROR,
            details=f"Monotonicity check failed: {e}",
            profile=ComputationalProfile.SEQUENTIAL_SCAN,
        )]
    finally:
        con.close()
