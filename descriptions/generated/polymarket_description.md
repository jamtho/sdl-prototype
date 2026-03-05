# Polymarket Dataset Description

*Generated from `polymarket_description.ttl` — do not edit.*

## Datasets

| Dataset | Row Semantics | Schema | Partitioning | Format |
|---------|---------------|--------|--------------|--------|
| Gamma Market Snapshots | mnf:SnapshotRow | mnf:InferredSchema | daily + hourly (dt, hour) | Parquet |
| Gamma Event Snapshots | mnf:SnapshotRow | mnf:InferredSchema | daily + hourly (dt, hour) | Parquet |
| CLOB Price Snapshots | mnf:SnapshotRow | mnf:InferredSchema | daily + hourly (dt, hour) | Parquet |
| CLOB Orderbook Snapshots | mnf:SnapshotRow | mnf:InferredSchema | daily + hourly (dt, hour) | Parquet |
| Trade Events | mnf:EventRow | mnf:InferredSchema | daily + hourly (dt, hour) | Parquet |
| Token Holder Snapshots | mnf:SnapshotRow | mnf:InferredSchema | daily + hourly (dt, hour) | Parquet |
| Gamma Tags | — | — | daily + hourly (dt, hour) | Parquet |
| Gamma Series | — | — | daily + hourly (dt, hour) | Parquet |
| Gamma Sports | — | — | daily + hourly (dt, hour) | Parquet |

---

## Gamma Market Snapshots

**URI:** `pm:MarketSnapshots`
  
Hourly snapshots of all active Polymarket markets from the Gamma API. ~33,500 markets per snapshot, polled every 5 minutes, compacted hourly. Richest schema (~30+ columns).
  
**Row semantics:** mnf:SnapshotRow
  
**Schema:** mnf:InferredSchema
  
**Path template:** `data/parquet/{stream}/dt={date}/hour={hour}.parquet`
  
**Entity key:** `id`

### Columns

| Name | Physical Type | Semantic Type | Nullable |
|------|---------------|---------------|----------|
| `_fetched_at` | mnf:Double | pm:FetchTimestamp | no |
| `_source` | mnf:Varchar | pm:DataSourceLabel | no |
| `active` | mnf:Varchar |  | yes |
| `bestAsk` | mnf:Double | pm:Probability | yes |
| `bestBid` | mnf:Double | pm:Probability | yes |
| `category` | mnf:Varchar | pm:MarketCategory | yes |
| `clobTokenIds` | mnf:Varchar | pm:JSONArray | yes |
| `closed` | mnf:Varchar |  | yes |
| `competitive` | mnf:Double | pm:CompetitivenessScore | yes |
| `conditionId` | mnf:Varchar | pm:ConditionId | yes |
| `createdAt` | mnf:Varchar | pm:ISOTimestamp | yes |
| `description` | mnf:Varchar |  | yes |
| `enableOrderBook` | mnf:Varchar |  | yes |
| `endDate` | mnf:Varchar | pm:ISOTimestamp | yes |
| `id` | mnf:Varchar | pm:MarketId | no |
| `image` | mnf:Varchar |  | yes |
| `lastTradePrice` | mnf:Double | pm:Probability | yes |
| `liquidity` | mnf:Varchar |  | yes |
| `liquidityNum` | mnf:Double | pm:USDAmount | yes |
| `negRisk` | mnf:Varchar |  | yes |
| `oneDayPriceChange` | mnf:Double | pm:PriceChange | yes |
| `oneWeekPriceChange` | mnf:Double | pm:PriceChange | yes |
| `outcomePrices` | mnf:Varchar | pm:JSONArray | yes |
| `outcomes` | mnf:Varchar | pm:JSONArray | yes |
| `question` | mnf:Varchar |  | yes |
| `rewardsMaxSpread` | mnf:Double |  | yes |
| `rewardsMinSize` | mnf:Double |  | yes |
| `slug` | mnf:Varchar | pm:Slug | yes |
| `spread` | mnf:Double | pm:PriceSpread | yes |
| `startDate` | mnf:Varchar | pm:ISOTimestamp | yes |
| `updatedAt` | mnf:Varchar | pm:ISOTimestamp | yes |
| `volume` | mnf:Varchar |  | yes |
| `volume1mo` | mnf:Double | pm:USDAmount | yes |
| `volume1wk` | mnf:Double | pm:USDAmount | yes |
| `volume1yr` | mnf:Double | pm:USDAmount | yes |
| `volume24hr` | mnf:Double | pm:USDAmount | yes |
| `volumeNum` | mnf:Double | pm:USDAmount | yes |

### Derivations

| Derived Column | Source Columns | Function | Properties |
|----------------|----------------|----------|------------|
| `_fetched_at` |  | pm:FetcherTimestampInjection | mnf:Deterministic |
| `_source` |  | pm:FetcherSourceInjection | mnf:Deterministic |
| `spread` | `bestAsk`, `bestBid` | pm:SpreadFromBidAsk | mnf:Deterministic, mnf:Invertible |

### Known Deficiencies

| Severity | Description |
|----------|-------------|
| moderate | Parquet schemas are inferred by Polars from JSON, not declared. The schema.py file in the fetcher defines type hints but they are NOT applied during compaction. Columns may appear or disappear depending on API response changes. Types may vary between hourly files if Polars infers differently from different data batches. Datasets declare mnf:schemaStability mnf:InferredSchema to signal this. |
| moderate | Snapshot datasets (markets, events, prices, holders) contain the same entity polled multiple times per hour. Within a single hourly file, the same market/event/token may appear multiple times with slightly different values. No deduplication is performed by the compactor. |
| minor | Several columns store structured data as JSON strings rather than native Parquet nested types: outcomes, outcomePrices, clobTokenIds (in markets), bids/asks (in books), holders (in holders), markets/tags (in events). This happens because the compactor does not parse these fields into structured columns. |

---

## Gamma Event Snapshots

**URI:** `pm:EventSnapshots`
  
Hourly snapshots of Polymarket events from the Gamma API. ~7,900 events per snapshot. Each event groups one or more related markets.
  
**Row semantics:** mnf:SnapshotRow
  
**Schema:** mnf:InferredSchema
  
**Path template:** `data/parquet/{stream}/dt={date}/hour={hour}.parquet`
  
**Entity key:** `id`

### Columns

| Name | Physical Type | Semantic Type | Nullable |
|------|---------------|---------------|----------|
| `_fetched_at` | mnf:Double | pm:FetchTimestamp | no |
| `_source` | mnf:Varchar | pm:DataSourceLabel | no |
| `active` | mnf:Varchar |  | yes |
| `closed` | mnf:Varchar |  | yes |
| `commentCount` | mnf:Double |  | yes |
| `competitive` | mnf:Double | pm:CompetitivenessScore | yes |
| `description` | mnf:Varchar |  | yes |
| `endDate` | mnf:Varchar | pm:ISOTimestamp | yes |
| `id` | mnf:Varchar | pm:EventId | no |
| `liquidity` | mnf:Double | pm:USDAmount | yes |
| `markets` | mnf:Varchar |  | yes |
| `negRisk` | mnf:Varchar |  | yes |
| `openInterest` | mnf:Double |  | yes |
| `slug` | mnf:Varchar | pm:Slug | yes |
| `startDate` | mnf:Varchar | pm:ISOTimestamp | yes |
| `tags` | mnf:Varchar | pm:JSONArray | yes |
| `title` | mnf:Varchar |  | yes |
| `volume` | mnf:Double | pm:USDAmount | yes |
| `volume24hr` | mnf:Double | pm:USDAmount | yes |

### Known Deficiencies

| Severity | Description |
|----------|-------------|
| moderate | Parquet schemas are inferred by Polars from JSON, not declared. The schema.py file in the fetcher defines type hints but they are NOT applied during compaction. Columns may appear or disappear depending on API response changes. Types may vary between hourly files if Polars infers differently from different data batches. Datasets declare mnf:schemaStability mnf:InferredSchema to signal this. |
| moderate | Snapshot datasets (markets, events, prices, holders) contain the same entity polled multiple times per hour. Within a single hourly file, the same market/event/token may appear multiple times with slightly different values. No deduplication is performed by the compactor. |

---

## CLOB Price Snapshots

**URI:** `pm:PriceSnapshots`
  
Hourly snapshots of CLOB token prices and midpoints. ~2,000 tokens polled every 30 seconds. Merges /price and /midpoint endpoints.
  
**Row semantics:** mnf:SnapshotRow
  
**Schema:** mnf:InferredSchema
  
**Path template:** `data/parquet/{stream}/dt={date}/hour={hour}.parquet`
  
**Entity key:** `token_id`

### Columns

| Name | Physical Type | Semantic Type | Nullable |
|------|---------------|---------------|----------|
| `_fetched_at` | mnf:Double | pm:FetchTimestamp | no |
| `_source` | mnf:Varchar | pm:DataSourceLabel | no |
| `midpoint` | mnf:Varchar |  | yes |
| `price` | mnf:Varchar |  | yes |
| `token_id` | mnf:Varchar | pm:CLOBTokenId | no |

### Known Deficiencies

| Severity | Description |
|----------|-------------|
| moderate | Parquet schemas are inferred by Polars from JSON, not declared. The schema.py file in the fetcher defines type hints but they are NOT applied during compaction. Columns may appear or disappear depending on API response changes. Types may vary between hourly files if Polars infers differently from different data batches. Datasets declare mnf:schemaStability mnf:InferredSchema to signal this. |
| moderate | The 'price' column in clob/prices may contain either a float value (the actual price) or an error object string when the CLOB API returns an error for a specific token. Since the compactor uses ignore_errors=True, these error responses are silently mixed in with valid data. |

---

## CLOB Orderbook Snapshots

**URI:** `pm:OrderbookSnapshots`
  
Hourly snapshots of orderbook state for top 100 active tokens. Polled every 2 minutes.
  
**Row semantics:** mnf:SnapshotRow
  
**Schema:** mnf:InferredSchema
  
**Path template:** `data/parquet/{stream}/dt={date}/hour={hour}.parquet`
  
**Entity key:** `asset_id`

### Columns

| Name | Physical Type | Semantic Type | Nullable |
|------|---------------|---------------|----------|
| `_fetched_at` | mnf:Double | pm:FetchTimestamp | no |
| `_source` | mnf:Varchar | pm:DataSourceLabel | no |
| `asks` | mnf:Varchar | pm:JSONArray | yes |
| `asset_id` | mnf:Varchar | pm:CLOBTokenId | no |
| `bids` | mnf:Varchar | pm:JSONArray | yes |
| `hash` | mnf:Varchar |  | yes |
| `last_trade_price` | mnf:Varchar |  | yes |
| `market` | mnf:Varchar | pm:ConditionId | yes |
| `min_order_size` | mnf:Varchar |  | yes |
| `neg_risk` | mnf:Varchar |  | yes |
| `tick_size` | mnf:Varchar |  | yes |
| `timestamp` | mnf:Varchar |  | yes |

### Known Deficiencies

| Severity | Description |
|----------|-------------|
| moderate | Parquet schemas are inferred by Polars from JSON, not declared. The schema.py file in the fetcher defines type hints but they are NOT applied during compaction. Columns may appear or disappear depending on API response changes. Types may vary between hourly files if Polars infers differently from different data batches. Datasets declare mnf:schemaStability mnf:InferredSchema to signal this. |
| minor | Several columns store structured data as JSON strings rather than native Parquet nested types: outcomes, outcomePrices, clobTokenIds (in markets), bids/asks (in books), holders (in holders), markets/tags (in events). This happens because the compactor does not parse these fields into structured columns. |

---

## Trade Events

**URI:** `pm:Trades`
  
Hourly files of recent trades from the Data API. 100 trades polled every 60 seconds. This is the most event-like dataset — each row represents a distinct trade event, unlike the snapshot datasets. Rows are in API response order (roughly reverse chronological), not meaningfully sorted.
  
**Row semantics:** mnf:EventRow
  
**Schema:** mnf:InferredSchema
  
**Path template:** `data/parquet/{stream}/dt={date}/hour={hour}.parquet`

### Columns

| Name | Physical Type | Semantic Type | Nullable |
|------|---------------|---------------|----------|
| `_fetched_at` | mnf:Double | pm:FetchTimestamp | no |
| `_source` | mnf:Varchar | pm:DataSourceLabel | no |
| `asset` | mnf:Varchar | pm:CLOBTokenId | yes |
| `bio` | mnf:Varchar |  | yes |
| `conditionId` | mnf:Varchar | pm:ConditionId | yes |
| `eventSlug` | mnf:Varchar | pm:Slug | yes |
| `icon` | mnf:Varchar |  | yes |
| `name` | mnf:Varchar |  | yes |
| `outcome` | mnf:Varchar |  | yes |
| `outcomeIndex` | mnf:Double | pm:OutcomeIndex | yes |
| `price` | mnf:Double | pm:Probability | yes |
| `profileImage` | mnf:Varchar |  | yes |
| `proxyWallet` | mnf:Varchar | pm:ProxyWallet | yes |
| `pseudonym` | mnf:Varchar |  | yes |
| `side` | mnf:Varchar | pm:TradeSide | yes |
| `size` | mnf:Double | pm:TradeSize | yes |
| `slug` | mnf:Varchar | pm:Slug | yes |
| `timestamp` | mnf:Double |  | yes |
| `title` | mnf:Varchar |  | yes |
| `transactionHash` | mnf:Varchar | pm:TransactionHash | yes |

### Known Deficiencies

| Severity | Description |
|----------|-------------|
| moderate | Parquet schemas are inferred by Polars from JSON, not declared. The schema.py file in the fetcher defines type hints but they are NOT applied during compaction. Columns may appear or disappear depending on API response changes. Types may vary between hourly files if Polars infers differently from different data batches. Datasets declare mnf:schemaStability mnf:InferredSchema to signal this. |
| moderate | The trades dataset may contain duplicate trades across consecutive polls if the same trade appears in multiple API responses. The fetcher polls the most recent 100 trades every 60 seconds, so overlapping windows produce duplicates. |

---

## Token Holder Snapshots

**URI:** `pm:HolderSnapshots`
  
Hourly snapshots of top 20 holders per token for first 50 known markets. Polled every 10 minutes. Snapshot semantics keyed by (condition_id, token) — composite entity key.
  
**Row semantics:** mnf:SnapshotRow
  
**Schema:** mnf:InferredSchema
  
**Path template:** `data/parquet/{stream}/dt={date}/hour={hour}.parquet`
  
**Entity key:** `condition_id`

### Columns

| Name | Physical Type | Semantic Type | Nullable |
|------|---------------|---------------|----------|
| `_fetched_at` | mnf:Double | pm:FetchTimestamp | no |
| `_source` | mnf:Varchar | pm:DataSourceLabel | no |
| `condition_id` | mnf:Varchar | pm:ConditionId | no |
| `holders` | mnf:Varchar |  | yes |
| `token` | mnf:Varchar | pm:CLOBTokenId | no |

### Derivations

| Derived Column | Source Columns | Function | Properties |
|----------------|----------------|----------|------------|
| `condition_id` |  | pm:FetcherConditionIdEnrichment | mnf:Deterministic |

### Known Deficiencies

| Severity | Description |
|----------|-------------|
| moderate | Parquet schemas are inferred by Polars from JSON, not declared. The schema.py file in the fetcher defines type hints but they are NOT applied during compaction. Columns may appear or disappear depending on API response changes. Types may vary between hourly files if Polars infers differently from different data batches. Datasets declare mnf:schemaStability mnf:InferredSchema to signal this. |
| moderate | Snapshot datasets (markets, events, prices, holders) contain the same entity polled multiple times per hour. Within a single hourly file, the same market/event/token may appear multiple times with slightly different values. No deduplication is performed by the compactor. |

---

## Gamma Tags

**URI:** `pm:Tags`
  
Near-static reference table of tags used to categorize markets. Refreshed daily. Columns: _fetched_at, _source, id, label, slug, publishedAt, createdAt, updatedAt, requiresTranslation.
  
**Path template:** `data/parquet/{stream}/dt={date}/hour={hour}.parquet`

### Columns

| Name | Physical Type | Semantic Type | Nullable |
|------|---------------|---------------|----------|

---

## Gamma Series

**URI:** `pm:Series`
  
Reference table of market series (recurring market groups). ~200 entries, refreshed daily. Columns: _fetched_at, _source, id, title, ticker, slug, seriesType, recurrence, active, closed, volume, volume24hr, liquidity, commentCount.
  
**Path template:** `data/parquet/{stream}/dt={date}/hour={hour}.parquet`

### Columns

| Name | Physical Type | Semantic Type | Nullable |
|------|---------------|---------------|----------|

---

## Gamma Sports

**URI:** `pm:Sports`
  
Reference table of sport categories for sports betting markets. ~100 entries, refreshed daily. Columns: _fetched_at, _source, id, sport, image, resolution, ordering, tags, series.
  
**Path template:** `data/parquet/{stream}/dt={date}/hour={hour}.parquet`

### Columns

| Name | Physical Type | Semantic Type | Nullable |
|------|---------------|---------------|----------|

---

## Semantic Types Reference

| Type | Label | Physical Type | Range | Unit | Description |
|------|-------|---------------|-------|------|-------------|
| pm:CLOBTokenId | CLOB Token ID | mnf:Varchar |  |  | Identifier for a tradable token on Polymarket's CLOB (Central Limit Order Book). Each market outcome has a distinct token ID. Long numeric string. |
| pm:CompetitivenessScore | Market Competitiveness Score | mnf:Double | 0.0–1.0 |  | Score from 0.0 to 1.0 indicating how competitive a market is. |
| pm:ConditionId | On-Chain Condition ID | mnf:Varchar |  |  | Hex-encoded blockchain condition identifier linking a Polymarket market to its on-chain resolution contract. Serves as the primary cross-system join key between gamma/markets, trades, and holders. |
| pm:DataSourceLabel | Data Source Label | mnf:Varchar |  |  | Label identifying which fetcher stream produced this row (e.g. 'gamma/markets', 'clob/prices'). Injected by the fetcher, not from the API. |
| pm:EventId | Polymarket Event ID | mnf:Varchar |  |  | Unique identifier for an event (a grouping of related markets) on Polymarket's Gamma API. |
| pm:FetchTimestamp | Fetch Timestamp | mnf:Double |  |  | Unix epoch float (seconds since 1970-01-01T00:00:00Z) injected by the fetcher at collection time. NOT from the API. Stored as Float64, not TimestampTZ, because the fetcher writes time.time() directly. |
| pm:ISOTimestamp | ISO 8601 Timestamp String | mnf:Varchar |  |  | ISO 8601 formatted timestamp as a string. Used by the Gamma API for dates (startDate, endDate, createdAt, etc.). |
| pm:JSONArray | JSON-Serialized Array | mnf:Varchar |  |  | A column whose physical type is Varchar but whose content is a JSON-encoded array. Examples: outcomes='["Yes","No"]', clobTokenIds='["1234","5678"]', bids/asks orderbook levels. Columns with this type should also declare mnf:embeddedStructure for the inner element type. |
| pm:MarketCategory | Market Category | mnf:Varchar |  |  | Category label for a market (e.g. 'Politics', 'Sports', 'Crypto'). Open-ended but constrained set from the platform. |
| pm:MarketId | Polymarket Market ID | mnf:Varchar |  |  | Unique identifier for a prediction market on Polymarket's Gamma API. Varchar string, typically a short alphanumeric slug. |
| pm:OutcomeIndex | Outcome Index | mnf:Double | 0.0 |  | Zero-based index into a market's outcome array. Typically 0 or 1 for binary Yes/No markets. |
| pm:PriceChange | Price Change | mnf:Double |  |  | Absolute change in price over a time window. Can be negative. |
| pm:PriceSpread | Bid-Ask Spread | mnf:Double | 0.0 |  | Difference between best ask and best bid prices. |
| pm:Probability | Probability | mnf:Double | 0.0–1.0 |  | Price interpreted as a probability. On Polymarket, prices of outcome tokens range from 0.0 to 1.0, representing the market-implied probability of that outcome. |
| pm:ProxyWallet | Proxy Wallet Address | mnf:Varchar |  |  | Ethereum proxy wallet address for a Polymarket trader. |
| pm:Slug | URL Slug | mnf:Varchar |  |  | URL-safe slug used in Polymarket URLs. |
| pm:TradeSide | Trade Side | mnf:Varchar |  |  | Direction of a trade: "BUY" or "SELL". |
| pm:TradeSize | Trade Size | mnf:Double | >0.0 |  | Number of shares in a trade. Stored as Float64 because the compactor infers from JSON (which has no integer type). |
| pm:TransactionHash | Transaction Hash | mnf:Varchar |  |  | On-chain transaction hash for a trade settlement. |
| pm:USDAmount | USD Amount | mnf:Double | 0.0 | USD | Dollar amount. Volume, liquidity, etc. |

## Cross-Dataset Relationships

### Foreign Keys

| Relationship | From (Dataset.Column) | To (Dataset.Column) | Integrity |
|-------------|----------------------|---------------------|-----------|
| Trades → Markets (via conditionId) | Trade Events.`conditionId` | Gamma Market Snapshots.`conditionId` | mnf:PartialIntegrity |
| Trades → Prices (via asset/token_id) | Trade Events.`asset` | CLOB Price Snapshots.`token_id` | mnf:PartialIntegrity |
| Holders → Markets (via condition_id) | Token Holder Snapshots.`condition_id` | Gamma Market Snapshots.`conditionId` | mnf:PartialIntegrity |
| Books → Markets (via market/conditionId) | CLOB Orderbook Snapshots.`market` | Gamma Market Snapshots.`conditionId` | mnf:PartialIntegrity |

### Same Entity

| Identity | Dataset | Column |
|----------|---------|--------|
| Condition ID identifies the same market across datasets | Gamma Market Snapshots | `conditionId` |
| Condition ID identifies the same market across datasets | Trade Events | `conditionId` |
| Condition ID identifies the same market across datasets | Token Holder Snapshots | `condition_id` |
| Condition ID identifies the same market across datasets | CLOB Orderbook Snapshots | `market` |
| CLOB token ID identifies the same token across datasets | CLOB Price Snapshots | `token_id` |
| CLOB token ID identifies the same token across datasets | CLOB Orderbook Snapshots | `asset_id` |
| CLOB token ID identifies the same token across datasets | Trade Events | `asset` |
| CLOB token ID identifies the same token across datasets | Token Holder Snapshots | `token` |

---

## Notes for AI Agents

This section explains Manifest concepts used in the tables above, to help you write correct queries against this data.

**Row semantics** determine how to interpret rows:

- **Event rows** (`mnf:EventRow`) — each row is an independent event or observation. No deduplication needed.
- **Snapshot rows** (`mnf:SnapshotRow`) — each row is a point-in-time observation of a recurring entity. The same entity appears multiple times. To get the latest state, deduplicate by entity key ordered by `_fetched_at` descending.

**Entity key** — the column that identifies which entity a snapshot row describes. Multiple rows with the same entity key are repeated observations over time, not distinct entities. Use `ROW_NUMBER() OVER (PARTITION BY {entity_key} ORDER BY _fetched_at DESC)` to select the most recent observation per entity within a file.

**Schema stability** affects query robustness:

- **Inferred** (`mnf:InferredSchema`) — schema is inferred from data and may vary between files. Use `TRY_CAST` for type safety, handle potentially missing columns, and use `UNION BY NAME` when combining files from different time periods.

**Foreign keys** — the From and To columns are joinable across datasets, even when column names differ. Check the Integrity column: `mnf:PartialIntegrity` means some values may not resolve in the target (use LEFT JOIN rather than INNER JOIN if you need all rows).

**Same entity** — these columns across different datasets refer to the same real-world entity and are joinable. Unlike foreign keys, same-entity is symmetric — neither side is the "reference" table.

**Known deficiencies** — documented data quality issues that may affect query correctness. Read these before writing queries that involve aggregation, deduplication, or cross-file joins.

**Notation** — `mnf:` prefixed terms are Manifest vocabulary concepts. Domain-specific prefixes (e.g. `ais:`, `pm:`) identify semantic types and domain entities. Physical types like `mnf:Varchar`, `mnf:Double`, `mnf:Integer` map directly to DuckDB/Parquet types.

