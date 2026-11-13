# Database Sharding System Design Quiz

## 1. [JUNIOR · TRUE_FALSE] Simple modulo-based hash sharding (e.g., hash(key) % N shards) makes it easy to add or remove shards without significant data movement.

```json
{
 "correctAnswer": false
}
```

**Explanation:** Simple modulo hashing requires massive data redistribution when changing shard count. Going from hash(key) % 4 to hash(key) % 5 changes where most records map, requiring most data to move. Consistent hashing is a different technique that minimizes this problem by only moving data from affected shards.

## 2. [JUNIOR · MULTIPLE_CHOICE] What is the 'celebrity problem' in sharding?

```json
{
 "options": [
  "Celebrities refuse to use sharded databases",
  "Some keys generate far more traffic, creating hot spots",
  "Sharding celebrities' data is illegal or not allowed under GDPR",
  "Celebrity data is too large to store"
 ],
 "correctAnswer": 1
}
```

**Explanation:** The celebrity problem occurs when certain keys (like Taylor Swift's user_id) generate 1000x more traffic than normal keys. Even with perfect distribution, that one shard becomes overloaded, creating a hot spot that becomes your bottleneck.

## 3. [MID_LEVEL · MULTIPLE_CHOICE] What makes a good shard key?

```json
{
 "options": [
  "Low cardinality and uneven distribution",
  "High cardinality and even distribution",
  "Boolean fields for simplicity",
  "Always use creation timestamp"
 ],
 "correctAnswer": 1
}
```

**Explanation:** A good shard key needs high cardinality (many unique values), even distribution across shards, and should align with your most common query patterns so queries hit just one shard instead of spanning multiple shards.

## 4. [MID_LEVEL · MULTIPLE_CHOICE] What is the main advantage of range-based sharding (e.g., orders sharded by date, with January on shard 1 and February on shard 2)?

```json
{
 "options": [
  "It provides even distribution of data",
  "Range queries within a shard's key range avoid cross-shard reads",
  "It eliminates hot spots",
  "It automatically rebalances data as shards fill up"
 ],
 "correctAnswer": 1
}
```

**Explanation:** Range-based sharding is useful when you frequently query contiguous ranges that fall within one shard's boundaries. If you shard orders by date, a query for 'all orders in January' can hit just one shard. Queries that span shard boundaries still need cross-shard reads, and the downside is potential hot spots when certain ranges (like the current month) get most of the traffic.

## 5. [MID_LEVEL · MULTIPLE_CHOICE] A transaction updates one user's profile and preferences. Which data placement lets this transaction commit on a single shard?

```json
{
 "options": [
  "Put the profile and preferences on different shards",
  "Keep both records on the same user-ID shard",
  "Place every profile on a randomly selected shard",
  "Distribute each record's fields across several shards"
 ],
 "correctAnswer": 1
}
```

**Explanation:** When every record touched by this transaction is on one shard, a local transaction can update them atomically. Operations involving records on other shards can still require distributed coordination.

## 6. [MID_LEVEL · MULTIPLE_CHOICE] How should you handle a query like 'get top 10 most popular posts globally' when sharding by user_id?

```json
{
 "options": [
  "Avoid it entirely, it's impossible with user_id sharding",
  "Cache the results since it requires hitting all shards",
  "Reshard by post_id instead",
  "Store all posts on one shard"
 ],
 "correctAnswer": 1
}
```

**Explanation:** Cross-shard queries that need global aggregation should be cached. The first query is expensive (hits all shards), but subsequent requests hit the cache. This works well for queries that don't need real-time accuracy like leaderboards and trending content.

## 7. [MID_LEVEL · TRUE_FALSE] In basic two-phase commit, a participant that has voted to commit can remain blocked if it cannot obtain the coordinator's final decision.

```json
{
 "correctAnswer": true
}
```

**Explanation:** After preparing, a participant cannot safely choose commit or abort on its own because other participants may have received a decision. A recoverable or replicated coordinator can improve availability, but a heartbeat alone does not reveal that decision.

## 8. [MID_LEVEL · TRUE_FALSE] You should mention sharding early in a system design interview to show you understand distributed systems.

```json
{
 "correctAnswer": false
}
```

**Explanation:** Premature sharding is a common mistake. You need to establish why a single database won't work first by doing capacity planning (storage, write/read throughput). Show the math proving you've hit limits before proposing sharding.

## 9. [MID_LEVEL · MULTIPLE_CHOICE] A social app shards users by user ID and posts by post ID, so a user's posts usually live on other shards. The profile page shows the user's post count and recent post titles. Which change lets the profile page get this from the user's shard alone, without moving the posts?

```json
{
 "options": [
  "Query every post shard for each profile request",
  "Store a copy of the post count and recent titles on the user's shard",
  "Move user data into a separate central database",
  "Run two-phase commit for each profile read"
 ],
 "correctAnswer": 1
}
```

**Explanation:** Storing a small copy of the post data on the user's shard is denormalization: the profile page reads one shard, while the full posts stay where they are. The cost is that creating or deleting a post must also update that copy, usually with eventual consistency. Querying every post shard is the cross-shard fan-out this avoids, and two-phase commit coordinates writes rather than speeding up reads.

## 10. [MID_LEVEL · MULTIPLE_CHOICE] For a social media app where most queries are user-centric (user's posts, followers, likes), what would be the best shard key?

```json
{
 "options": [
  "post_id",
  "user_id",
  "created_at",
  "content_type"
 ],
 "correctAnswer": 1
}
```

**Explanation:** user_id is ideal because most queries are scoped to a single user anyway ('show me this user's data'). This means queries hit just one shard. It has high cardinality, distributes evenly with hashing, and aligns perfectly with query patterns.

## 11. [SENIOR · TRUE_FALSE] A table sharded by creation time can have plenty of total storage capacity across old shards while still being write-bottlenecked, because new rows concentrate on the newest range.

```json
{
 "correctAnswer": true
}
```

**Explanation:** The article warns that time-based range sharding often sends nearly all new writes to the most recent shard, while older shards sit mostly idle. This means storage may be distributed, but write throughput is still limited by the hottest current shard.

## 12. [SENIOR · TRUE_FALSE] For a dominant query that must touch every shard, increasing the shard count can solve storage pressure while making that query more expensive to coordinate and merge.

```json
{
 "correctAnswer": true
}
```

**Explanation:** Sharding gives each shard its own CPU, memory, storage, and connection pool, so it can relieve single-machine capacity limits. But the article emphasizes that queries spanning shards are expensive; as the number of shards grows, fan-out, coordination, and result merging become more painful.

## 13. [SENIOR · MULTIPLE_CHOICE] Your database is 230 TiB and grows by 8 TiB per month. The article notes that even large single-node databases like Aurora max out around 256 TiB. Ignoring migration lead time, what conclusion follows?

```json
{
 "options": [
  "You have about 8 months before capacity is a concern, and table partitioning will add storage capacity.",
  "You have about 26 months before capacity is a concern, because only the remaining TiB count matters.",
  "You have about 3.25 months before hitting the single-machine storage ceiling, and sharding is the relevant scale-out option.",
  "You are already over the limit, because sharding must begin once a database exceeds 128 TiB."
 ],
 "correctAnswer": 2
}
```

**Explanation:** The remaining capacity is 256 - 230 = 26 TiB, and at 8 TiB per month that lasts 3.25 months. Partitioning may improve management inside one database, but it does not add machines or bypass a single instance’s storage ceiling; sharding does.

## 14. [SENIOR · MULTIPLE_CHOICE] A SaaS product assigns each customer company a contiguous range of user IDs. Different queries target different companies, but each query scans users within one company's range. Which sharding strategy keeps those scans localized?

```json
{
 "options": [
  "Shard by created_at using ranges, because new records will naturally go to the newest shard.",
  "Hash each individual user_id, because hash-based sharding is always the best default regardless of query locality.",
  "Use range-based sharding over the company/user ID ranges so tenant-scoped queries stay localized.",
  "Use directory-based sharding for every user, because it avoids needing a shard key."
 ],
 "correctAnswer": 2
}
```

**Explanation:** The article notes that range-based sharding works well when different users naturally query different ranges, such as multi-tenant systems where each company owns a range of IDs. Hashing individual user IDs may distribute evenly, but it can destroy locality for tenant-scoped range queries.

## 15. [SENIOR · MULTIPLE_CHOICE] A single PostgreSQL database has a 500M-row orders table. Queries for last month’s orders are slow, and maintenance tasks like vacuuming or rebuilding indexes are painful, but the machine still has enough CPU, storage, and write capacity. Based on the article, what is the best next step?

```json
{
 "options": [
  "Hash-shard the orders table across multiple databases by order_id to spread all reads and writes immediately.",
  "Horizontally partition the orders table inside the same database, for example by month or year.",
  "Move to directory-based sharding so each month can be remapped dynamically.",
  "Vertically partition by putting order_id in one database and the rest of the columns in another."
 ],
 "correctAnswer": 1
}
```

**Explanation:** The article distinguishes partitioning from sharding: partitioning helps a single database manage a huge table more efficiently without adding machines. In this scenario, the bottleneck is table size, scans, and maintenance overhead—not the limits of a single machine—so intra-database partitioning is the lower-complexity fix.
