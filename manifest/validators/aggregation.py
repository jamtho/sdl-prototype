"""
Aggregation validators.

Verify that summary/index datasets are consistent with their source data.
These compare recomputed aggregations against stored values for sampled groups.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import duckdb

from manifest.model import (
    AggregatedColumnInfo,
    AggregationInfo,
    Attestation,
    ComputationalProfile,
    ValidationResult,
)

# Standard MNF aggregation function URIs mapped to DuckDB SQL expressions.
# The placeholder {col} is replaced with the actual column name.
STANDARD_AGG_SQL: dict[str, str] = {
    "mnf:Min": 'MIN("{col}")',
    "mnf:Max": 'MAX("{col}")',
    "mnf:Mean": 'AVG("{col}")',
    "mnf:Sum": 'SUM("{col}")',
    "mnf:Count": "COUNT(*)",
    "mnf:CountDistinct": 'COUNT(DISTINCT "{col}")',
    "mnf:DistinctList": 'LIST(DISTINCT "{col}")',
}


def _is_standard_agg(func_uri: str) -> bool:
    return func_uri in STANDARD_AGG_SQL


def _build_agg_expr(func_uri: str, source_columns: list[str]) -> str | None:
    """Build a DuckDB SQL aggregate expression, or None for custom aggs."""
    template = STANDARD_AGG_SQL.get(func_uri)
    if template is None:
        return None
    # Use first source column for the placeholder
    col = source_columns[0] if source_columns else "*"
    return template.replace("{col}", col)


def validate_aggregation_sample(
    source_path: Path,
    target_path: Path,
    *,
    dataset_uri: str,
    aggregation: AggregationInfo,
    sample_groups: int = 50,
    rel_tol: float = 1e-6,
    **kwargs: Any,
) -> list[Attestation]:
    """
    Spot-check aggregation consistency by sampling groups.

    For each sampled group (e.g. MMSI), recomputes standard aggregations
    from the source data and compares against stored values in the target.
    Custom/sequential aggregations are skipped (they need their own
    domain-specific validators).
    """
    attestations: list[Attestation] = []
    con = duckdb.connect()

    group_col = aggregation.group_by_column

    # Identify which aggregated columns we can verify (standard aggs only)
    verifiable: list[tuple[AggregatedColumnInfo, str]] = []
    skipped: list[str] = []

    for ac in aggregation.aggregated_columns:
        expr = _build_agg_expr(ac.function_uri, ac.source_columns)
        if expr is not None:
            verifiable.append((ac, expr))
        else:
            skipped.append(f"{ac.target_column} ({ac.function_uri})")

    if not verifiable:
        return [Attestation(
            constraint_uri=f"{dataset_uri}/aggregation",
            dataset_uri=dataset_uri,
            result=ValidationResult.WARN,
            details="No standard aggregations to verify. "
                    f"Skipped custom: {skipped}",
            profile=ComputationalProfile.FULL_SCAN,
        )]

    try:
        # Sample groups from the target
        sample_query = f"""
            SELECT DISTINCT "{group_col}"
            FROM read_parquet('{target_path}')
            USING SAMPLE {sample_groups}
        """
        group_values = [
            row[0] for row in con.execute(sample_query).fetchall()
        ]

        if not group_values:
            return [Attestation(
                constraint_uri=f"{dataset_uri}/aggregation",
                dataset_uri=dataset_uri,
                result=ValidationResult.WARN,
                details="No groups found in target file.",
                profile=ComputationalProfile.FULL_SCAN,
            )]

        group_list = ", ".join(
            f"'{v}'" if isinstance(v, str) else str(v)
            for v in group_values
        )

        # Recompute aggregations from source
        agg_exprs: list[str] = []
        agg_aliases: list[str] = []
        for ac, expr in verifiable:
            alias = f"recomputed_{ac.target_column}"
            agg_exprs.append(f"{expr} AS {alias}")
            agg_aliases.append(alias)

        recompute_query = f"""
            SELECT
                "{group_col}",
                {', '.join(agg_exprs)}
            FROM read_parquet('{source_path}')
            WHERE "{group_col}" IN ({group_list})
            GROUP BY "{group_col}"
        """
        recomputed = {
            row[0]: row[1:]
            for row in con.execute(recompute_query).fetchall()
        }

        # Fetch stored values from target
        target_cols = ", ".join(
            f'"{ac.target_column}"' for ac, _ in verifiable
        )
        stored_query = f"""
            SELECT
                "{group_col}",
                {target_cols}
            FROM read_parquet('{target_path}')
            WHERE "{group_col}" IN ({group_list})
        """
        stored = {
            row[0]: row[1:]
            for row in con.execute(stored_query).fetchall()
        }

        # Compare
        total_checks: int = 0
        mismatches: list[str] = []

        for group_val in group_values:
            if group_val not in recomputed or group_val not in stored:
                continue

            rc_vals = recomputed[group_val]
            st_vals = stored[group_val]

            for i, (ac, _) in enumerate(verifiable):
                rc_v = rc_vals[i]
                st_v = st_vals[i]
                total_checks += 1

                if rc_v is None and st_v is None:
                    continue
                if rc_v is None or st_v is None:
                    mismatches.append(
                        f"  {group_col}={group_val}, {ac.target_column}: "
                        f"recomputed={rc_v}, stored={st_v}"
                    )
                    continue

                # For numeric types, use approximate comparison
                if isinstance(rc_v, (int, float)) and isinstance(st_v, (int, float)):
                    if isinstance(rc_v, int) and isinstance(st_v, int):
                        if rc_v != st_v:
                            mismatches.append(
                                f"  {group_col}={group_val}, "
                                f"{ac.target_column}: "
                                f"recomputed={rc_v}, stored={st_v}"
                            )
                    elif not math.isclose(
                        float(rc_v), float(st_v), rel_tol=rel_tol
                    ):
                        mismatches.append(
                            f"  {group_col}={group_val}, "
                            f"{ac.target_column}: "
                            f"recomputed={rc_v:.6f}, stored={st_v:.6f}"
                        )
                # For list types, compare as sorted sets
                elif isinstance(rc_v, list) and isinstance(st_v, list):
                    rc_set = set(str(x) for x in rc_v if x is not None)
                    st_set = set(str(x) for x in st_v if x is not None)
                    if rc_set != st_set:
                        mismatches.append(
                            f"  {group_col}={group_val}, "
                            f"{ac.target_column}: "
                            f"recomputed={sorted(rc_set)}, "
                            f"stored={sorted(st_set)}"
                        )

        if not mismatches:
            attestations.append(Attestation(
                constraint_uri=f"{dataset_uri}/aggregation",
                dataset_uri=dataset_uri,
                file_path=str(target_path),
                result=ValidationResult.PASS,
                details=f"All {total_checks} aggregation checks passed "
                        f"across {len(group_values)} sampled groups.",
                profile=ComputationalProfile.FULL_SCAN,
            ))
        else:
            attestations.append(Attestation(
                constraint_uri=f"{dataset_uri}/aggregation",
                dataset_uri=dataset_uri,
                file_path=str(target_path),
                result=ValidationResult.FAIL,
                details=f"{len(mismatches)} mismatches in {total_checks} "
                        f"checks:\n" + "\n".join(mismatches[:20]),
                profile=ComputationalProfile.FULL_SCAN,
            ))

        if skipped:
            attestations.append(Attestation(
                constraint_uri=f"{dataset_uri}/aggregation/custom",
                dataset_uri=dataset_uri,
                file_path=str(target_path),
                result=ValidationResult.WARN,
                details=f"Skipped custom aggregations (no built-in verifier): "
                        f"{', '.join(skipped)}",
                profile=ComputationalProfile.FULL_SCAN,
            ))

    except Exception as e:
        attestations.append(Attestation(
            constraint_uri=f"{dataset_uri}/aggregation",
            dataset_uri=dataset_uri,
            file_path=str(target_path),
            result=ValidationResult.ERROR,
            details=f"Aggregation validation failed: {e}",
            profile=ComputationalProfile.FULL_SCAN,
        ))
    finally:
        con.close()

    return attestations
