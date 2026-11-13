# PostgreSQL System Design Quiz

## 1. [JUNIOR · MULTIPLE_CHOICE] What is the primary bottleneck for write performance in a single PostgreSQL instance?

```json
{
 "options": [
  "CPU processing power",
  "Available RAM",
  "Disk I/O for WAL writes",
  "Network bandwidth"
 ],
 "correctAnswer": 2
}
```

**Explanation:** PostgreSQL's Write-Ahead Log (WAL) must be written to disk before transactions can commit to ensure durability. Since WAL writes are sequential and synchronous, disk I/O becomes the primary bottleneck for write throughput, typically limiting a well-tuned instance to around 5,000 writes per second per core.

## 2. [JUNIOR · MULTIPLE_CHOICE] Which PostgreSQL scaling strategy involves distributing data across multiple PostgreSQL instances based on a chosen column?

```json
{
 "options": [
  "Table partitioning within a single database instance",
  "Read replicas",
  "Horizontal sharding",
  "Connection pooling"
 ],
 "correctAnswer": 2
}
```

**Explanation:** Horizontal sharding distributes data across multiple PostgreSQL instances based on a sharding key (like user_id). Unlike PostgreSQL's built-in table partitioning (which splits data within a single instance), sharding requires external logic to route queries to the correct instance.

## 3. [MID_LEVEL · MULTIPLE_CHOICE] With asynchronous PostgreSQL read replicas, how can you ensure a user sees their own just-written data without sacrificing replica read performance?

```json
{
 "options": [
  "Convert to synchronous replication",
  "Route that specific user's critical reads to the primary",
  "Add more read replicas",
  "Use Serializable isolation level"
 ],
 "correctAnswer": 1
}
```

**Explanation:** With async replicas, there's replication lag. Rather than making all writes synchronous (hurting write performance), you can selectively route critical reads to the primary. For example, after posting a comment, route that user's reads to the primary for a few seconds while replicas catch up.

## 4. [MID_LEVEL · TRUE_FALSE] PostgreSQL's partial indexes can significantly improve performance and reduce storage when most queries only need a subset of data.

```json
{
 "correctAnswer": true
}
```

**Explanation:** Partial indexes only index rows that meet specific conditions (e.g., WHERE status = 'active'). This makes the index smaller, faster to maintain, and more efficient for queries that typically filter on the same conditions, especially when most of your data is inactive or deleted records.

## 5. [MID_LEVEL · TRUE_FALSE] PostgreSQL's Repeatable Read isolation level provides stronger guarantees than the SQL standard requires, preventing phantom reads.

```json
{
 "correctAnswer": true
}
```

**Explanation:** PostgreSQL's Repeatable Read implementation is stronger than the SQL standard. While the SQL standard allows phantom reads at this level, PostgreSQL's implementation prevents them by creating a consistent snapshot that doesn't allow new rows to appear that match your query conditions.

## 6. [MID_LEVEL · MULTIPLE_CHOICE] Which scenario is a poor fit for PostgreSQL's architecture?

```json
{
 "options": [
  "E-commerce system with complex product relationships",
  "Global app requiring millions of writes per second across regions",
  "Application needing ACID-compliant transactions",
  "Search feature requiring full-text indexing"
 ],
 "correctAnswer": 1
}
```

**Explanation:** PostgreSQL has a single-primary architecture where all writes go through one node. For global applications requiring massive write throughput across multiple regions, databases like Cassandra (multi-master) or CockroachDB (distributed SQL) are better suited.

## 7. [MID_LEVEL · RANKING] Using the article's rough throughput estimates, order these PostgreSQL write operations with the lowest throughput at the top of the list and the highest throughput at the bottom:

```json
{
 "items": [
  "Simple inserts",
  "Complex transactions (multiple tables/indexes)",
  "Updates with index modifications"
 ],
 "correctOrder": [
  1,
  2,
  0
 ]
}
```

**Explanation:** From top to bottom: complex transactions, then updates with index modifications, then simple inserts. The article estimates complex transactions touching multiple tables and indexes at hundreds per second, updates with index modifications at ~1,000-2,000 per second per core, and simple inserts at ~5,000 per second per core. Each extra table or index an operation touches adds work, so throughput drops.

## 8. [MID_LEVEL · MULTIPLE_CHOICE] When should you consider using PostgreSQL's FOR UPDATE clause?

```json
{
 "options": [
  "To speed up read queries by reducing index lookups",
  "To ensure atomic operations across related rows",
  "To improve write performance on large tables",
  "To enable full-text search"
 ],
 "correctAnswer": 1
}
```

**Explanation:** FOR UPDATE provides row-level locking to ensure atomic operations. For example, in an auction system, you'd use FOR UPDATE when checking the current bid and placing a new one to prevent two users from simultaneously bidding based on the same outdated information.

## 9. [MID_LEVEL · MULTIPLE_CHOICE] Which PostgreSQL feature allows you to avoid needing a separate Elasticsearch cluster for many applications?

```json
{
 "options": [
  "JSONB columns with schema-flexible document storage",
  "Full-text search with GIN indexes",
  "PostGIS extension",
  "Table partitioning"
 ],
 "correctAnswer": 1
}
```

**Explanation:** PostgreSQL's built-in full-text search with GIN indexes supports word stemming, relevance ranking, multiple languages, and complex queries with AND/OR/NOT operations. This eliminates the need for Elasticsearch in many use cases, keeping the architecture simpler.

## 10. [MID_LEVEL · TRUE_FALSE] PostgreSQL's asynchronous replication provides better write performance than synchronous replication but may result in data loss during failover.

```json
{
 "correctAnswer": true
}
```

**Explanation:** With asynchronous replication, the primary confirms writes immediately without waiting for replica acknowledgment, providing better performance. However, if the primary fails before changes are replicated, those changes can be lost. Synchronous replication waits for replica confirmation, ensuring no data loss but with higher latency.

## 11. [SENIOR · MULTIPLE_CHOICE] You switch PostgreSQL from asynchronous to synchronous replication because the system cannot tolerate losing committed writes during failover. What failure mode must the design now account for?

```json
{
 "options": [
  "If the required synchronous standby is unavailable or slow, commits can block or fail until replication catches up or configuration changes",
  "The primary will silently continue asynchronously, preserving write latency with no durability trade-off",
  "Read replicas will become fresher, but write behavior on the primary is unchanged",
  "PostgreSQL will automatically shard writes across replicas, increasing write throughput but weakening consistency"
 ],
 "correctAnswer": 0
}
```

**Explanation:** Synchronous replication improves durability because a commit waits for confirmation from another node. The trade-off is that the replica is now on the write path, so replica slowness, network issues, or standby failure can directly impact write availability and latency.

## 12. [SENIOR · MULTIPLE_CHOICE] A social profile page frequently runs: `SELECT title, created_at FROM posts WHERE user_id = ? ORDER BY created_at DESC LIMIT 20`. Which index best matches this access pattern?

```json
{
 "options": [
  "A B-tree index on `(created_at, user_id)`, because the query sorts by `created_at`",
  "A B-tree index on `(user_id, created_at)`, because it first narrows to one user and then reads that user's posts in time order",
  "Two separate B-tree indexes, one on `user_id` and one on `created_at`, because PostgreSQL can always combine them optimally",
  "A GIN index on `(user_id, created_at)`, because GIN indexes are optimized for multi-column lookups"
 ],
 "correctAnswer": 1
}
```

**Explanation:** For a composite B-tree index, column order matters: the equality predicate on `user_id` should come first, followed by the column used for ordering/range access. Separate indexes may help some queries, but they usually cannot satisfy this pattern as efficiently as a single index matching the filter and sort order.

## 13. [SENIOR · TRUE_FALSE] For a query that matches a large fraction of a table, adding a B-tree index on the filtered column may not improve read latency, while still increasing write cost and storage usage.

```json
{
 "correctAnswer": true
}
```

**Explanation:** The article notes that PostgreSQL's planner may prefer a sequential scan when an index is not selective enough. Even unused or rarely useful indexes still have to be maintained on writes and consume disk space, so indexing every column can hurt a write-heavy system.

## 14. [SENIOR · MULTIPLE_CHOICE] A viral post receives thousands of likes per second, and each like transaction both inserts a row into `likes` and increments `posts.like_count` on the same post row. Which design best addresses the PostgreSQL bottleneck while preserving acceptable product behavior described in the article?

```json
{
 "options": [
  "Run the transactions at `Serializable` isolation so the increments are more scalable",
  "Add an index on `posts.like_count` so the counter row can be updated faster",
  "Record likes as writes and update/display the like count asynchronously or from a cache, accepting eventual consistency",
  "Move the `posts` table to a read replica so the counter updates do not affect the primary"
 ],
 "correctAnswer": 2
}
```

**Explanation:** A single frequently updated counter row becomes a hot spot because all transactions contend on the same row. The article treats like counts as a case where eventual consistency is acceptable, so decoupling the exact counter update from the like write avoids unnecessary contention.

## 15. [SENIOR · TRUE_FALSE] After sharding a PostgreSQL-backed social app by user_id, creating a DM thread between two users on different shards can still be made atomic with one ordinary local PostgreSQL transaction.

```json
{
 "correctAnswer": false
}
```

**Explanation:** A local PostgreSQL transaction gives ACID guarantees only within the database instance handling that transaction. Once related rows are split across shards, cross-shard operations require extra coordination, a different data model, or accepting weaker consistency.
