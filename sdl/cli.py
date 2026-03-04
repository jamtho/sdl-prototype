"""
SDL Toolkit CLI.

Usage:
    sdl validate <file.parquet> --dataset ais:DailyBroadcasts --vocab vocab/ --desc desc/
    sdl validate <broadcast.parquet> --dataset ais:DailyBroadcasts --companion <index.parquet> --companion-dataset ais:DailyIndex
    sdl describe <vocab_dir> <desc_dir>
    sdl generate-docs --vocab vocabularies/ --desc descriptions/ --out descriptions/generated/
    sdl info <file.parquet>
"""

from __future__ import annotations

from pathlib import Path

import click
from rdflib import Graph, Namespace, URIRef

from sdl.engine import ValidationEngine
from sdl.graph import SDLGraph, SDL, RDF, RDFS, _str, _label_or_str, _lit_str
from sdl.model import ComputationalProfile, ValidationResult


def _load_graph(
    vocab_paths: tuple[str, ...],
    desc_paths: tuple[str, ...],
) -> SDLGraph:
    """Load vocabulary and description files into an SDLGraph."""
    graph = SDLGraph()
    for p in vocab_paths:
        path = Path(p)
        if path.is_dir():
            graph.load_directory(path)
        else:
            graph.load(path)
    for p in desc_paths:
        path = Path(p)
        if path.is_dir():
            graph.load_directory(path)
        else:
            graph.load(path)
    return graph


@click.group()
def main() -> None:
    """SDL Toolkit — Structural Data Language for data lakes."""
    pass


@main.command()
@click.argument("file_path", type=click.Path(exists=True))
@click.option(
    "--dataset", "-d",
    required=True,
    help="SDL dataset URI (e.g. ais:DailyBroadcasts)",
)
@click.option(
    "--vocab", "-v",
    multiple=True,
    required=True,
    help="Path to vocabulary .ttl file or directory",
)
@click.option(
    "--desc",
    multiple=True,
    required=True,
    help="Path to description .ttl file or directory",
)
@click.option(
    "--companion", "-c",
    type=click.Path(exists=True),
    default=None,
    help="Path to companion file (e.g. index file)",
)
@click.option(
    "--companion-dataset",
    default=None,
    help="SDL dataset URI for the companion file",
)
@click.option(
    "--max-level",
    type=click.Choice(["schema", "values", "scan", "sequential"]),
    default="sequential",
    help="Maximum validation depth",
)
@click.option("--turtle", is_flag=True, help="Output attestations as Turtle")
@click.option("--verbose", is_flag=True, help="Print progress")
def validate(
    file_path: str,
    dataset: str,
    vocab: tuple[str, ...],
    desc: tuple[str, ...],
    companion: str | None,
    companion_dataset: str | None,
    max_level: str,
    turtle: bool,
    verbose: bool,
) -> None:
    """Validate a Parquet file against its SDL description."""
    level_map = {
        "schema": ComputationalProfile.SCHEMA_CHECK,
        "values": ComputationalProfile.PER_VALUE,
        "scan": ComputationalProfile.FULL_SCAN,
        "sequential": ComputationalProfile.SEQUENTIAL_SCAN,
    }

    graph = _load_graph(vocab, desc)
    engine = ValidationEngine(graph)

    attestations = engine.validate_file(
        Path(file_path),
        dataset,
        companion_path=Path(companion) if companion else None,
        companion_dataset_uri=companion_dataset,
        max_profile=level_map[max_level],
        verbose=verbose,
    )

    # Summary
    passes = sum(1 for a in attestations if a.result == ValidationResult.PASS)
    fails = sum(1 for a in attestations if a.result == ValidationResult.FAIL)
    warns = sum(1 for a in attestations if a.result == ValidationResult.WARN)
    errors = sum(1 for a in attestations if a.result == ValidationResult.ERROR)

    click.echo(f"\n{'=' * 72}")
    click.echo(
        f"  {passes} passed  {fails} failed  {warns} warnings  {errors} errors"
    )
    click.echo(f"{'=' * 72}\n")

    for a in attestations:
        click.echo(a.summary_line())
        if a.result != ValidationResult.PASS:
            for line in a.details.split("\n"):
                click.echo(f"      {line}")

    if turtle:
        click.echo("\n# --- Attestation Triples ---")
        click.echo("@prefix sdl: <http://example.org/sdl#> .")
        click.echo("@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .")
        click.echo()
        for a in attestations:
            click.echo(a.to_turtle())

    # Exit code: non-zero if any failures
    if fails > 0 or errors > 0:
        raise SystemExit(1)


@main.command()
@click.option(
    "--vocab", "-v",
    multiple=True,
    required=True,
    help="Path to vocabulary .ttl file or directory",
)
@click.option(
    "--desc",
    multiple=True,
    required=True,
    help="Path to description .ttl file or directory",
)
def describe(vocab: tuple[str, ...], desc: tuple[str, ...]) -> None:
    """Show a summary of datasets described in the SDL graph."""
    graph = _load_graph(vocab, desc)

    for ds_uri in graph.list_datasets():
        ds = graph.get_dataset(ds_uri)
        click.echo(f"\n{'=' * 60}")
        click.echo(f"Dataset: {ds.label}")
        click.echo(f"URI:     {ds.uri}")
        click.echo(f"Format:  {ds.file_format}")

        if ds.partition_path_template:
            click.echo(f"Path:    {ds.partition_path_template}")
        if ds.partition_granularity:
            click.echo(f"Partitioned: {ds.partition_granularity}")

        click.echo(f"\nColumns ({len(ds.columns)}):")
        for col in sorted(ds.columns, key=lambda c: c.name):
            sem = f"  [{col.semantic_type}]" if col.semantic_type else ""
            click.echo(f"  {col.name:24s} {col.physical_type:16s}{sem}")

        if ds.ordering_keys:
            keys = sorted(ds.ordering_keys, key=lambda k: k.precedence)
            click.echo(f"\nRow ordering:")
            for k in keys:
                click.echo(
                    f"  {k.precedence}. {k.column_name} {k.direction} "
                    f"({k.semantic})"
                )

        derivations = graph.get_derivations(ds_uri)
        if derivations:
            click.echo(f"\nDerivations:")
            for d in derivations:
                props = ", ".join(d.properties) if d.properties else ""
                click.echo(
                    f"  {d.derived_column} <- {d.source_columns} "
                    f"via {d.function_uri} [{props}]"
                )

        deficiencies = graph.get_known_deficiencies(ds_uri)
        if deficiencies:
            click.echo(f"\nKnown deficiencies:")
            for d in deficiencies:
                click.echo(f"  [{d['severity']}] {d['description'][:80]}...")

        companions = graph.get_companions(ds_uri)
        if companions:
            click.echo(f"\nCompanions: {', '.join(companions)}")

    # Show aggregation relationships
    for ds_uri in graph.list_datasets():
        aggs = graph.get_aggregations(ds_uri)
        for agg in aggs:
            click.echo(f"\n{'=' * 60}")
            click.echo(f"Aggregation: {agg.source_dataset} -> {agg.target_dataset}")
            click.echo(f"Group by: {agg.group_by_column}")
            click.echo(f"Columns ({len(agg.aggregated_columns)}):")
            for ac in agg.aggregated_columns:
                order = f" (ordered by {ac.within_group_ordering})" if ac.within_group_ordering else ""
                click.echo(
                    f"  {ac.target_column:24s} = "
                    f"{ac.function_uri}({', '.join(ac.source_columns)})"
                    f"{order}"
                )


@main.command()
@click.argument("file_path", type=click.Path(exists=True))
def info(file_path: str) -> None:
    """Show Parquet file metadata (for quick inspection)."""
    import pyarrow.parquet as pq

    pf = pq.ParquetFile(file_path)
    meta = pf.metadata
    schema = pf.schema_arrow

    click.echo(f"File: {file_path}")
    click.echo(f"Rows: {meta.num_rows:,}")
    click.echo(f"Row groups: {meta.num_row_groups}")
    click.echo(f"Columns: {meta.num_columns}")
    click.echo(f"Created by: {meta.created_by}")
    click.echo(f"Format version: {meta.format_version}")
    click.echo()

    click.echo("Schema:")
    for i in range(len(schema)):
        f = schema.field(i)
        click.echo(f"  {f.name:24s} {str(f.type):30s} nullable={f.nullable}")

    if meta.num_row_groups > 0:
        click.echo(f"\nRow group 0 (of {meta.num_row_groups}):")
        rg = meta.row_group(0)
        click.echo(f"  Rows: {rg.num_rows:,}")
        for j in range(rg.num_columns):
            col = rg.column(j)
            click.echo(
                f"  {col.path_in_schema:24s} "
                f"compressed={col.total_compressed_size:>10,} "
                f"uncompressed={col.total_uncompressed_size:>10,}"
            )


@main.command("generate-docs")
@click.option(
    "--vocab", "-v",
    multiple=True,
    required=True,
    help="Path to vocabulary .ttl file or directory",
)
@click.option(
    "--desc",
    multiple=True,
    required=True,
    help="Path to description .ttl file or directory",
)
@click.option(
    "--out", "-o",
    required=True,
    type=click.Path(),
    help="Output directory for generated markdown",
)
def generate_docs(vocab: tuple[str, ...], desc: tuple[str, ...], out: str) -> None:
    """Generate markdown documentation from SDL descriptions."""
    graph = _load_graph(vocab, desc)
    out_dir = Path(out)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Collect all .ttl description files
    desc_files: list[Path] = []
    for p in desc:
        path = Path(p)
        if path.is_dir():
            desc_files.extend(sorted(path.glob("*.ttl")))
        else:
            desc_files.append(path)

    # For each description file, find which datasets it declares
    for desc_file in desc_files:
        tmp = Graph()
        tmp.parse(str(desc_file), format="turtle")
        ds_uris = [
            _str(s) for s in tmp.subjects(RDF.type, SDL.Dataset)
        ]
        if not ds_uris:
            continue

        md_path = out_dir / desc_file.with_suffix(".md").name
        md = _render_description(graph, ds_uris, desc_file.name)
        md_path.write_text(md, encoding="utf-8")
        click.echo(f"  wrote {md_path}")


def _render_description(
    graph: SDLGraph, ds_uris: list[str], source_filename: str,
) -> str:
    """Render markdown for all datasets from one description file."""
    g = graph.g
    lines: list[str] = []

    # Title — preserve all-caps acronyms like AIS
    stem = source_filename.replace("_description.ttl", "")
    title = stem.upper() if stem == stem.lower() and len(stem) <= 4 else stem.replace("_", " ").title()
    lines.append(f"# {title} Dataset Description")
    lines.append("")
    lines.append(f"*Generated from `{source_filename}` — do not edit.*")
    lines.append("")

    # Dataset summary table
    lines.append("## Datasets")
    lines.append("")
    lines.append("| Dataset | Row Semantics | Schema | Partitioning | Format |")
    lines.append("|---------|---------------|--------|--------------|--------|")
    for uri in ds_uris:
        ds = graph.get_dataset(uri)
        subj = graph._resolve_uri(uri)
        row_sem = _label_or_str(g, g.value(subj, SDL.rowSemantics))
        stability = _label_or_str(g, g.value(subj, SDL.schemaStability))
        part = ds.partition_granularity or "—"
        lines.append(
            f"| {ds.label} | {row_sem or '—'} | {stability or '—'} "
            f"| {part} | {ds.file_format} |"
        )
    lines.append("")

    # Per-dataset sections
    for uri in ds_uris:
        lines.extend(_render_dataset_section(graph, uri))

    # Semantic types reference
    sem_types = _render_semantic_types(graph, ds_uris)
    if sem_types:
        lines.extend(sem_types)

    # Cross-dataset relationships
    cross = _render_cross_dataset(graph, ds_uris)
    if cross:
        lines.append("## Cross-Dataset Relationships")
        lines.append("")
        lines.extend(cross)

    # Agent notes — adaptive to what's in this description
    lines.extend(_render_agent_notes(graph, ds_uris))

    return "\n".join(lines) + "\n"


def _render_dataset_section(graph: SDLGraph, uri: str) -> list[str]:
    """Render one dataset's full documentation section."""
    g = graph.g
    ds = graph.get_dataset(uri)
    subj = graph._resolve_uri(uri)
    lines: list[str] = []

    lines.append("---")
    lines.append("")
    lines.append(f"## {ds.label}")
    lines.append("")
    lines.append(f"**URI:** `{uri}`")

    comment = _lit_str(g.value(subj, RDFS.comment))
    if comment:
        lines.append(f"  \n{' '.join(comment.split())}")

    row_sem = _label_or_str(g, g.value(subj, SDL.rowSemantics))
    if row_sem:
        lines.append(f"  \n**Row semantics:** {row_sem}")
    stability = _label_or_str(g, g.value(subj, SDL.schemaStability))
    if stability:
        lines.append(f"  \n**Schema:** {stability}")
    if ds.partition_path_template:
        lines.append(f"  \n**Path template:** `{ds.partition_path_template}`")

    entity_key = g.value(subj, SDL.entityKey)
    if entity_key:
        ek_name = _lit_str(g.value(entity_key, SDL.columnName))
        lines.append(f"  \n**Entity key:** `{ek_name}`")

    lines.append("")

    # Columns table
    lines.append("### Columns")
    lines.append("")
    lines.append("| Name | Physical Type | Semantic Type | Nullable |")
    lines.append("|------|---------------|---------------|----------|")
    for col in sorted(ds.columns, key=lambda c: c.name):
        sem = col.semantic_type or ""
        nullable = "yes" if col.nullable else "no"
        lines.append(f"| `{col.name}` | {col.physical_type} | {sem} | {nullable} |")
    lines.append("")

    # Ordering
    if ds.ordering_keys:
        keys = sorted(ds.ordering_keys, key=lambda k: k.precedence)
        lines.append("### Ordering")
        lines.append("")
        lines.append("| # | Column | Direction | Semantic |")
        lines.append("|---|--------|-----------|----------|")
        for k in keys:
            lines.append(
                f"| {k.precedence} | `{k.column_name}` | {k.direction} | {k.semantic} |"
            )
        lines.append("")

    # Derivations
    derivations = graph.get_derivations(uri)
    if derivations:
        lines.append("### Derivations")
        lines.append("")
        lines.append("| Derived Column | Source Columns | Function | Properties |")
        lines.append("|----------------|----------------|----------|------------|")
        for d in derivations:
            src = ", ".join(f"`{s}`" for s in d.source_columns)
            props = ", ".join(d.properties) if d.properties else ""
            lines.append(f"| `{d.derived_column}` | {src} | {d.function_uri} | {props} |")
        lines.append("")

    # Known deficiencies
    deficiencies = graph.get_known_deficiencies(uri)
    if deficiencies:
        lines.append("### Known Deficiencies")
        lines.append("")
        lines.append("| Severity | Description |")
        lines.append("|----------|-------------|")
        for d in deficiencies:
            desc_text = " ".join(d["description"].split())
            lines.append(f"| {d['severity']} | {desc_text} |")
        lines.append("")

    return lines


def _render_semantic_types(graph: SDLGraph, ds_uris: list[str]) -> list[str]:
    """Render a reference table of all semantic types used across datasets."""
    g = graph.g
    # Collect unique semantic type URIs
    seen: set[str] = set()
    for uri in ds_uris:
        ds = graph.get_dataset(uri)
        for col in ds.columns:
            if col.semantic_type:
                seen.add(col.semantic_type)
    if not seen:
        return []

    lines: list[str] = []
    lines.append("---")
    lines.append("")
    lines.append("## Semantic Types Reference")
    lines.append("")
    lines.append("| Type | Label | Physical Type | Range | Unit | Description |")
    lines.append("|------|-------|---------------|-------|------|-------------|")

    for type_uri in sorted(seen):
        info = graph.get_semantic_type(type_uri)
        if info is None:
            lines.append(f"| {type_uri} | | | | | |")
            continue
        # Build range string
        parts: list[str] = []
        if info.min_inclusive is not None:
            parts.append(f"{info.min_inclusive}")
        elif info.min_exclusive is not None:
            parts.append(f">{info.min_exclusive}")
        if info.max_inclusive is not None:
            parts.append(f"{info.max_inclusive}")
        elif info.max_exclusive is not None:
            parts.append(f"<{info.max_exclusive}")
        range_str = "–".join(parts) if parts else ""

        comment = _lit_str(g.value(graph._resolve_uri(type_uri), RDFS.comment))
        desc = " ".join(comment.split()) if comment else ""
        lines.append(
            f"| {type_uri} | {info.label} | {info.required_physical_type or ''} "
            f"| {range_str} | {info.unit or ''} | {desc} |"
        )

    lines.append("")
    return lines


def _render_cross_dataset(graph: SDLGraph, ds_uris: list[str]) -> list[str]:
    """Render cross-dataset relationships: aggregations, foreign keys, same-entity."""
    g = graph.g
    lines: list[str] = []

    # Aggregations
    for uri in ds_uris:
        aggs = graph.get_aggregations(uri)
        for agg in aggs:
            lines.append("### Aggregation")
            lines.append("")
            lines.append(
                f"**{agg.source_dataset}** → **{agg.target_dataset}** "
                f"(grouped by `{agg.group_by_column}`)"
            )
            lines.append("")
            lines.append("| Target Column | Source Column(s) | Function |")
            lines.append("|---------------|------------------|----------|")
            for ac in agg.aggregated_columns:
                src = ", ".join(f"`{s}`" for s in ac.source_columns)
                func = _label_or_str(g, graph._resolve_uri(ac.function_uri))
                lines.append(f"| `{ac.target_column}` | {src} | {func} |")
            lines.append("")

    # Foreign keys
    fk_lines: list[str] = []
    ds_uris_resolved = {graph._resolve_uri(u) for u in ds_uris}
    for fk_node in g.subjects(RDF.type, SDL.ForeignKey):
        from_col = g.value(fk_node, SDL.foreignKeyFrom)
        to_col = g.value(fk_node, SDL.foreignKeyTo)
        if from_col is None or to_col is None:
            continue
        # Check if either column belongs to a dataset in our set
        from_ds = _find_dataset_for_column(g, from_col, ds_uris_resolved)
        to_ds = _find_dataset_for_column(g, to_col, ds_uris_resolved)
        if from_ds is None and to_ds is None:
            continue
        label = _lit_str(g.value(fk_node, RDFS.label)) or _str(fk_node)
        from_name = _lit_str(g.value(from_col, SDL.columnName))
        to_name = _lit_str(g.value(to_col, SDL.columnName))
        from_ds_label = _lit_str(g.value(from_ds, RDFS.label)) if from_ds else "?"
        to_ds_label = _lit_str(g.value(to_ds, RDFS.label)) if to_ds else "?"
        integrity = _label_or_str(g, g.value(fk_node, SDL.referentialIntegrity))
        fk_lines.append(
            f"| {label} | {from_ds_label}.`{from_name}` "
            f"| {to_ds_label}.`{to_name}` | {integrity} |"
        )

    if fk_lines:
        lines.append("### Foreign Keys")
        lines.append("")
        lines.append("| Relationship | From (Dataset.Column) | To (Dataset.Column) | Integrity |")
        lines.append("|-------------|----------------------|---------------------|-----------|")
        lines.extend(fk_lines)
        lines.append("")

    # Same entity (long format: one row per column)
    se_lines: list[str] = []
    for se_node in g.subjects(RDF.type, SDL.SameEntity):
        cols = list(g.objects(se_node, SDL.identifyingColumn))
        relevant = any(
            _find_dataset_for_column(g, col, ds_uris_resolved) is not None
            for col in cols
        )
        if not relevant:
            continue
        label = _lit_str(g.value(se_node, RDFS.label)) or _str(se_node)
        for col in cols:
            col_name = _lit_str(g.value(col, SDL.columnName))
            col_ds = _find_dataset_for_column(g, col, ds_uris_resolved)
            ds_label = _lit_str(g.value(col_ds, RDFS.label)) if col_ds else "?"
            se_lines.append(f"| {label} | {ds_label} | `{col_name}` |")

    if se_lines:
        lines.append("### Same Entity")
        lines.append("")
        lines.append("| Identity | Dataset | Column |")
        lines.append("|----------|---------|--------|")
        lines.extend(se_lines)
        lines.append("")

    return lines


def _render_agent_notes(graph: SDLGraph, ds_uris: list[str]) -> list[str]:
    """Render contextual notes for AI agents, adaptive to concepts present."""
    g = graph.g
    lines: list[str] = []

    # Detect which concepts are present
    row_sems: set[str] = set()
    stabilities: set[str] = set()
    has_entity_keys = False
    has_deficiencies = False
    has_ordering = False
    for uri in ds_uris:
        subj = graph._resolve_uri(uri)
        rs = _str(g.value(subj, SDL.rowSemantics))
        if rs:
            row_sems.add(rs)
        st = _str(g.value(subj, SDL.schemaStability))
        if st:
            stabilities.add(st)
        if g.value(subj, SDL.entityKey):
            has_entity_keys = True
        ds = graph.get_dataset(uri)
        if ds.ordering_keys:
            has_ordering = True
        if graph.get_known_deficiencies(uri):
            has_deficiencies = True

    ds_uris_resolved = {graph._resolve_uri(u) for u in ds_uris}
    has_fks = any(
        _find_dataset_for_column(g, g.value(fk, SDL.foreignKeyFrom), ds_uris_resolved) is not None
        or _find_dataset_for_column(g, g.value(fk, SDL.foreignKeyTo), ds_uris_resolved) is not None
        for fk in g.subjects(RDF.type, SDL.ForeignKey)
        if g.value(fk, SDL.foreignKeyFrom) is not None
    )
    has_same_entity = any(
        any(
            _find_dataset_for_column(g, col, ds_uris_resolved) is not None
            for col in g.objects(se, SDL.identifyingColumn)
        )
        for se in g.subjects(RDF.type, SDL.SameEntity)
    )
    has_aggregations = any(
        graph.get_aggregations(uri) for uri in ds_uris
    )

    lines.append("---")
    lines.append("")
    lines.append("## Notes for AI Agents")
    lines.append("")
    lines.append(
        "This section explains SDL concepts used in the tables above, "
        "to help you write correct queries against this data."
    )
    lines.append("")

    # Row semantics
    if row_sems:
        lines.append("**Row semantics** determine how to interpret rows:")
        lines.append("")
        if "sdl:EventRow" in row_sems:
            lines.append(
                "- **Event rows** (`sdl:EventRow`) — each row is an independent "
                "event or observation. No deduplication needed."
            )
        if "sdl:SnapshotRow" in row_sems:
            lines.append(
                "- **Snapshot rows** (`sdl:SnapshotRow`) — each row is a "
                "point-in-time observation of a recurring entity. The same entity "
                "appears multiple times. To get the latest state, deduplicate by "
                "entity key ordered by `_fetched_at` descending."
            )
        if "sdl:AggregateRow" in row_sems:
            lines.append(
                "- **Aggregate rows** (`sdl:AggregateRow`) — each row summarises "
                "a group of source rows. Check the Aggregation table for how "
                "columns relate to the source dataset."
            )
        lines.append("")

    # Entity keys
    if has_entity_keys:
        lines.append(
            "**Entity key** — the column that identifies which entity a snapshot "
            "row describes. Multiple rows with the same entity key are repeated "
            "observations over time, not distinct entities. Use "
            "`ROW_NUMBER() OVER (PARTITION BY {entity_key} ORDER BY _fetched_at DESC)` "
            "to select the most recent observation per entity within a file."
        )
        lines.append("")

    # Schema stability
    if stabilities:
        lines.append("**Schema stability** affects query robustness:")
        lines.append("")
        if "sdl:FixedSchema" in stabilities:
            lines.append(
                "- **Fixed** (`sdl:FixedSchema`) — all files have identical "
                "columns and types. Query without defensive casting."
            )
        if "sdl:InferredSchema" in stabilities:
            lines.append(
                "- **Inferred** (`sdl:InferredSchema`) — schema is inferred from "
                "data and may vary between files. Use `TRY_CAST` for type safety, "
                "handle potentially missing columns, and use `UNION BY NAME` when "
                "combining files from different time periods."
            )
        if "sdl:VariableSchema" in stabilities:
            lines.append(
                "- **Variable** (`sdl:VariableSchema`) — schema changes over "
                "time as the upstream source evolves. Query defensively."
            )
        lines.append("")

    # Ordering
    if has_ordering:
        lines.append(
            "**Row ordering** — files with declared ordering are physically sorted "
            "by the listed keys. DuckDB can exploit this for merge joins and "
            "ordered aggregations. The semantic column distinguishes keys that "
            "carry meaning (e.g. a time series) from keys used purely for "
            "index clustering."
        )
        lines.append("")

    # Cross-dataset: foreign keys, same entity, aggregations
    if has_fks:
        lines.append(
            "**Foreign keys** — the From and To columns are joinable across "
            "datasets, even when column names differ. Check the Integrity column: "
            "`sdl:PartialIntegrity` means some values may not resolve in the "
            "target (use LEFT JOIN rather than INNER JOIN if you need all rows)."
        )
        lines.append("")

    if has_same_entity:
        lines.append(
            "**Same entity** — these columns across different datasets refer to "
            "the same real-world entity and are joinable. Unlike foreign keys, "
            "same-entity is symmetric — neither side is the \"reference\" table."
        )
        lines.append("")

    if has_aggregations:
        lines.append(
            "**Aggregations** — the target dataset's columns are computed from "
            "the source dataset. Don't recompute what already exists in the "
            "aggregate table. The Function column shows exactly how each target "
            "column is derived."
        )
        lines.append("")

    # Deficiencies
    if has_deficiencies:
        lines.append(
            "**Known deficiencies** — documented data quality issues that may "
            "affect query correctness. Read these before writing queries that "
            "involve aggregation, deduplication, or cross-file joins."
        )
        lines.append("")

    # Notation
    lines.append(
        "**Notation** — `sdl:` prefixed terms are SDL vocabulary concepts. "
        "Domain-specific prefixes (e.g. `ais:`, `pm:`) identify semantic types "
        "and domain entities. Physical types like `sdl:Varchar`, `sdl:Double`, "
        "`sdl:Integer` map directly to DuckDB/Parquet types."
    )
    lines.append("")

    return lines


def _find_dataset_for_column(
    g: Graph, col_node: URIRef, ds_set: set[URIRef],
) -> URIRef | None:
    """Find which dataset a column belongs to, if any in ds_set."""
    for ds in g.subjects(SDL.hasColumn, col_node):
        if ds in ds_set:
            return ds
    return None


if __name__ == "__main__":
    main()
