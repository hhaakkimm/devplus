# Scaling Reads System Design Quiz

## 1. [JUNIOR · MULTIPLE_CHOICE] What is the key challenge with read replicas when using asynchronous replication?

```json
{
 "options": [
  "Higher storage costs due to maintaining full copies of data",
  "Replication lag causing potentially stale reads",
  "Increased write latency on the primary",
  "Complex query routing logic"
 ],
 "correctAnswer": 1
}
```

**Explanation:** With async replication, there's a delay before changes reach replicas. A user might update their profile on the leader, then immediately read from a replica that hasn't received the change yet. Synchronous replication avoids this but adds write latency since the leader must wait for replicas to acknowledge.

## 2. [JUNIOR · TRUE_FALSE] Cache versioning avoids invalidation complexity by changing cache keys when data updates, making old entries naturally unreachable.

```json
{
 "correctAnswer": true
}
```

**Explanation:** Cache versioning increments a version number in the database with each update and includes that version in cache keys, avoiding complex invalidation logic and race conditions.

## 3. [MID_LEVEL · MULTIPLE_CHOICE] What should primarily drive your choice of cache TTL values?

```json
{
 "options": [
  "A safe default of 5-15 minutes for all data",
  "Business requirements for acceptable data staleness",
  "The same TTL value across all cached data for simplicity",
  "The longest possible TTL to maximize cache hit rate"
 ],
 "correctAnswer": 1
}
```

**Explanation:** Cache TTL should match business requirements around data freshness. If the requirement says 'search results can be up to 30 seconds old,' use a 30-second TTL. Different data types often have different staleness tolerances - stock prices need seconds, product descriptions can be hours.

## 4. [MID_LEVEL · MULTIPLE_CHOICE] A single cached key (say, a celebrity's profile) gets so much traffic it overloads one cache node. Which technique most directly addresses this?

```json
{
 "options": [
  "Lowering the TTL on that key",
  "Splitting the hot key into copies (key_1, key_2, ...) spread across nodes and reading a random copy",
  "Switching the cache to write-through",
  "Adding more read replicas to the database"
 ],
 "correctAnswer": 1
}
```

**Explanation:** Hot key splitting (or key replication) stores the value under several keys spread across different nodes, so reads fan out instead of hammering one node. Lowering the TTL or adding database replicas doesn't help here -- the bottleneck is a single cache node serving one extremely popular key.

## 5. [MID_LEVEL · MULTIPLE_CHOICE] What characterizes functional sharding (splitting data by business domain like users, products, orders)?

```json
{
 "options": [
  "It's purely a write scaling technique with no read benefits",
  "Domains get isolated databases optimized for their access patterns",
  "It requires consistent hashing to work for proper data distribution",
  "It eliminates the need for caching"
 ],
 "correctAnswer": 1
}
```

**Explanation:** Functional sharding separates data by business domain, allowing each database to be optimized for its specific read and write patterns. While sharding in general helps with write scaling, functional sharding also improves reads by keeping related data together and reducing database complexity.

## 6. [MID_LEVEL · TRUE_FALSE] In most applications, missing indexes on common query patterns cause more performance problems than the extra write overhead of maintaining those indexes.

```json
{
 "correctAnswer": true
}
```

**Explanation:** A query without a supporting index falls back to a full table scan, and that slowdown hits users directly as tables grow. Each index does add some work to every insert and update, but modern databases handle that cost well for typical read-heavy workloads. Indexes still consume memory and add write latency, so index the queries you actually run rather than every column.

## 7. [MID_LEVEL · MULTIPLE_CHOICE] Why do most applications benefit significantly from caching?

```json
{
 "options": [
  "Caching reduces database storage costs by offloading old data to memory",
  "Skewed access patterns mean popular content gets repeated reads",
  "Caching eliminates the need for indexes",
  "Caching improves write performance"
 ],
 "correctAnswer": 1
}
```

**Explanation:** Most applications have skewed access patterns where popular content (viral tweets, popular products) gets requested repeatedly, making caching extremely effective.

## 8. [MID_LEVEL · MULTIPLE_CHOICE] Your database is well indexed and lightly loaded, but each query is still slow because it waits on random seeks on spinning HDDs. Which change lowers the latency of each individual query?

```json
{
 "options": [
  "Add HDD-backed read replicas and spread reads across them",
  "Move the database to SSD storage",
  "Add more application servers in front of the database",
  "Reduce cache TTLs to force fresher reads"
 ],
 "correctAnswer": 1
}
```

**Explanation:** SSDs have no moving parts, so random reads are 10–100x faster than on spinning disks and every query that waits on disk gets faster. Read replicas add throughput for heavy load, but each replica still pays the same HDD seek time per query. More app servers and shorter cache TTLs do not change disk latency, and shorter TTLs send more reads to the slow disk.

## 9. [MID_LEVEL · MULTIPLE_CHOICE] What is the key benefit of request coalescing for handling hot keys?

```json
{
 "options": [
  "Reduces memory usage in caches by deduplicating stored entries across nodes",
  "Caps backend load at N requests (one per server)",
  "Improves cache hit rates",
  "Eliminates need for cache invalidation"
 ],
 "correctAnswer": 1
}
```

**Explanation:** Request coalescing ensures that even if millions of users want the same data simultaneously, your backend only receives N requests - one per application server doing the coalescing.

## 10. [MID_LEVEL · RANKING] An application server in Tokyo can use local Redis, query its local database, or make a cache-miss round trip to an origin in Virginia. Using the figures in the article, rank these operations from fastest to slowest.

```json
{
 "items": [
  "Run a well-optimized query against the local database",
  "Read a value from local in-memory Redis",
  "Make the Tokyo-to-Virginia round trip"
 ],
 "correctOrder": [
  1,
  0,
  2
 ]
}
```

**Explanation:** The article gives sub-millisecond latency for an in-memory cache hit, tens of milliseconds for a well-optimized database query, and about 200ms for its Tokyo-to-Virginia example. Keeping the caller fixed in Tokyo makes the comparison use one vantage point: local Redis → local database → cross-region origin.

## 11. [SENIOR · MULTIPLE_CHOICE] A feed endpoint performs about 20 indexed database reads per feed load. Traffic reaches 4,000 feed loads/second, while writes are only 200/second. Based on the article’s rule of thumb, which conclusion is best?

```json
{
 "options": [
  "The database sees about 4,000 read operations/second, so the primary is well below the article's scaling range.",
  "The database sees about 80,000 read operations/second, so read replicas or caching are reasonable if an indexed primary is saturated.",
  "The database sees about 80,000 read operations/second, so it must be sharded even if the primary still has headroom.",
  "The database sees about 80,000 read operations/second, so synchronous replication is required before reads can scale."
 ],
 "correctAnswer": 1
}
```

**Explanation:** Each feed load issues 20 reads, so 20 × 4,000 = 80,000 database reads/second. That falls in the article's rough 50,000–100,000 range where an indexed primary that has reached its limit may justify read replicas or caching; the number alone does not prove the data must be sharded, and synchronous replication is a consistency trade-off rather than a prerequisite for scaling reads.

## 12. [SENIOR · MULTIPLE_CHOICE] A system uses asynchronous leader-follower replication. The primary acknowledges a write to the client, then crashes before any follower has applied that write. A follower is promoted to primary. What is the key failure mode?

```json
{
 "options": [
  "The promoted follower may not contain the acknowledged write, trading lower latency and faster failover for possible data loss or stale state.",
  "The promoted follower will automatically replay the missing write from the crashed primary before accepting traffic.",
  "Clients are guaranteed read-your-writes because every write originally went through the primary.",
  "Only reads before the crash can be stale; after promotion, the replica must be fully consistent."
 ],
 "correctAnswer": 0
}
```

**Explanation:** With asynchronous replication, the primary can acknowledge a write before replicas receive it. If the primary fails in that window, promoting a replica minimizes downtime but may expose stale state or lose the unreplicated write.

## 13. [SENIOR · TRUE_FALSE] The article’s rule of thumb to scale horizontally at 50,000-100,000 reads per second applies even when the queries are unindexed, so a database at that read volume should add read replicas before adding indexes.

```json
{
 "correctAnswer": false
}
```

**Explanation:** The article’s 50,000-100,000 reads-per-second guideline explicitly assumes the database is already properly indexed. When queries are unindexed, the first step is to add indexes; adding read replicas mostly spreads inefficient full-table scans across more machines while introducing replication lag and operational complexity.

## 14. [SENIOR · TRUE_FALSE] For an endpoint dominated by repeatedly computing AVG/GROUP BY over a large reviews table, read replicas can increase total throughput but may still perform the same expensive aggregation on every request; a materialized view changes the cost profile by precomputing the result.

```json
{
 "correctAnswer": true
}
```

**Explanation:** Read replicas distribute read load, but each replica may still spend CPU and I/O recomputing the same aggregation. A materialized view trades freshness and refresh complexity for a much cheaper read path by storing the precomputed result.

## 15. [SENIOR · MULTIPLE_CHOICE] You replace a live `AVG(rating)` query with a materialized view refreshed by a background job every 10 minutes. Which requirement would make this a poor fit unless you add a more immediate refresh path?

```json
{
 "options": [
  "Showing approximate product ratings on a browsing page.",
  "Running analytics over historical review data.",
  "Reducing repeated joins across products and reviews.",
  "Showing the exact updated average immediately after each new review is submitted."
 ],
 "correctAnswer": 3
}
```

**Explanation:** Materialized views speed reads by precomputing and storing expensive results, often refreshed asynchronously. That makes them well-suited to expensive aggregations, but not to requirements that demand immediately consistent derived values after each write.
