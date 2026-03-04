# Polymarket Dataset Description

*Generated from `polymarket_description.ttl` — do not edit.*

## Datasets

| Dataset | Row Semantics | Schema | Partitioning | Format |
|---------|---------------|--------|--------------|--------|
| Gamma Market Snapshots | sdl:SnapshotRow | sdl:InferredSchema | daily + hourly (dt, hour) | Parquet |
| Gamma Event Snapshots | sdl:SnapshotRow | sdl:InferredSchema | daily + hourly (dt, hour) | Parquet |
| CLOB Price Snapshots | sdl:SnapshotRow | sdl:InferredSchema | daily + hourly (dt, hour) | Parquet |
| CLOB Orderbook Snapshots | sdl:SnapshotRow | sdl:InferredSchema | daily + hourly (dt, hour) | Parquet |
| Trade Events | sdl:EventRow | sdl:InferredSchema | daily + hourly (dt, hour) | Parquet |
| Token Holder Snapshots | sdl:SnapshotRow | sdl:InferredSchema | daily + hourly (dt, hour) | Parquet |
| Gamma Tags | — | — | daily + hourly (dt, hour) | Parquet |
| Gamma Series | — | — | daily + hourly (dt, hour) | Parquet |
| Gamma Sports | — | — | daily + hourly (dt, hour) | Parquet |

---

## Gamma Market Snapshots

**URI:** `pm:MarketSnapshots`
  
Hourly snapshots of all active Polymarket markets from the Gamma API. ~33,500 markets per snapshot, polled every 5 minutes, compacted hourly. Richest schema (~30+ columns).
  
**Row semantics:** sdl:SnapshotRow
  
**Schema:** sdl:InferredSchema
  
**Path template:** `data/parquet/{stream}/dt={date}/hour={hour}.parquet`
  
**Entity key:** `id`

### Columns

| Name | Physical Type | Semantic Type | Nullable |
|------|---------------|---------------|----------|
| `_fetched_at` | sdl:Double | pm:FetchTimestamp | no |
| `_source` | sdl:Varchar | pm:DataSourceLabel | no |
| `active` | sdl:Varchar |  | yes |
| `bestAsk` | sdl:Double | pm:Probability | yes |
| `bestBid` | sdl:Double | pm:Probability | yes |
| `category` | sdl:Varchar | pm:MarketCategory | yes |
| `clobTokenIds` | sdl:Varchar | pm:JSONArray | yes |
| `closed` | sdl:Varchar |  | yes |
| `competitive` | sdl:Double | pm:CompetitivenessScore | yes |
| `conditionId` | sdl:Varchar | pm:ConditionId | yes |
| `createdAt` | sdl:Varchar | pm:ISOTimestamp | yes |
| `description` | sdl:Varchar |  | yes |
| `enableOrderBook` | sdl:Varchar |  | yes |
| `endDate` | sdl:Varchar | pm:ISOTimestamp | yes |
| `id` | sdl:Varchar | pm:MarketId | no |
| `image` | sdl:Varchar |  | yes |
| `lastTradePrice` | sdl:Double | pm:Probability | yes |
| `liquidity` | sdl:Varchar |  | yes |
| `liquidityNum` | sdl:Double | pm:USDAmount | yes |
| `negRisk` | sdl:Varchar |  | yes |
| `oneDayPriceChange` | sdl:Double | pm:PriceChange | yes |
| `oneWeekPriceChange` | sdl:Double | pm:PriceChange | yes |
| `outcomePrices` | sdl:Varchar | pm:JSONArray | yes |
| `outcomes` | sdl:Varchar | pm:JSONArray | yes |
| `question` | sdl:Varchar |  | yes |
| `rewardsMaxSpread` | sdl:Double |  | yes |
| `rewardsMinSize` | sdl:Double |  | yes |
| `slug` | sdl:Varchar | pm:Slug | yes |
| `spread` | sdl:Double | pm:PriceSpread | yes |
| `startDate` | sdl:Varchar | pm:ISOTimestamp | yes |
| `updatedAt` | sdl:Varchar | pm:ISOTimestamp | yes |
| `volume` | sdl:Varchar |  | yes |
| `volume1mo` | sdl:Double | pm:USDAmount | yes |
| `volume1wk` | sdl:Double | pm:USDAmount | yes |
| `volume1yr` | sdl:Double | pm:USDAmount | yes |
| `volume24hr` | sdl:Double | pm:USDAmount | yes |
| `volumeNum` | sdl:Double | pm:USDAmount | yes |

### Derivations

| Derived Column | Source Columns | Function | Properties |
|----------------|----------------|----------|------------|
| `_fetched_at` |  | pm:FetcherTimestampInjection | sdl:Deterministic |
| `_source` |  | pm:FetcherSourceInjection | sdl:Deterministic |
| `spread` | `bestAsk`, `bestBid` | pm:SpreadFromBidAsk | sdl:Deterministic, sdl:Invertible |

### Known Deficiencies

| Severity | Description |
|----------|-------------|
| moderate | Parquet schemas are inferred by Polars from JSON, not declared. The schema.py file in the fetcher defines type hints but they are NOT applied during compaction. Columns may appear or disappear depending on API response changes. Types may vary between hourly files if Polars infers differently from different data batches. Datasets declare sdl:schemaStability sdl:InferredSchema to signal this. |
| moderate | Snapshot datasets (markets, events, prices, holders) contain the same entity polled multiple times per hour. Within a single hourly file, the same market/event/token may appear multiple times with slightly different values. No deduplication is performed by the compactor. |
| minor | Several columns store structured data as JSON strings rather than native Parquet nested types: outcomes, outcomePrices, clobTokenIds (in markets), bids/asks (in books), holders (in holders), markets/tags (in events). This happens because the compactor does not parse these fields into structured columns. |

---

## Gamma Event Snapshots

**URI:** `pm:EventSnapshots`
  
Hourly snapshots of Polymarket events from the Gamma API. ~7,900 events per snapshot. Each event groups one or more related markets.
  
**Row semantics:** sdl:SnapshotRow
  
**Schema:** sdl:InferredSchema
  
**Path template:** `data/parquet/{stream}/dt={date}/hour={hour}.parquet`
  
**Entity key:** `id`

### Columns

| Name | Physical Type | Semantic Type | Nullable |
|------|---------------|---------------|----------|
| `_fetched_at` | sdl:Double | pm:FetchTimestamp | no |
| `_source` | sdl:Varchar | pm:DataSourceLabel | no |
| `active` | sdl:Varchar |  | yes |
| `closed` | sdl:Varchar |  | yes |
| `commentCount` | sdl:Double |  | yes |
| `competitive` | sdl:Double | pm:CompetitivenessScore | yes |
| `description` | sdl:Varchar |  | yes |
| `endDate` | sdl:Varchar | pm:ISOTimestamp | yes |
| `id` | sdl:Varchar | pm:EventId | no |
| `liquidity` | sdl:Double | pm:USDAmount | yes |
| `markets` | sdl:Varchar |  | yes |
| `negRisk` | sdl:Varchar |  | yes |
| `openInterest` | sdl:Double |  | yes |
| `slug` | sdl:Varchar | pm:Slug | yes |
| `startDate` | sdl:Varchar | pm:ISOTimestamp | yes |
| `tags` | sdl:Varchar | pm:JSONArray | yes |
| `title` | sdl:Varchar |  | yes |
| `volume` | sdl:Double | pm:USDAmount | yes |
| `volume24hr` | sdl:Double | pm:USDAmount | yes |

### Known Deficiencies

| Severity | Description |
|----------|-------------|
| moderate | Parquet schemas are inferred by Polars from JSON, not declared. The schema.py file in the fetcher defines type hints but they are NOT applied during compaction. Columns may appear or disappear depending on API response changes. Types may vary between hourly files if Polars infers differently from different data batches. Datasets declare sdl:schemaStability sdl:InferredSchema to signal this. |
| moderate | Snapshot datasets (markets, events, prices, holders) contain the same entity polled multiple times per hour. Within a single hourly file, the same market/event/token may appear multiple times with slightly different values. No deduplication is performed by the compactor. |

---

## CLOB Price Snapshots

**URI:** `pm:PriceSnapshots`
  
Hourly snapshots of CLOB token prices and midpoints. ~2,000 tokens polled every 30 seconds. Merges /price and /midpoint endpoints.
  
**Row semantics:** sdl:SnapshotRow
  
**Schema:** sdl:InferredSchema
  
**Path template:** `data/parquet/{stream}/dt={date}/hour={hour}.parquet`
  
**Entity key:** `token_id`

### Columns

| Name | Physical Type | Semantic Type | Nullable |
|------|---------------|---------------|----------|
| `_fetched_at` | sdl:Double | pm:FetchTimestamp | no |
| `_source` | sdl:Varchar | pm:DataSourceLabel | no |
| `midpoint` | sdl:Varchar |  | yes |
| `price` | sdl:Varchar |  | yes |
| `token_id` | sdl:Varchar | pm:CLOBTokenId | no |

### Known Deficiencies

| Severity | Description |
|----------|-------------|
| moderate | Parquet schemas are inferred by Polars from JSON, not declared. The schema.py file in the fetcher defines type hints but they are NOT applied during compaction. Columns may appear or disappear depending on API response changes. Types may vary between hourly files if Polars infers differently from different data batches. Datasets declare sdl:schemaStability sdl:InferredSchema to signal this. |
| moderate | The 'price' column in clob/prices may contain either a float value (the actual price) or an error object string when the CLOB API returns an error for a specific token. Since the compactor uses ignore_errors=True, these error responses are silently mixed in with valid data. |

---

## CLOB Orderbook Snapshots

**URI:** `pm:OrderbookSnapshots`
  
Hourly snapshots of orderbook state for top 100 active tokens. Polled every 2 minutes.
  
**Row semantics:** sdl:SnapshotRow
  
**Schema:** sdl:InferredSchema
  
**Path template:** `data/parquet/{stream}/dt={date}/hour={hour}.parquet`
  
**Entity key:** `asset_id`

### Columns

| Name | Physical Type | Semantic Type | Nullable |
|------|---------------|---------------|----------|
| `_fetched_at` | sdl:Double | pm:FetchTimestamp | no |
| `_source` | sdl:Varchar | pm:DataSourceLabel | no |
| `asks` | sdl:Varchar | pm:JSONArray | yes |
| `asset_id` | sdl:Varchar | pm:CLOBTokenId | no |
| `bids` | sdl:Varchar | pm:JSONArray | yes |
| `hash` | sdl:Varchar |  | yes |
| `last_trade_price` | sdl:Varchar |  | yes |
| `market` | sdl:Varchar | pm:ConditionId | yes |
| `min_order_size` | sdl:Varchar |  | yes |
| `neg_risk` | sdl:Varchar |  | yes |
| `tick_size` | sdl:Varchar |  | yes |
| `timestamp` | sdl:Varchar |  | yes |

### Known Deficiencies

| Severity | Description |
|----------|-------------|
| moderate | Parquet schemas are inferred by Polars from JSON, not declared. The schema.py file in the fetcher defines type hints but they are NOT applied during compaction. Columns may appear or disappear depending on API response changes. Types may vary between hourly files if Polars infers differently from different data batches. Datasets declare sdl:schemaStability sdl:InferredSchema to signal this. |
| minor | Several columns store structured data as JSON strings rather than native Parquet nested types: outcomes, outcomePrices, clobTokenIds (in markets), bids/asks (in books), holders (in holders), markets/tags (in events). This happens because the compactor does not parse these fields into structured columns. |

---

## Trade Events

**URI:** `pm:Trades`
  
Hourly files of recent trades from the Data API. 100 trades polled every 60 seconds. This is the most event-like dataset — each row represents a distinct trade event, unlike the snapshot datasets. Rows are in API response order (roughly reverse chronological), not meaningfully sorted.
  
**Row semantics:** sdl:EventRow
  
**Schema:** sdl:InferredSchema
  
**Path template:** `data/parquet/{stream}/dt={date}/hour={hour}.parquet`

### Columns

| Name | Physical Type | Semantic Type | Nullable |
|------|---------------|---------------|----------|
| `_fetched_at` | sdl:Double | pm:FetchTimestamp | no |
| `_source` | sdl:Varchar | pm:DataSourceLabel | no |
| `asset` | sdl:Varchar | pm:CLOBTokenId | yes |
| `bio` | sdl:Varchar |  | yes |
| `conditionId` | sdl:Varchar | pm:ConditionId | yes |
| `eventSlug` | sdl:Varchar | pm:Slug | yes |
| `icon` | sdl:Varchar |  | yes |
| `name` | sdl:Varchar |  | yes |
| `outcome` | sdl:Varchar |  | yes |
| `outcomeIndex` | sdl:Double | pm:OutcomeIndex | yes |
| `price` | sdl:Double | pm:Probability | yes |
| `profileImage` | sdl:Varchar |  | yes |
| `proxyWallet` | sdl:Varchar | pm:ProxyWallet | yes |
| `pseudonym` | sdl:Varchar |  | yes |
| `side` | sdl:Varchar | pm:TradeSide | yes |
| `size` | sdl:Double | pm:TradeSize | yes |
| `slug` | sdl:Varchar | pm:Slug | yes |
| `timestamp` | sdl:Double |  | yes |
| `title` | sdl:Varchar |  | yes |
| `transactionHash` | sdl:Varchar | pm:TransactionHash | yes |

### Known Deficiencies

| Severity | Description |
|----------|-------------|
| moderate | Parquet schemas are inferred by Polars from JSON, not declared. The schema.py file in the fetcher defines type hints but they are NOT applied during compaction. Columns may appear or disappear depending on API response changes. Types may vary between hourly files if Polars infers differently from different data batches. Datasets declare sdl:schemaStability sdl:InferredSchema to signal this. |
| moderate | The trades dataset may contain duplicate trades across consecutive polls if the same trade appears in multiple API responses. The fetcher polls the most recent 100 trades every 60 seconds, so overlapping windows produce duplicates. |

---

## Token Holder Snapshots

**URI:** `pm:HolderSnapshots`
  
Hourly snapshots of top 20 holders per token for first 50 known markets. Polled every 10 minutes. Snapshot semantics keyed by (condition_id, token) — composite entity key.
  
**Row semantics:** sdl:SnapshotRow
  
**Schema:** sdl:InferredSchema
  
**Path template:** `data/parquet/{stream}/dt={date}/hour={hour}.parquet`
  
**Entity key:** `condition_id`

### Columns

| Name | Physical Type | Semantic Type | Nullable |
|------|---------------|---------------|----------|
| `_fetched_at` | sdl:Double | pm:FetchTimestamp | no |
| `_source` | sdl:Varchar | pm:DataSourceLabel | no |
| `condition_id` | sdl:Varchar | pm:ConditionId | no |
| `holders` | sdl:Varchar |  | yes |
| `token` | sdl:Varchar | pm:CLOBTokenId | no |

### Derivations

| Derived Column | Source Columns | Function | Properties |
|----------------|----------------|----------|------------|
| `condition_id` |  | pm:FetcherConditionIdEnrichment | sdl:Deterministic |

### Known Deficiencies

| Severity | Description |
|----------|-------------|
| moderate | Parquet schemas are inferred by Polars from JSON, not declared. The schema.py file in the fetcher defines type hints but they are NOT applied during compaction. Columns may appear or disappear depending on API response changes. Types may vary between hourly files if Polars infers differently from different data batches. Datasets declare sdl:schemaStability sdl:InferredSchema to signal this. |
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
| pm:CLOBTokenId | CLOB Token ID | sdl:Varchar |  |  | Identifier for a tradable token on Polymarket's CLOB (Central Limit Order Book). Each market outcome has a distinct token ID. Long numeric string. |
| pm:CompetitivenessScore | Market Competitiveness Score | sdl:Double | 0.0–1.0 |  | Score from 0.0 to 1.0 indicating how competitive a market is. |
| pm:ConditionId | On-Chain Condition ID | sdl:Varchar |  |  | Hex-encoded blockchain condition identifier linking a Polymarket market to its on-chain resolution contract. Serves as the primary cross-system join key between gamma/markets, trades, and holders. |
| pm:DataSourceLabel | Data Source Label | sdl:Varchar |  |  | Label identifying which fetcher stream produced this row (e.g. 'gamma/markets', 'clob/prices'). Injected by the fetcher, not from the API. |
| pm:EventId | Polymarket Event ID | sdl:Varchar |  |  | Unique identifier for an event (a grouping of related markets) on Polymarket's Gamma API. |
| pm:FetchTimestamp | Fetch Timestamp | sdl:Double |  |  | Unix epoch float (seconds since 1970-01-01T00:00:00Z) injected by the fetcher at collection time. NOT from the API. Stored as Float64, not TimestampTZ, because the fetcher writes time.time() directly. |
| pm:ISOTimestamp | ISO 8601 Timestamp String | sdl:Varchar |  |  | ISO 8601 formatted timestamp as a string. Used by the Gamma API for dates (startDate, endDate, createdAt, etc.). |
| pm:JSONArray | JSON-Serialized Array | sdl:Varchar |  |  | A column whose physical type is Varchar but whose content is a JSON-encoded array. Examples: outcomes='["Yes","No"]', clobTokenIds='["1234","5678"]', bids/asks orderbook levels. Columns with this type should also declare sdl:embeddedStructure for the inner element type. |
| pm:MarketCategory | Market Category | sdl:Varchar |  |  | Category label for a market (e.g. 'Politics', 'Sports', 'Crypto'). Open-ended but constrained set from the platform. |
| pm:MarketId | Polymarket Market ID | sdl:Varchar |  |  | Unique identifier for a prediction market on Polymarket's Gamma API. Varchar string, typically a short alphanumeric slug. |
| pm:OutcomeIndex | Outcome Index | sdl:Double | 0.0 |  | Zero-based index into a market's outcome array. Typically 0 or 1 for binary Yes/No markets. |
| pm:PriceChange | Price Change | sdl:Double |  |  | Absolute change in price over a time window. Can be negative. |
| pm:PriceSpread | Bid-Ask Spread | sdl:Double | 0.0 |  | Difference between best ask and best bid prices. |
| pm:Probability | Probability | sdl:Double | 0.0–1.0 |  | Price interpreted as a probability. On Polymarket, prices of outcome tokens range from 0.0 to 1.0, representing the market-implied probability of that outcome. |
| pm:ProxyWallet | Proxy Wallet Address | sdl:Varchar |  |  | Ethereum proxy wallet address for a Polymarket trader. |
| pm:Slug | URL Slug | sdl:Varchar |  |  | URL-safe slug used in Polymarket URLs. |
| pm:TradeSide | Trade Side | sdl:Varchar |  |  | Direction of a trade: "BUY" or "SELL". |
| pm:TradeSize | Trade Size | sdl:Double | >0.0 |  | Number of shares in a trade. Stored as Float64 because the compactor infers from JSON (which has no integer type). |
| pm:TransactionHash | Transaction Hash | sdl:Varchar |  |  | On-chain transaction hash for a trade settlement. |
| pm:USDAmount | USD Amount | sdl:Double | 0.0 | USD | Dollar amount. Volume, liquidity, etc. |

## Cross-Dataset Relationships

### Foreign Keys

| Relationship | From (Dataset.Column) | To (Dataset.Column) | Integrity |
|-------------|----------------------|---------------------|-----------|
| Trades → Markets (via conditionId) | Trade Events.`conditionId` | Gamma Market Snapshots.`conditionId` | sdl:PartialIntegrity |
| Trades → Prices (via asset/token_id) | Trade Events.`asset` | CLOB Price Snapshots.`token_id` | sdl:PartialIntegrity |
| Holders → Markets (via condition_id) | Token Holder Snapshots.`condition_id` | Gamma Market Snapshots.`conditionId` | sdl:PartialIntegrity |
| Books → Markets (via market/conditionId) | CLOB Orderbook Snapshots.`market` | Gamma Market Snapshots.`conditionId` | sdl:PartialIntegrity |

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

This section explains SDL concepts used in the tables above, to help you write correct queries against this data.

**Row semantics** determine how to interpret rows:

- **Event rows** (`sdl:EventRow`) — each row is an independent event or observation. No deduplication needed.
- **Snapshot rows** (`sdl:SnapshotRow`) — each row is a point-in-time observation of a recurring entity. The same entity appears multiple times. To get the latest state, deduplicate by entity key ordered by `_fetched_at` descending.

**Entity key** — the column that identifies which entity a snapshot row describes. Multiple rows with the same entity key are repeated observations over time, not distinct entities. Use `ROW_NUMBER() OVER (PARTITION BY {entity_key} ORDER BY _fetched_at DESC)` to select the most recent observation per entity within a file.

**Schema stability** affects query robustness:

- **Inferred** (`sdl:InferredSchema`) — schema is inferred from data and may vary between files. Use `TRY_CAST` for type safety, handle potentially missing columns, and use `UNION BY NAME` when combining files from different time periods.

**Foreign keys** — the From and To columns are joinable across datasets, even when column names differ. Check the Integrity column: `sdl:PartialIntegrity` means some values may not resolve in the target (use LEFT JOIN rather than INNER JOIN if you need all rows).

**Same entity** — these columns across different datasets refer to the same real-world entity and are joinable. Unlike foreign keys, same-entity is symmetric — neither side is the "reference" table.

**Known deficiencies** — documented data quality issues that may affect query correctness. Read these before writing queries that involve aggregation, deduplication, or cross-file joins.

**Notation** — `sdl:` prefixed terms are SDL vocabulary concepts. Domain-specific prefixes (e.g. `ais:`, `pm:`) identify semantic types and domain entities. Physical types like `sdl:Varchar`, `sdl:Double`, `sdl:Integer` map directly to DuckDB/Parquet types.

