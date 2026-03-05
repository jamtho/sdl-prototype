# Manifest Toolkit

**Manifest** — describe, validate, and integrate data with formal semantics.

Manifest sits between a schema and a full ontology. It captures structural knowledge about data that goes beyond column names and types: semantic types, value ranges, physical ordering, derivation relationships, aggregation dependencies, provenance, and known deficiencies.

## Motivation

Data formats like Parquet tell you column names and physical types. Manifest lets you express everything else a machine (or an LLM) would need to know to work with your data correctly:

- That `mmsi` **must** be stored as `INTEGER`, not `VARCHAR` — and that a prediction-market `side` column must be one of `{"BUY", "SELL"}`, not just a string (type and enum constraints caught from metadata alone)
- That `conditionId` in a trades dataset and `condition_id` in a holders dataset refer to the same logical entity, even though column names differ
- That `geometry` is deterministically derived from `(latitude, longitude)`, so it can be recomputed rather than stored — while a `bids` column is physically Varchar but contains a JSON array of `{price, size}` objects that could be parsed into structured columns
- That AIS broadcast files are sorted by MMSI then timestamp — where MMSI ordering is for index efficiency but timestamp ordering carries semantic meaning (it's a vessel trajectory) — while Polymarket snapshots have no meaningful ordering at all
- That each Polymarket snapshot row is a point-in-time observation of a recurring entity (keyed by `condition_id`), while each AIS row is an independent event
- That the index file's `sog_mean` is the arithmetic mean of the broadcast file's `sog`, grouped by MMSI — a cross-dataset aggregation dependency the system can verify
- That AIS data has known gaps from NOAA's undocumented downsampling, and Polymarket schemas are inferred by Polars from JSON so columns may vary between files

All of this is expressed as RDF in Turtle files, queryable, composable, and machine-readable. See the [generated dataset tables](descriptions/generated/) for a readable view of what's described.

## Design Principles

- **Combinators over opaque leaves**: the system reasons about structure; domain-specific semantics live in extensible leaf terms identified by URI.
- **Description and verification are decoupled**: the graph stores assertions; validators are external tools whose results are recorded as attestations.
- **Physical and logical are both first-class**: storage layout (ordering, partitioning) carries semantic weight and is formally described.
- **Cost-aware**: validators declare their computational profile so the engine runs cheapest checks first.

## Quick Start

```bash
# Install (editable, from the repo root)
uv sync  # or: pip install -e .

# See what the Manifest graph describes (no data needed)
mnf describe --vocab vocabularies/ --desc descriptions/

# Generate browsable markdown tables from the descriptions
mnf generate-docs --vocab vocabularies/ --desc descriptions/ --out descriptions/generated/

# Instant schema check — catches type mismatches from Parquet metadata alone
mnf validate path/to/ais-2025-01-01.parquet \
    --dataset ais:DailyBroadcasts \
    --vocab vocabularies/ --desc descriptions/ \
    --max-level schema

# Full validation — value ranges, ordering, monotonicity
mnf validate path/to/ais-2025-01-01.parquet \
    --dataset ais:DailyBroadcasts \
    --vocab vocabularies/ --desc descriptions/ \
    --verbose

# Validate a Polymarket snapshot file
mnf validate path/to/gamma-markets/hour=00.parquet \
    --dataset pm:MarketSnapshots \
    --vocab vocabularies/ --desc descriptions/ \
    --verbose

# With companion index file — also checks aggregation consistency
mnf validate path/to/broadcasts/ais-2025-01-01.parquet \
    --dataset ais:DailyBroadcasts \
    --vocab vocabularies/ --desc descriptions/ \
    --companion path/to/index/ais-2025-01-01.parquet \
    --companion-dataset ais:DailyIndex \
    --verbose

# Inspect a Parquet file's raw metadata
mnf info path/to/data.parquet
```

## Python API

```python
from pathlib import Path
from manifest import ManifestGraph, ValidationEngine

# Load the graph — vocabulary + one or more domain descriptions
graph = ManifestGraph()
graph.load("vocabularies/mnf_core.ttl")
graph.load("descriptions/ais_description.ttl")
graph.load("descriptions/polymarket_description.ttl")

# Inspect what's described — works across both domains at once
for ds_uri in graph.list_datasets():
    ds = graph.get_dataset(ds_uri)
    print(f"{ds.label}: {len(ds.columns)} columns")

# Validate a file against its description
engine = ValidationEngine(graph)
attestations = engine.validate_file(
    Path("data/gamma-markets/hour=00.parquet"),
    "pm:MarketSnapshots",
    verbose=True,
)
for a in attestations:
    print(a.summary_line())

# Explore metadata — semantic types, derivations, cross-dataset links
st = graph.get_semantic_type("ais:MMSI")
print(f"MMSI requires: {st.required_physical_type}, range: [{st.min_inclusive}, {st.max_inclusive}]")

derivations = graph.get_derivations("pm:MarketSnapshots")   # spread <- bestAsk, bestBid
aggregations = graph.get_aggregations("ais:DailyIndex")     # broadcasts -> index
deficiencies = graph.get_known_deficiencies("pm:MarketSnapshots")
```

## Validation Levels

Validators run in cost order, cheapest first:

| Level | Profile | What it checks | Data read |
|-------|---------|---------------|-----------|
| 0 | `SCHEMA_CHECK` | Physical types, column presence | Parquet footer only |
| 1 | `PER_VALUE` | Value ranges from semantic types | Column scan |
| 2 | `FULL_SCAN` | Constant columns, partition keys | Full file |
| 3 | `SEQUENTIAL_SCAN` | Row ordering, within-group monotonicity | Ordered scan |
| — | `FULL_SCAN` | Aggregation consistency (with companion) | Both files |

Use `--max-level schema` for instant type-mismatch detection.

## Structure

```
manifest-toolkit/
├── manifest/                 # Python package
│   ├── model.py              # Core data types (Attestation, ColumnInfo, etc.)
│   ├── graph.py              # Manifest graph loader and query layer (rdflib)
│   ├── engine.py             # Graph-driven validation orchestrator
│   ├── registry.py           # Extensible validator registry
│   ├── cli.py                # Click CLI
│   └── validators/           # Built-in validators
│       ├── schema.py         #   Physical type checks (Parquet metadata only)
│       ├── values.py         #   Value range checks (DuckDB scan)
│       ├── ordering.py       #   Row ordering + monotonicity (DuckDB)
│       └── aggregation.py    #   Index/summary consistency (DuckDB)
├── vocabularies/             # Core Manifest vocabulary (domain-independent)
│   └── mnf_core.ttl
├── descriptions/             # Domain-specific descriptions
│   ├── ais_description.ttl           # NOAA AIS maritime data
│   ├── polymarket_description.ttl    # Polymarket prediction-market data
│   └── generated/                    # Markdown tables (regenerate with mnf generate-docs)
│       ├── ais_description.md
│       └── polymarket_description.md
├── docs/
│   └── vocabulary-evolution.md       # How the Polymarket domain drove vocabulary extensions
├── pyproject.toml
└── README.md
```

## Current State and Limitations

This is a v0.1 prototype. It works end-to-end against real data, but there are important things to know:

**The engine is graph-driven but not yet fully generic.** It reads the Manifest graph to discover columns, semantic types, ordering keys, and aggregation relationships, and automatically dispatches built-in validators based on what it finds. However, the combinator-based constraint model in the Turtle (the `mnf:Grouped` / `mnf:Ordered` / `mnf:innerConstraint` chains) is not yet walked generically as an interpreter — the engine recognises specific patterns (ordering + monotonicity within groups) rather than interpreting arbitrary combinator trees. Making that fully generic is the natural next evolution.

**The validator registry exists but isn't wired into the engine yet.** `ValidatorRegistry` is there for when you need to register domain-specific validators by URI (e.g. a custom H3 derivation checker, or the `MaxConsecutiveImpliedSpeed` sequential aggregation). Currently the engine dispatches directly to built-in validators. The registry becomes the extension point when custom domain validators are needed.

**Standard aggregations are verified automatically; custom ones are skipped.** The aggregation validator handles `MIN`, `MAX`, `MEAN`, `COUNT`, `COUNT DISTINCT`, and `DISTINCT LIST` by recomputing them from source data and comparing. Sequential/windowed aggregations like `MaxConsecutiveImpliedSpeed` and `HaversineFirstToLast` need domain-specific validators that would be registered via the registry.

**Currently tied to Parquet on local filesystem.** The validators use `pyarrow` for schema inspection and `duckdb` for data queries, both reading local Parquet files. S3 support is straightforward (DuckDB and PyArrow both support S3 paths) but isn't parameterised yet. Extending to other formats (JSON, CSV, database tables) is a future direction — the Manifest vocabulary itself is format-agnostic, only the validators are Parquet-specific.

**New vocabulary terms don't yet have validators.** The vocabulary extensions added for the Polymarket domain (`AllowedValues`, `entityKey`, `embeddedStructure`, `ForeignKey`, `schemaStability`, `SameEntity`, `CompositePartitionScheme`) are fully expressible in the graph but the validation engine doesn't yet check them. For example, the engine doesn't yet verify that a `TradeSide` column only contains values from its `AllowedValues` set, or that a `ForeignKey` relationship has matching values across datasets. The terms are immediately useful for documentation and for LLM/tool consumption; automated validation will follow.

## Adding a New Domain

1. Define semantic types for your domain in a new `.ttl` file in `descriptions/`
2. Describe your datasets: columns, physical types, semantic types
3. Declare derivations, aggregation relationships, ordering, provenance
4. Use the newer vocabulary terms where applicable: `entityKey` for snapshot data, `AllowedValues` for categoricals, `embeddedStructure` for JSON-in-string, `ForeignKey` for cross-dataset links, `SameEntity` for shared identifiers, `schemaStability` for inferred schemas, `CompositePartitionScheme` for multi-level partitioning
5. Run `mnf validate` — all standard checks (schema, ranges, ordering) work automatically
6. For domain-specific constraints, implement validators and register them via `ValidatorRegistry`

The core vocabulary was extended once — when modelling Polymarket prediction-market data surfaced 7 genuinely domain-independent gaps (enum constraints, entity keys, embedded structure, multi-level partitioning, foreign keys, schema stability, cross-dataset identity). All additions were backward-compatible. See [`docs/vocabulary-evolution.md`](docs/vocabulary-evolution.md) for the full story.

## Two Domain Examples

Manifest ships with two domain descriptions that together exercise the full vocabulary:

| | AIS Maritime Data | Polymarket Prediction Markets |
|-|-------------------|-------------------------------|
| **File** | `descriptions/ais_description.ttl` | `descriptions/polymarket_description.ttl` |
| **Datasets** | 2 (broadcasts + index) | 9 (6 core + 3 reference) |
| **Row semantics** | Events (each row = one broadcast) | Snapshots (same entity repeated) |
| **Ordering** | Meaningful (MMSI + timestamp) | None (poll arrival order) |
| **Partitioning** | Single-level (daily) | Two-level (date + hour) |
| **Schema** | Fixed (declared) | Inferred (Polars from JSON) |
| **Cross-dataset links** | Aggregation (broadcasts -> index) | Foreign keys + entity identity |
| **Key vocabulary exercised** | Ordering semantics, aggregation relationships, column groups | Entity keys, embedded structure, allowed values, composite partitions, FK, SameEntity |

## Dependencies

- `rdflib >= 7.0` — RDF graph loading and SPARQL
- `duckdb >= 1.0` — efficient Parquet scanning for validation queries
- `pyarrow >= 15.0` — Parquet schema inspection
- `click >= 8.0` — CLI

Optional: `h3` (for H3 derivation validation), `pytest` (for tests).
