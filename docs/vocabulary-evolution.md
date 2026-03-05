# Manifest Vocabulary Evolution: Lessons from Polymarket

*2026-03-04 (1 of 2)*

How modelling a prediction-market data store surfaced gaps in the original Manifest vocabulary, and the extensions that resolved them.

## Background

Manifest was initially designed around a single domain: NOAA AIS maritime data. AIS data has clean properties that made it a natural starting point — stable schemas, clear temporal ordering, well-defined aggregation relationships, and a single partition dimension (daily). The vocabulary that emerged was sufficient for that domain.

To test whether Manifest generalises, we modelled a fundamentally different domain: [Polymarket](https://polymarket.com) prediction-market data collected by a custom fetcher. This data has:

- **Snapshot semantics** (the same market polled repeatedly, not distinct events)
- **Schemas inferred from JSON** by Polars, not declared upfront
- **Structured data encoded as strings** (JSON arrays in Varchar columns)
- **Two-level Hive partitioning** (date + hour)
- **Cross-dataset referential relationships** (markets, trades, holders linked by condition IDs)
- **Variable-type columns** (a "price" column that's sometimes a float, sometimes an error object)

The exercise surfaced 10 vocabulary gaps. Seven required new vocabulary terms; three were adequately handled by existing mechanisms.

## The 10 Gaps

### Gap 1: Snapshot Semantics

**Problem.** AIS data is event-like: each row is a distinct position broadcast. Polymarket's market snapshots repeat the same entity (identified by market ID) across every hourly file. Manifest had no way to declare "this column is the entity key and rows are temporal snapshots."

Without this, a consumer has no machine-readable signal that the dataset needs deduplication by entity key, or that grouping by market ID across time is the expected access pattern.

**Resolution.** Added `mnf:entityKey` — a property on `mnf:Dataset` pointing to the column(s) that identify the repeated entity.

```turtle
# Before: only a comment
pm:MarketSnapshots a mnf:Dataset ;
    rdfs:comment "...keyed by market ID..." .

# After: formal declaration
pm:MarketSnapshots a mnf:Dataset ;
    mnf:entityKey pm:mkt_id .
```

Composite entity keys (e.g. holders keyed by condition_id + token) use multiple `mnf:entityKey` properties.

**Vocabulary addition:** `mnf:entityKey` (Section 12 of `mnf_core.ttl`)

---

### Gap 2: Enum / Categorical Constraints

**Problem.** `mnf:valueRange` only supports numeric bounds (`minInclusive`, `maxInclusive`, etc.). Polymarket has columns constrained to string enumerations — trade side must be `"BUY"` or `"SELL"`, market category must be one of a known set. There was no way to express this.

**Resolution.** Added `mnf:AllowedValues` class and `mnf:allowedValue` property, linked from a semantic type via `mnf:hasAllowedValues`.

```turtle
pm:TradeSide a mnf:SemanticType ;
    mnf:requiredPhysicalType mnf:Varchar ;
    mnf:hasAllowedValues [
        a mnf:AllowedValues ;
        mnf:allowedValue "BUY" ;
        mnf:allowedValue "SELL"
    ] .
```

For open-ended categoricals (like market category), the allowed values set can include a comment noting it's non-exhaustive.

**Vocabulary addition:** `mnf:AllowedValues`, `mnf:hasAllowedValues`, `mnf:allowedValue` (Section 11)

---

### Gap 3: Structured Data in String Columns

**Problem.** Several Polymarket columns store JSON arrays as Varchar strings — outcomes (`["Yes","No"]`), orderbook bids/asks (`[{"price":"0.50","size":"100"},...]`), nested holder objects. Manifest could declare the physical type as Varchar but had no way to describe what was *inside* the string.

This matters because a consumer needs to know these aren't just text — they require JSON parsing, and the inner structure has its own schema.

**Resolution.** Added `mnf:embeddedStructure` property on columns, pointing to an `mnf:EmbeddedStructure` that declares the encoding format and inner element type.

```turtle
pm:ob_bids a mnf:Column ;
    mnf:physicalType mnf:Varchar ;
    mnf:semanticType pm:JSONArray ;
    mnf:embeddedStructure [
        a mnf:EmbeddedStructure ;
        mnf:embeddedFormat "json" ;
        mnf:embeddedElementType "array<{price: string, size: string}>"
    ] .
```

This also addresses **Gap 8** (nested/repeated fields) — the `embeddedElementType` can describe arbitrary nesting.

**Vocabulary addition:** `mnf:embeddedStructure`, `mnf:EmbeddedStructure`, `mnf:embeddedFormat`, `mnf:embeddedElementType` (Section 13)

---

### Gap 4: Multi-Level Partitioning

**Problem.** AIS data uses single-dimension partitioning: one file per date. Polymarket uses two-level Hive partitioning: `dt=YYYY-MM-DD/hour=HH`. Manifest's `PartitionScheme` had a single `partitionColumn` and `partitionGranularity` — no way to express the second level.

The `pathTemplate` property captured the structure textually, but there was no formal way to declare two independent partition dimensions.

**Resolution.** Added `mnf:CompositePartitionScheme` (subclass of `mnf:PartitionScheme`) with `mnf:PartitionLevel` nodes, each having a `levelPrecedence`, `levelColumn`, and `levelGranularity`.

```turtle
pm:hourly_hive_partition a mnf:CompositePartitionScheme ;
    mnf:pathTemplate "data/parquet/{stream}/dt={date}/hour={hour}.parquet" ;
    mnf:hasPartitionLevel [
        a mnf:PartitionLevel ;
        mnf:levelPrecedence 1 ;
        mnf:levelColumn "dt" ;
        mnf:levelGranularity "daily"
    ] ;
    mnf:hasPartitionLevel [
        a mnf:PartitionLevel ;
        mnf:levelPrecedence 2 ;
        mnf:levelColumn "hour" ;
        mnf:levelGranularity "hourly"
    ] .
```

Because `CompositePartitionScheme` is a subclass of `PartitionScheme`, existing `mnf:partitionedBy` links work unchanged.

**Vocabulary addition:** `mnf:CompositePartitionScheme`, `mnf:PartitionLevel`, `mnf:hasPartitionLevel`, `mnf:levelPrecedence`, `mnf:levelColumn`, `mnf:levelGranularity` (Section 14)

---

### Gap 5: Foreign Key / Referential Relationships

**Problem.** Polymarket's datasets are linked by shared identifiers: trades reference markets via `conditionId`, holders reference markets the same way, orderbooks reference markets via `market`. Manifest had `mnf:companionOf` for co-partitioned datasets, but no concept for general referential links between datasets that are partitioned independently.

**Resolution.** Added `mnf:ForeignKey` class with `mnf:foreignKeyFrom` and `mnf:foreignKeyTo` properties, plus `mnf:referentialIntegrity` to declare the expected integrity level.

```turtle
pm:fk_trades_to_markets a mnf:ForeignKey ;
    mnf:foreignKeyFrom pm:tr_condition_id ;
    mnf:foreignKeyTo pm:mkt_condition_id ;
    mnf:referentialIntegrity "partial" ;
    rdfs:comment """Partial: some trades reference resolved markets
        no longer in active snapshots.""" .
```

The `referentialIntegrity` property acknowledges real-world data: strict (every FK resolves), eventual (may temporarily be missing), or partial (some values never resolve).

**Vocabulary addition:** `mnf:ForeignKey`, `mnf:foreignKeyFrom`, `mnf:foreignKeyTo`, `mnf:referentialIntegrity` (Section 15)

---

### Gap 6: Variable-Type Columns

**Problem.** The `price` column in `clob/prices` can be a float (the actual price) or an error object string (when the API returns an error). Since Polars infers types per batch, the same column might be Float64 in one hourly file and Varchar in another.

**Resolution.** No new vocabulary was needed. The existing `mnf:acceptablePhysicalType` partially covers this (allowing multiple valid types for a semantic type), and the specific data quality issue is documented via `mnf:KnownDeficiency`. This gap is more of a data quality problem than a vocabulary problem — Manifest correctly describes the *intended* type, and the deficiency documents the reality.

---

### Gap 7: Non-Semantic Row Ordering

**Problem.** AIS data has meaningful row ordering (MMSI clustering for index efficiency, timestamp ordering within each cluster). Polymarket's files have no meaningful ordering — rows arrive in poll order.

**Resolution.** No new vocabulary was needed. Manifest already handles this gracefully: simply omit `mnf:hasRowOrdering` from the `PhysicalLayout`. The absence of an ordering declaration correctly communicates that rows have no guaranteed or meaningful order.

---

### Gap 8: Nested / Repeated Fields

**Problem.** Holders contain arrays of holder objects; events contain nested market arrays. Manifest couldn't describe column-level nesting beyond list types.

**Resolution.** Addressed by the same `mnf:embeddedStructure` mechanism from Gap 3. The `embeddedElementType` property can describe arbitrary nesting:

```turtle
pm:hld_holders a mnf:Column ;
    mnf:physicalType mnf:Varchar ;
    mnf:embeddedStructure [
        a mnf:EmbeddedStructure ;
        mnf:embeddedFormat "json" ;
        mnf:embeddedElementType "array<{proxyWallet: string, name: string, amount: float, ...}>"
    ] .
```

---

### Gap 9: Schema Stability

**Problem.** AIS data has a stable, declared schema. Polymarket's Parquet schemas are entirely Polars-inferred — `schema.py` definitions exist in the fetcher but are *not applied* during compaction. Columns may appear or disappear depending on what the API returns in each batch. Manifest assumed schemas were fixed.

**Resolution.** Added `mnf:schemaStability` property with three levels: `FixedSchema`, `InferredSchema`, and `VariableSchema`.

```turtle
pm:MarketSnapshots a mnf:Dataset ;
    mnf:schemaStability mnf:InferredSchema .
```

This gives consumers a machine-readable signal about how much to trust the declared column list. `InferredSchema` means "these columns are typical but may vary between files."

**Vocabulary addition:** `mnf:schemaStability`, `mnf:SchemaStabilityLevel`, `mnf:FixedSchema`, `mnf:InferredSchema`, `mnf:VariableSchema` (Section 16)

---

### Gap 10: Cross-Dataset Entity Identity

**Problem.** The condition ID in `gamma/markets` is the same logical entity referenced by `conditionId` in trades, `condition_id` in holders, and `market` in orderbooks. These columns live in different datasets with different names. Manifest had no way to declare "these columns across datasets identify the same entity." This is different from `companionOf` (co-partitioning) and `ForeignKey` (directional reference) — it's a symmetric identity assertion.

**Resolution.** Added `mnf:SameEntity` class with `mnf:identifyingColumn` linking all the participating columns.

```turtle
pm:same_entity_condition_id a mnf:SameEntity ;
    rdfs:label "Condition ID identifies the same market across datasets" ;
    mnf:identifyingColumn pm:mkt_condition_id ;
    mnf:identifyingColumn pm:tr_condition_id ;
    mnf:identifyingColumn pm:hld_condition_id ;
    mnf:identifyingColumn pm:ob_market .
```

This is a symmetric, non-directional assertion — all four columns refer to the same entity. A query planner or data integration tool can use this to know that joining on any pair is valid.

**Vocabulary addition:** `mnf:SameEntity`, `mnf:identifyingColumn` (Section 17)

---

## Summary of Vocabulary Changes

| Section | Gap | New Terms | Type |
|---------|-----|-----------|------|
| 11 | Enum constraints | `AllowedValues`, `hasAllowedValues`, `allowedValue` | Class + properties |
| 12 | Snapshot semantics | `entityKey` | Property |
| 13 | Embedded structure | `embeddedStructure`, `EmbeddedStructure`, `embeddedFormat`, `embeddedElementType` | Class + properties |
| 14 | Multi-level partitioning | `CompositePartitionScheme`, `PartitionLevel`, `hasPartitionLevel`, `levelPrecedence`, `levelColumn`, `levelGranularity` | Classes + properties |
| 15 | Foreign keys | `ForeignKey`, `foreignKeyFrom`, `foreignKeyTo`, `referentialIntegrity` | Class + properties |
| 16 | Schema stability | `schemaStability`, `SchemaStabilityLevel`, `FixedSchema`, `InferredSchema`, `VariableSchema` | Class + property + instances |
| 17 | Entity identity | `SameEntity`, `identifyingColumn` | Class + property |

**Backward compatibility.** All additions are purely additive. Existing AIS descriptions require no changes. The `CompositePartitionScheme` subclasses `PartitionScheme`, so `partitionedBy` links work without modification.

## Reflections

The original README noted: *"The core vocabulary should not need to change for new domains. If it does, that's a signal that something belongs in the core that was missed."* The Polymarket exercise proved this exactly right — every gap we found was genuinely domain-independent:

- Entity keys apply to any snapshot/polling system (IoT sensors, API crawlers, price feeds)
- Enum constraints apply to any categorical data
- Embedded structure applies to any JSON-in-string column (common in data lakes)
- Multi-level partitioning is standard in Hive-style data stores
- Foreign keys are a universal relational concept
- Schema stability is relevant to any inferred-schema data pipeline
- Cross-dataset entity identity is fundamental to data integration

None of these are Polymarket-specific. The vocabulary was incomplete, not wrongly designed.
