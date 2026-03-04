# SDL Vocabulary Review: Findings, Actions, and Deferred Items

*2026-03-04 (2 of 2)*

A fresh-eyes review of the SDL vocabulary design, conducted after the core vocabulary and both domain descriptions (AIS, Polymarket) were complete.

## What's strong

**Architecture.** The three-layer separation (vocabulary / description / validation) is correct. Most metadata systems conflate at least two of these.

**Combinators over opaque leaves.** The constraint algebra (ForEach, Grouped, Ordered, Conditional, And, Or) is the right abstraction. Domain semantics stay extensible at the leaves while the system reasons about structure.

**Computational profile.** Ordering validators by cost (schema-check -> per-value -> full-scan -> sequential-scan -> external) is practical and well-designed. Rare to see this made first-class.

**Known deficiencies.** Every schema system describes what data *should* be. Almost none describe what it *isn't*. The link from deficiency -> violated invariant -> constraint is genuinely useful for safe data integration.

**Two-domain validation.** Testing the vocabulary against a second, fundamentally different domain (Polymarket) was exactly the right strategy. The vocabulary-evolution doc is honest about the gaps this surfaced.

---

## Actions taken

### 1. String literals replaced with named individuals

**Problem.** The vocabulary defined `sdl:AllowedValues` for domain enum constraints, but used freeform string literals for its own structural enumerations. This meant no typo detection, no SPARQL queryability, and no `rdfs:comment` on individual values.

**Fix.** Introduced named individual classes and instances for seven properties:

| Property | Old range | New range | Individuals |
|----------|-----------|-----------|-------------|
| `sdl:keyDirection` | `xsd:string` | `sdl:SortDirection` | `sdl:Ascending`, `sdl:Descending` |
| `sdl:fileFormat` | `xsd:string` | `sdl:FileFormat` | `sdl:Parquet`, `sdl:CSV`, `sdl:ORC` |
| `sdl:partitionGranularity` | `xsd:string` | `sdl:TemporalGranularity` | `sdl:Daily`, `sdl:Hourly`, `sdl:Monthly`, `sdl:ByValue` |
| `sdl:levelGranularity` | `xsd:string` | `sdl:TemporalGranularity` | (shares the above) |
| `sdl:severity` | `xsd:string` | `sdl:SeverityLevel` | `sdl:Minor`, `sdl:Moderate`, `sdl:Severe` |
| `sdl:embeddedFormat` | `xsd:string` | `sdl:DataEncodingFormat` | `sdl:JSONEncoding`, `sdl:CSVEncoding` |
| `sdl:verificationResult` | `xsd:string` | `sdl:VerificationResultValue` | `sdl:Pass`, `sdl:Fail`, `sdl:Partial`, `sdl:Error` |
| `sdl:referentialIntegrity` | `xsd:string` | `sdl:ReferentialIntegrityLevel` | `sdl:StrictIntegrity`, `sdl:EventualIntegrity`, `sdl:PartialIntegrity` |

Each named individual carries an `rdfs:label` matching the old string value (e.g. `sdl:Ascending rdfs:label "ascending"`), so the Python API returns the same strings via a new `_label_or_str()` helper. Downstream code (validators, CLI) is unaffected.

### 2. Consistent `rdfs:Class` declarations

**Problem.** Some subclasses were properly declared (`sdl:ForEach a rdfs:Class ; rdfs:subClassOf sdl:Constraint`) while others omitted the `a rdfs:Class` triple (`sdl:ScalarConstraint rdfs:subClassOf sdl:Constraint`).

**Fix.** Added `a rdfs:Class` to all subclass declarations: `ScalarConstraint`, `PairConstraint`, `SequenceConstraint`, `WindowedSequenceConstraint`, `DatasetConstraint`, `GroupedConstraint`, `CompositePartitionScheme`, `PythonValidator`, `SPARQLValidator`, `DuckDBValidator`.

### 3. Added `sdl:Boolean` and `sdl:Float` physical types

**Problem.** The physical type vocabulary had no Boolean (forcing Polymarket to use `pm:BooleanString` with `sdl:Varchar`) and no 32-bit float (only `sdl:Double`).

**Fix.** Added `sdl:Boolean` (label "BOOLEAN") and `sdl:Float` (label "FLOAT"). Added `sdl:Float sdl:narrowerThan sdl:Double` to the type compatibility chain. Updated the Python schema validator's Arrow type mapping to include `bool` -> `sdl:Boolean` and `float32` -> `sdl:Float`.

### 4. Added `sdl:rowSemantics` and `sdl:snapshotTimestamp`

**Problem.** The vocabulary had `sdl:entityKey` for snapshot semantics but no general way to declare what a row represents (event vs. snapshot vs. aggregate), and no way to declare which column is the temporal dimension for snapshot datasets.

**Fix.** Added:
- `sdl:rowSemantics` (domain `sdl:Dataset`, range `sdl:RowSemanticsType`)
- `sdl:RowSemanticsType` class with `sdl:EventRow`, `sdl:SnapshotRow`, `sdl:AggregateRow`
- `sdl:snapshotTimestamp` (domain `sdl:Dataset`, range `sdl:Column`)

Updated descriptions:
- AIS `DailyBroadcasts` -> `sdl:EventRow`
- AIS `DailyIndex` -> `sdl:AggregateRow`
- Polymarket snapshot datasets -> `sdl:SnapshotRow` + `sdl:snapshotTimestamp` pointing to `_fetched_at`
- Polymarket `Trades` -> `sdl:EventRow`

### 5. Added `rdfs:domain` to constraint target properties

**Problem.** `sdl:appliesToDataset`, `sdl:appliesToColumn`, and `sdl:appliesToColumnGroup` had ranges declared but no domain, making them unmoored from the `sdl:Constraint` class.

**Fix.** Added `rdfs:domain sdl:Constraint` to all three.

### 6. Removed unused terms

- Removed `owl:` prefix (was imported but never used)
- Removed `sdl:ConstraintSignature` class (declared but never referenced)
- Updated section 2 header comment to say "DuckDB conventions" instead of "Parquet logical types"
- Added design principle 4 to the header: "Named individuals over string literals"

### 7. Updated both domain descriptions

All string literal usages in `ais_description.ttl` and `polymarket_description.ttl` updated to reference the new named individuals. Both descriptions also gained `sdl:rowSemantics` and `sdl:schemaStability` declarations where missing.

### 8. Python code updated for compatibility

- `graph.py`: Added `_label_or_str()` helper that resolves `rdfs:label` from named individuals, so downstream code continues to receive clean strings like `"ascending"` rather than `"sdl:Ascending"`.
- `model.py`: `Attestation.to_turtle()` now emits `sdl:verificationResult sdl:Pass` instead of `sdl:verificationResult "pass"`.
- `validators/schema.py`: Added `sdl:Boolean` and `sdl:Float` to the Arrow type mapping.

---

## Deferred items (not taken, with rationale)

### `sdl:levelColumn` string vs `sdl:Column` URI mismatch

`sdl:partitionColumn` points to a `sdl:Column` URI, but `sdl:levelColumn` is a plain string. This exists because Hive partition keys (like `dt`, `hour`) may not correspond to data columns — they're extracted from directory paths. Fixing this requires deciding whether to create phantom Column nodes for path-only keys, or to add a parallel `sdl:levelDataColumn` property. Both options add complexity for a currently-working pattern. Deferred until a third domain exercises this.

### `sdl:embeddedElementType` recursive modeling

The inner structure of embedded JSON is described as a free-text string (`"array<{price: string, size: string}>"`). This is essentially an ad-hoc schema language inside a string literal — the very problem SDL exists to solve. A proper fix would use SDL's own Column/PhysicalType vocabulary recursively. Deferred because: (a) the ad-hoc format works for the current use cases, (b) recursive column modeling is a significant design effort, and (c) it's unclear whether the complexity is justified until there's a use case that needs machine-readable inner schemas (e.g., a validator that checks JSON structure).

### ForeignKey / SameEntity overlap

The same condition_id columns appear in both `sdl:ForeignKey` (directional reference) and `sdl:SameEntity` (symmetric identity) declarations in the Polymarket description. These serve different purposes: FK declares referential integrity expectations, while SameEntity declares joinability. But in practice most FKs also participate in SameEntity. Deferred because: removing either would lose information, and making SameEntity inferrable from FK cycles would require SPARQL-level reasoning that isn't needed yet.

### SameEntity naming

`sdl:SameEntity` could be confused with OWL's `owl:sameAs`. `sdl:SharedIdentifier` or `sdl:EntityIdentityMapping` would be clearer. Deferred because renaming is cosmetic and the existing name is unambiguous in context (it operates on columns, not instances).

### Verbosity / compact shorthand

~7 lines of boilerplate per column makes 100-column datasets unwieldy in Turtle. A tabular shorthand (CSV or YAML) that compiles to Turtle would help adoption. Deferred because: the canonical format should stay RDF, and a compiler is a separate tool, not a vocabulary change.

### Constraint combinator coverage

The constraint algebra (ForEach, Paired, Ordered, Grouped, Conditional, And, Or) is well-designed but only Grouped + Ordered are exercised in either description. The others are aspirational. Not a vocabulary problem — they're available for future use — but worth noting that they're untested.
