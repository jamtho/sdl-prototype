# Manifest Vocabulary Review: Findings, Actions, and Deferred Items

*2026-03-04 (2 of 2)*

A fresh-eyes review of the Manifest vocabulary design, conducted after the core vocabulary and both domain descriptions (AIS, Polymarket) were complete.

## What's strong

**Architecture.** The three-layer separation (vocabulary / description / validation) is correct. Most metadata systems conflate at least two of these.

**Combinators over opaque leaves.** The constraint algebra (ForEach, Grouped, Ordered, Conditional, And, Or) is the right abstraction. Domain semantics stay extensible at the leaves while the system reasons about structure.

**Computational profile.** Ordering validators by cost (schema-check -> per-value -> full-scan -> sequential-scan -> external) is practical and well-designed. Rare to see this made first-class.

**Known deficiencies.** Every schema system describes what data *should* be. Almost none describe what it *isn't*. The link from deficiency -> violated invariant -> constraint is genuinely useful for safe data integration.

**Two-domain validation.** Testing the vocabulary against a second, fundamentally different domain (Polymarket) was exactly the right strategy. The vocabulary-evolution doc is honest about the gaps this surfaced.

---

## Actions taken

### 1. String literals replaced with named individuals

**Problem.** The vocabulary defined `mnf:AllowedValues` for domain enum constraints, but used freeform string literals for its own structural enumerations. This meant no typo detection, no SPARQL queryability, and no `rdfs:comment` on individual values.

**Fix.** Introduced named individual classes and instances for seven properties:

| Property | Old range | New range | Individuals |
|----------|-----------|-----------|-------------|
| `mnf:keyDirection` | `xsd:string` | `mnf:SortDirection` | `mnf:Ascending`, `mnf:Descending` |
| `mnf:fileFormat` | `xsd:string` | `mnf:FileFormat` | `mnf:Parquet`, `mnf:CSV`, `mnf:ORC` |
| `mnf:partitionGranularity` | `xsd:string` | `mnf:TemporalGranularity` | `mnf:Daily`, `mnf:Hourly`, `mnf:Monthly`, `mnf:ByValue` |
| `mnf:levelGranularity` | `xsd:string` | `mnf:TemporalGranularity` | (shares the above) |
| `mnf:severity` | `xsd:string` | `mnf:SeverityLevel` | `mnf:Minor`, `mnf:Moderate`, `mnf:Severe` |
| `mnf:embeddedFormat` | `xsd:string` | `mnf:DataEncodingFormat` | `mnf:JSONEncoding`, `mnf:CSVEncoding` |
| `mnf:verificationResult` | `xsd:string` | `mnf:VerificationResultValue` | `mnf:Pass`, `mnf:Fail`, `mnf:Partial`, `mnf:Error` |
| `mnf:referentialIntegrity` | `xsd:string` | `mnf:ReferentialIntegrityLevel` | `mnf:StrictIntegrity`, `mnf:EventualIntegrity`, `mnf:PartialIntegrity` |

Each named individual carries an `rdfs:label` matching the old string value (e.g. `mnf:Ascending rdfs:label "ascending"`), so the Python API returns the same strings via a new `_label_or_str()` helper. Downstream code (validators, CLI) is unaffected.

### 2. Consistent `rdfs:Class` declarations

**Problem.** Some subclasses were properly declared (`mnf:ForEach a rdfs:Class ; rdfs:subClassOf mnf:Constraint`) while others omitted the `a rdfs:Class` triple (`mnf:ScalarConstraint rdfs:subClassOf mnf:Constraint`).

**Fix.** Added `a rdfs:Class` to all subclass declarations: `ScalarConstraint`, `PairConstraint`, `SequenceConstraint`, `WindowedSequenceConstraint`, `DatasetConstraint`, `GroupedConstraint`, `CompositePartitionScheme`, `PythonValidator`, `SPARQLValidator`, `DuckDBValidator`.

### 3. Added `mnf:Boolean` and `mnf:Float` physical types

**Problem.** The physical type vocabulary had no Boolean (forcing Polymarket to use `pm:BooleanString` with `mnf:Varchar`) and no 32-bit float (only `mnf:Double`).

**Fix.** Added `mnf:Boolean` (label "BOOLEAN") and `mnf:Float` (label "FLOAT"). Added `mnf:Float mnf:narrowerThan mnf:Double` to the type compatibility chain. Updated the Python schema validator's Arrow type mapping to include `bool` -> `mnf:Boolean` and `float32` -> `mnf:Float`.

### 4. Added `mnf:rowSemantics` and `mnf:snapshotTimestamp`

**Problem.** The vocabulary had `mnf:entityKey` for snapshot semantics but no general way to declare what a row represents (event vs. snapshot vs. aggregate), and no way to declare which column is the temporal dimension for snapshot datasets.

**Fix.** Added:
- `mnf:rowSemantics` (domain `mnf:Dataset`, range `mnf:RowSemanticsType`)
- `mnf:RowSemanticsType` class with `mnf:EventRow`, `mnf:SnapshotRow`, `mnf:AggregateRow`
- `mnf:snapshotTimestamp` (domain `mnf:Dataset`, range `mnf:Column`)

Updated descriptions:
- AIS `DailyBroadcasts` -> `mnf:EventRow`
- AIS `DailyIndex` -> `mnf:AggregateRow`
- Polymarket snapshot datasets -> `mnf:SnapshotRow` + `mnf:snapshotTimestamp` pointing to `_fetched_at`
- Polymarket `Trades` -> `mnf:EventRow`

### 5. Added `rdfs:domain` to constraint target properties

**Problem.** `mnf:appliesToDataset`, `mnf:appliesToColumn`, and `mnf:appliesToColumnGroup` had ranges declared but no domain, making them unmoored from the `mnf:Constraint` class.

**Fix.** Added `rdfs:domain mnf:Constraint` to all three.

### 6. Removed unused terms

- Removed `owl:` prefix (was imported but never used)
- Removed `mnf:ConstraintSignature` class (declared but never referenced)
- Updated section 2 header comment to say "DuckDB conventions" instead of "Parquet logical types"
- Added design principle 4 to the header: "Named individuals over string literals"

### 7. Updated both domain descriptions

All string literal usages in `ais_description.ttl` and `polymarket_description.ttl` updated to reference the new named individuals. Both descriptions also gained `mnf:rowSemantics` and `mnf:schemaStability` declarations where missing.

### 8. Python code updated for compatibility

- `graph.py`: Added `_label_or_str()` helper that resolves `rdfs:label` from named individuals, so downstream code continues to receive clean strings like `"ascending"` rather than `"mnf:Ascending"`.
- `model.py`: `Attestation.to_turtle()` now emits `mnf:verificationResult mnf:Pass` instead of `mnf:verificationResult "pass"`.
- `validators/schema.py`: Added `mnf:Boolean` and `mnf:Float` to the Arrow type mapping.

---

## Deferred items (not taken, with rationale)

### `mnf:levelColumn` string vs `mnf:Column` URI mismatch

`mnf:partitionColumn` points to a `mnf:Column` URI, but `mnf:levelColumn` is a plain string. This exists because Hive partition keys (like `dt`, `hour`) may not correspond to data columns — they're extracted from directory paths. Fixing this requires deciding whether to create phantom Column nodes for path-only keys, or to add a parallel `mnf:levelDataColumn` property. Both options add complexity for a currently-working pattern. Deferred until a third domain exercises this.

### `mnf:embeddedElementType` recursive modeling

The inner structure of embedded JSON is described as a free-text string (`"array<{price: string, size: string}>"`). This is essentially an ad-hoc schema language inside a string literal — the very problem Manifest exists to solve. A proper fix would use Manifest's own Column/PhysicalType vocabulary recursively. Deferred because: (a) the ad-hoc format works for the current use cases, (b) recursive column modeling is a significant design effort, and (c) it's unclear whether the complexity is justified until there's a use case that needs machine-readable inner schemas (e.g., a validator that checks JSON structure).

### ForeignKey / SameEntity overlap

The same condition_id columns appear in both `mnf:ForeignKey` (directional reference) and `mnf:SameEntity` (symmetric identity) declarations in the Polymarket description. These serve different purposes: FK declares referential integrity expectations, while SameEntity declares joinability. But in practice most FKs also participate in SameEntity. Deferred because: removing either would lose information, and making SameEntity inferrable from FK cycles would require SPARQL-level reasoning that isn't needed yet.

### SameEntity naming

`mnf:SameEntity` could be confused with OWL's `owl:sameAs`. `mnf:SharedIdentifier` or `mnf:EntityIdentityMapping` would be clearer. Deferred because renaming is cosmetic and the existing name is unambiguous in context (it operates on columns, not instances).

### Verbosity / compact shorthand

~7 lines of boilerplate per column makes 100-column datasets unwieldy in Turtle. A tabular shorthand (CSV or YAML) that compiles to Turtle would help adoption. Deferred because: the canonical format should stay RDF, and a compiler is a separate tool, not a vocabulary change.

### Constraint combinator coverage

The constraint algebra (ForEach, Paired, Ordered, Grouped, Conditional, And, Or) is well-designed but only Grouped + Ordered are exercised in either description. The others are aspirational. Not a vocabulary problem — they're available for future use — but worth noting that they're untested.
