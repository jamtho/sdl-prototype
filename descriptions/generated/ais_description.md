# AIS Dataset Description

*Generated from `ais_description.ttl` — do not edit.*

## Datasets

| Dataset | Row Semantics | Schema | Partitioning | Format |
|---------|---------------|--------|--------------|--------|
| AIS Daily Broadcast Positions | mnf:EventRow | mnf:FixedSchema | daily | Parquet |
| AIS Daily Vessel Index | mnf:AggregateRow | mnf:FixedSchema | daily | Parquet |

---

## AIS Daily Broadcast Positions

**URI:** `ais:DailyBroadcasts`
  
One Parquet file per day containing preprocessed AIS vessel position reports from NOAA Marine Cadastre. Denormalized: includes static vessel data (name, IMO, dimensions) merged with position reports. Ordered by MMSI then timestamp within each file.
  
**Row semantics:** mnf:EventRow
  
**Schema:** mnf:FixedSchema
  
**Path template:** `broadcasts/{year}/ais-{date}.parquet`

### Columns

| Name | Physical Type | Semantic Type | Nullable |
|------|---------------|---------------|----------|
| `base_date_time` | mnf:Varchar | ais:AISRawTimestampString | yes |
| `call_sign` | mnf:Varchar | ais:CallSign | yes |
| `cargo` | mnf:Integer | ais:CargoTypeCode | yes |
| `cog` | mnf:Double | ais:CourseOverGround | yes |
| `date` | mnf:Date | ais:PartitionDate | yes |
| `draft` | mnf:Double | ais:VesselDraft | yes |
| `geometry` | mnf:Blob | ais:WKBPoint | yes |
| `h3_res15` | mnf:UBigInt | ais:H3Resolution15 | yes |
| `heading` | mnf:Double | ais:TrueHeading | yes |
| `imo` | mnf:Varchar | ais:IMONumber | yes |
| `latitude` | mnf:Double | ais:WGS84Latitude | yes |
| `length` | mnf:Double | ais:VesselLength | yes |
| `longitude` | mnf:Double | ais:WGS84Longitude | yes |
| `mmsi` | mnf:Integer | ais:MMSI | yes |
| `sog` | mnf:Double | ais:SpeedOverGround | yes |
| `status` | mnf:Integer | ais:NavigationalStatus | yes |
| `timestamp` | mnf:TimestampTZ | ais:AISTimestamp | yes |
| `transceiver` | mnf:Varchar | ais:TransceiverClass | yes |
| `vessel_name` | mnf:Varchar | ais:VesselName | yes |
| `vessel_type` | mnf:Integer | ais:VesselTypeCode | yes |
| `width` | mnf:Double | ais:VesselWidth | yes |

### Ordering

| # | Column | Direction | Semantic |
|---|--------|-----------|----------|
| 1 | `mmsi` | ascending | mnf:ClusteringForIndex |
| 2 | `timestamp` | ascending | mnf:MeaningfulSequence |

### Derivations

| Derived Column | Source Columns | Function | Properties |
|----------------|----------------|----------|------------|
| `timestamp` | `base_date_time` | ais:ParseTimestamp | mnf:Deterministic, mnf:Invertible |
| `geometry` | `latitude`, `longitude` | ais:PointFromWGS84 | mnf:Deterministic, mnf:Invertible |
| `h3_res15` | `latitude`, `longitude` | ais:H3IndexFromWGS84Res15 | mnf:Deterministic, mnf:Lossy |

### Known Deficiencies

| Severity | Description |
|----------|-------------|
| moderate | Temporal gaps exist within vessel trajectories due to NOAA's undocumented downsampling. Trajectory-based analyses (distance, speed) may be inaccurate for affected segments. |
| minor | Static vessel data is denormalized into position rows. A vessel's name/IMO/dimensions may appear differently across rows due to broadcast timing and the merge process. |
| moderate | MMSI does not reliably identify a single vessel. Known issues: MMSI reuse between vessels, multiple vessels sharing an MMSI simultaneously, default/test MMSIs, and spoofing. |

---

## AIS Daily Vessel Index

**URI:** `ais:DailyIndex`
  
One Parquet file per day, one row per MMSI observed that day. Summarises the broadcast data for quick vessel-level queries across the full time range.
  
**Row semantics:** mnf:AggregateRow
  
**Schema:** mnf:FixedSchema
  
**Path template:** `broadcasts/{year}/ais-{date}.parquet`

### Columns

| Name | Physical Type | Semantic Type | Nullable |
|------|---------------|---------------|----------|
| `call_signs` | mnf:VarcharList |  | yes |
| `cargos` | mnf:IntegerList |  | yes |
| `centroid_lat` | mnf:Double | ais:WGS84Latitude | yes |
| `centroid_lon` | mnf:Double | ais:WGS84Longitude | yes |
| `date` | mnf:Date | ais:PartitionDate | yes |
| `distance_m` | mnf:Double | ais:DistanceMetres | yes |
| `drafts` | mnf:DoubleList |  | yes |
| `duration_s` | mnf:Double | ais:DurationSeconds | yes |
| `first_timestamp` | mnf:TimestampTZ | ais:AISTimestamp | yes |
| `h3_cell_count` | mnf:BigInt |  | yes |
| `imos` | mnf:VarcharList |  | yes |
| `last_timestamp` | mnf:TimestampTZ | ais:AISTimestamp | yes |
| `lengths` | mnf:DoubleList |  | yes |
| `max_inter_msg_speed_ms` | mnf:Double | ais:SpeedMetresPerSecond | yes |
| `max_lat` | mnf:Double | ais:WGS84Latitude | yes |
| `max_lon` | mnf:Double | ais:WGS84Longitude | yes |
| `message_count` | mnf:BigInt | ais:MessageCount | yes |
| `min_lat` | mnf:Double | ais:WGS84Latitude | yes |
| `min_lon` | mnf:Double | ais:WGS84Longitude | yes |
| `mmsi` | mnf:Integer | ais:MMSI | yes |
| `sog_max` | mnf:Double | ais:SpeedOverGround | yes |
| `sog_mean` | mnf:Double | ais:SpeedOverGround | yes |
| `sog_min` | mnf:Double | ais:SpeedOverGround | yes |
| `status_codes` | mnf:IntegerList |  | yes |
| `transceiver_classes` | mnf:VarcharList |  | yes |
| `vessel_names` | mnf:VarcharList |  | yes |
| `vessel_types` | mnf:IntegerList |  | yes |
| `widths` | mnf:DoubleList |  | yes |

---

## Semantic Types Reference

| Type | Label | Physical Type | Range | Unit | Description |
|------|-------|---------------|-------|------|-------------|
| ais:AISRawTimestampString | Raw AIS Timestamp String | mnf:Varchar |  |  | Original timestamp string from the NOAA CSV before parsing. Retained for traceability. |
| ais:AISTimestamp | AIS Broadcast Timestamp | mnf:TimestampTZ |  |  | Timestamp of the AIS broadcast, with timezone (UTC). |
| ais:CallSign | Radio Call Sign | mnf:Varchar |  |  |  |
| ais:CargoTypeCode | AIS Cargo Type Code | mnf:Integer |  |  |  |
| ais:CourseOverGround | Course Over Ground | mnf:Double | 0.0–<360.0 | degrees | Relative to true north. 3600 (36.0 scaled) = not available. |
| ais:DistanceMetres | Distance in Metres | mnf:Double | 0.0 | metres |  |
| ais:DurationSeconds | Duration in Seconds | mnf:Double | 0.0 | seconds |  |
| ais:H3Resolution15 | H3 Cell Index at Resolution 15 | mnf:UBigInt |  |  | ~0.9 m² cell area. Finest H3 resolution. |
| ais:IMONumber | IMO Ship Identification Number | mnf:Varchar |  |  | Seven-digit number permanently assigned to a vessel. More reliable than MMSI for identity, but not always present in AIS data. String because leading 'IMO' prefix is sometimes included. |
| ais:MMSI | Maritime Mobile Service Identity | mnf:Integer | 100000000.0–799999999.0 |  | Nine-digit vessel identifier assigned by flag state. In practice: not unique to a vessel (vessels change MMSI, multiple vessels sometimes share one, some are garbage). Treat as 'mostly identifies a vessel, with known failure modes'. |
| ais:MessageCount | Count of AIS Messages | mnf:BigInt | 1.0 |  | Must be >= 1 since the group would not exist otherwise. |
| ais:NavigationalStatus | AIS Navigational Status | mnf:Integer | 0.0–15.0 |  | 0=under way using engine, 1=at anchor, 2=not under command, 3=restricted maneuverability, 5=moored, 7=fishing, 8=under sail, 15=default/not defined. Per ITU-R M.1371. |
| ais:PartitionDate | Partition Date | mnf:Date |  |  | Date value constant within each file, matching the file's partition. Embedded as a column for query convenience. |
| ais:SpeedMetresPerSecond | Speed in Metres per Second | mnf:Double | 0.0 | m/s |  |
| ais:SpeedOverGround | Speed Over Ground | mnf:Double | 0.0–102.2 | knots | AIS SOG: 0.0-102.2 knots in 0.1 knot steps. Value 102.3 means >=102.2. Null or NaN means not available. |
| ais:TransceiverClass | AIS Transceiver Class | mnf:Varchar |  |  | E.g. 'A', 'B', 'A-S'. |
| ais:TrueHeading | True Heading | mnf:Double | 0.0–<360.0 | degrees | 511 means not available in raw AIS; may appear as NaN here. |
| ais:VesselDraft | Vessel Static Draft | mnf:Double | 0.0–25.5 | metres | Maximum draught. 0 = not available in raw AIS. |
| ais:VesselLength | Vessel Length | mnf:Double |  | metres |  |
| ais:VesselName | Vessel Name | mnf:Varchar |  |  | As broadcast by AIS. May contain trailing spaces, be truncated, or vary between broadcasts. |
| ais:VesselTypeCode | AIS Vessel Type Code | mnf:Integer | 0.0–99.0 |  | Vessel type as per ITU-R M.1371. Values 0-99. Grouped: 30-39 fishing, 40-49 HSC, 60-69 passenger, 70-79 cargo, 80-89 tanker, etc. |
| ais:VesselWidth | Vessel Width (Beam) | mnf:Double |  | metres |  |
| ais:WGS84Latitude | WGS84 Latitude | mnf:Double | -90.0–90.0 | degrees |  |
| ais:WGS84Longitude | WGS84 Longitude | mnf:Double | -180.0–180.0 | degrees |  |
| ais:WKBPoint | Well-Known Binary Point Geometry | mnf:Blob |  |  | WKB-encoded Point geometry. CRS: WGS84 / EPSG:4326. |

## Cross-Dataset Relationships

### Aggregation

**ais:DailyBroadcasts** → **ais:DailyIndex** (grouped by `mmsi`)

| Target Column | Source Column(s) | Function |
|---------------|------------------|----------|
| `message_count` | `mmsi` | COUNT |
| `first_timestamp` | `timestamp` | MIN |
| `last_timestamp` | `timestamp` | MAX |
| `vessel_names` | `vessel_name` | LIST of DISTINCT values |
| `imos` | `imo` | LIST of DISTINCT values |
| `call_signs` | `call_sign` | LIST of DISTINCT values |
| `vessel_types` | `vessel_type` | LIST of DISTINCT values |
| `cargos` | `cargo` | LIST of DISTINCT values |
| `lengths` | `length` | LIST of DISTINCT values |
| `widths` | `width` | LIST of DISTINCT values |
| `drafts` | `draft` | LIST of DISTINCT values |
| `transceiver_classes` | `transceiver` | LIST of DISTINCT values |
| `status_codes` | `status` | LIST of DISTINCT values |
| `min_lat` | `latitude` | MIN |
| `max_lat` | `latitude` | MAX |
| `min_lon` | `longitude` | MIN |
| `max_lon` | `longitude` | MAX |
| `centroid_lat` | `latitude` | MEAN / AVG |
| `centroid_lon` | `longitude` | MEAN / AVG |
| `sog_min` | `sog` | MIN |
| `sog_max` | `sog` | MAX |
| `sog_mean` | `sog` | MEAN / AVG |
| `h3_cell_count` | `h3_res15` | COUNT DISTINCT |
| `duration_s` | `timestamp` | Duration between min and max timestamps |
| `distance_m` | `latitude`, `longitude` | Haversine distance from first to last position |
| `max_inter_msg_speed_ms` | `latitude`, `longitude`, `timestamp` | Maximum implied speed between consecutive messages |

---

## Notes for AI Agents

This section explains Manifest concepts used in the tables above, to help you write correct queries against this data.

**Row semantics** determine how to interpret rows:

- **Event rows** (`mnf:EventRow`) — each row is an independent event or observation. No deduplication needed.
- **Aggregate rows** (`mnf:AggregateRow`) — each row summarises a group of source rows. Check the Aggregation table for how columns relate to the source dataset.

**Schema stability** affects query robustness:

- **Fixed** (`mnf:FixedSchema`) — all files have identical columns and types. Query without defensive casting.

**Row ordering** — files with declared ordering are physically sorted by the listed keys. DuckDB can exploit this for merge joins and ordered aggregations. The semantic column distinguishes keys that carry meaning (e.g. a time series) from keys used purely for index clustering.

**Aggregations** — the target dataset's columns are computed from the source dataset. Don't recompute what already exists in the aggregate table. The Function column shows exactly how each target column is derived.

**Known deficiencies** — documented data quality issues that may affect query correctness. Read these before writing queries that involve aggregation, deduplication, or cross-file joins.

**Notation** — `mnf:` prefixed terms are Manifest vocabulary concepts. Domain-specific prefixes (e.g. `ais:`, `pm:`) identify semantic types and domain entities. Physical types like `mnf:Varchar`, `mnf:Double`, `mnf:Integer` map directly to DuckDB/Parquet types.

