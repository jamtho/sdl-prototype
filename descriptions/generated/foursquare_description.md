# Foursquare Dataset Description

*Generated from `foursquare_description.ttl` — do not edit.*

## Datasets

| Dataset | Row Semantics | Schema | Partitioning | Format |
|---------|---------------|--------|--------------|--------|
| Foursquare Open Places | mnf:SnapshotRow | mnf:FixedSchema | — | Parquet |
| Foursquare Categories | mnf:SnapshotRow | mnf:FixedSchema | — | Parquet |

---

## Foursquare Open Places

**URI:** `fsq:Places`
  
Periodic release of ~105M points of interest worldwide. Data is sharded across 100 Parquet files for size management — there is no hive partitioning or semantic meaning to the shard assignment. Each release is a full snapshot; the same place appears across releases identified by fsq_place_id.
  
**Row semantics:** mnf:SnapshotRow
  
**Schema:** mnf:FixedSchema
  
**Path template:** `places/places-{shard}.zstd.parquet`
  
**Entity key:** `fsq_place_id`

### Columns

| Name | Physical Type | Semantic Type | Nullable |
|------|---------------|---------------|----------|
| `address` | mnf:Varchar |  | yes |
| `admin_region` | mnf:Varchar |  | yes |
| `bbox` | mnf:Struct |  | yes |
| `country` | mnf:Varchar | fsq:ISOCountryCode | yes |
| `date_closed` | mnf:Varchar | fsq:DateString | yes |
| `date_created` | mnf:Varchar | fsq:DateString | yes |
| `date_refreshed` | mnf:Varchar | fsq:DateString | yes |
| `email` | mnf:Varchar |  | yes |
| `facebook_id` | mnf:BigInt |  | yes |
| `fsq_category_ids` | mnf:VarcharList | fsq:CategoryIDList | yes |
| `fsq_category_labels` | mnf:VarcharList | fsq:CategoryLabelList | yes |
| `fsq_place_id` | mnf:Varchar | fsq:FoursquarePlaceID | no |
| `geom` | mnf:Blob | fsq:WKBGeometry | yes |
| `instagram` | mnf:Varchar |  | yes |
| `latitude` | mnf:Double | fsq:WGS84Latitude | yes |
| `locality` | mnf:Varchar |  | yes |
| `longitude` | mnf:Double | fsq:WGS84Longitude | yes |
| `name` | mnf:Varchar |  | yes |
| `placemaker_url` | mnf:Varchar |  | yes |
| `po_box` | mnf:Varchar |  | yes |
| `post_town` | mnf:Varchar |  | yes |
| `postcode` | mnf:Varchar |  | yes |
| `region` | mnf:Varchar |  | yes |
| `tel` | mnf:Varchar |  | yes |
| `twitter` | mnf:Varchar |  | yes |
| `unresolved_flags` | mnf:VarcharList | fsq:QualityFlag | yes |
| `website` | mnf:Varchar |  | yes |

### Known Deficiencies

| Severity | Description |
|----------|-------------|
| moderate | Date fields (date_created, date_refreshed, date_closed) reflect database events, not real-world events. date_created is when the place entered the Foursquare database, not when the venue opened. date_closed is when it was flagged closed, not when it actually ceased operations. |
| minor | Region formatting is inconsistent across countries. US, Canada, Australia, and Brazil use abbreviated state/province codes (e.g. 'CA', 'ON', 'NSW'). All other countries use full region names. |
| minor | The bbox and unresolved_flags columns are mostly NULL across the dataset. bbox is only populated for places with area geometry rather than point geometry. |
| minor | facebook_id is stored as BIGINT in the Parquet files, but Foursquare's documentation describes it as String. The actual data contains integer values that fit in BIGINT. |

---

## Foursquare Categories

**URI:** `fsq:Categories`
  
Category taxonomy with 1,245 entries across up to 6 hierarchy levels. Reference/lookup table for the fsq_category_ids column in the Places dataset. Denormalized: each row includes its full ancestry via level1–level6 columns.
  
**Row semantics:** mnf:SnapshotRow
  
**Schema:** mnf:FixedSchema
  
**Path template:** `categories/categories.zstd.parquet`
  
**Entity key:** `category_id`

### Columns

| Name | Physical Type | Semantic Type | Nullable |
|------|---------------|---------------|----------|
| `category_id` | mnf:Varchar | fsq:CategoryID | no |
| `category_label` | mnf:Varchar |  | no |
| `category_level` | mnf:Integer | fsq:CategoryLevel | no |
| `category_name` | mnf:Varchar |  | no |
| `level1_category_id` | mnf:Varchar | fsq:CategoryID | yes |
| `level1_category_name` | mnf:Varchar |  | yes |
| `level2_category_id` | mnf:Varchar | fsq:CategoryID | yes |
| `level2_category_name` | mnf:Varchar |  | yes |
| `level3_category_id` | mnf:Varchar | fsq:CategoryID | yes |
| `level3_category_name` | mnf:Varchar |  | yes |
| `level4_category_id` | mnf:Varchar | fsq:CategoryID | yes |
| `level4_category_name` | mnf:Varchar |  | yes |
| `level5_category_id` | mnf:Varchar | fsq:CategoryID | yes |
| `level5_category_name` | mnf:Varchar |  | yes |
| `level6_category_id` | mnf:Varchar | fsq:CategoryID | yes |
| `level6_category_name` | mnf:Varchar |  | yes |

---

## Semantic Types Reference

| Type | Label | Physical Type | Range | Unit | Description |
|------|-------|---------------|-------|------|-------------|
| fsq:CategoryID | Foursquare Category ID | mnf:Varchar |  |  | BSON ObjectId identifying a category in the taxonomy. |
| fsq:CategoryIDList | Category ID List | mnf:VarcharList |  |  | List of Foursquare category IDs assigned to a place. Each element is a BSON ObjectId referencing the Categories dataset. |
| fsq:CategoryLabelList | Category Label List | mnf:VarcharList |  |  | List of hierarchical category breadcrumbs. Each label uses ' > ' as separator (e.g. 'Dining > Restaurant > Italian'). |
| fsq:CategoryLevel | Category Hierarchy Level | mnf:Integer | 1.0–6.0 |  | Depth in the category taxonomy, 1 being the broadest. |
| fsq:DateString | Date String | mnf:Varchar |  |  | YYYY-MM-DD formatted date. Reflects database events (creation, refresh, closure timestamps) not real-world opening/closing dates. |
| fsq:FoursquarePlaceID | Foursquare Place ID | mnf:Varchar |  |  | 24-character hexadecimal BSON ObjectId uniquely identifying a place in the Foursquare database. |
| fsq:ISOCountryCode | ISO Country Code | mnf:Varchar |  |  | 2-letter ISO 3166-1 alpha-2 country code. |
| fsq:QualityFlag | Quality / Status Flag | mnf:VarcharList |  |  | Quality or status flag for a place. Values indicate issues detected by Foursquare or community moderation. |
| fsq:WGS84Latitude | WGS84 Latitude | mnf:Double | -90.0–90.0 | degrees | WGS84 latitude of the place. Foursquare uses front-door placement where possible, not building centroid. |
| fsq:WGS84Longitude | WGS84 Longitude | mnf:Double | -180.0–180.0 | degrees | WGS84 longitude of the place. Foursquare uses front-door placement where possible, not building centroid. |
| fsq:WKBGeometry | Well-Known Binary Geometry | mnf:Blob |  |  | WKB-encoded point geometry. CRS: WGS84 / EPSG:4326. |

## Cross-Dataset Relationships

### Foreign Keys

| Relationship | From (Dataset.Column) | To (Dataset.Column) | Integrity |
|-------------|----------------------|---------------------|-----------|
| Places -> Categories (via fsq_category_ids) | Foursquare Open Places.`fsq_category_ids` | Foursquare Categories.`category_id` | mnf:StrictIntegrity |

---

## Notes for AI Agents

This section explains Manifest concepts used in the tables above, to help you write correct queries against this data.

**Row semantics** determine how to interpret rows:

- **Snapshot rows** (`mnf:SnapshotRow`) — each row is a point-in-time observation of a recurring entity. The same entity appears multiple times. To get the latest state, deduplicate by entity key ordered by `_fetched_at` descending.

**Entity key** — the column that identifies which entity a snapshot row describes. Multiple rows with the same entity key are repeated observations over time, not distinct entities. Use `ROW_NUMBER() OVER (PARTITION BY {entity_key} ORDER BY _fetched_at DESC)` to select the most recent observation per entity within a file.

**Schema stability** affects query robustness:

- **Fixed** (`mnf:FixedSchema`) — all files have identical columns and types. Query without defensive casting.

**Foreign keys** — the From and To columns are joinable across datasets, even when column names differ. Check the Integrity column: `mnf:PartialIntegrity` means some values may not resolve in the target (use LEFT JOIN rather than INNER JOIN if you need all rows).

**Known deficiencies** — documented data quality issues that may affect query correctness. Read these before writing queries that involve aggregation, deduplication, or cross-file joins.

**Notation** — `mnf:` prefixed terms are Manifest vocabulary concepts. Domain-specific prefixes (e.g. `ais:`, `pm:`) identify semantic types and domain entities. Physical types like `mnf:Varchar`, `mnf:Double`, `mnf:Integer` map directly to DuckDB/Parquet types.

