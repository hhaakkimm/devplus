# Core Concepts Quiz

## 1. [JUNIOR · MULTIPLE_CHOICE] Which external system is the go-to choice for full-text search, like searching tweets or documents?

```json
{
 "options": [
  "Elasticsearch",
  "Redis",
  "PostGIS",
  "DynamoDB"
 ],
 "correctAnswer": 0
}
```

**Explanation:** Elasticsearch is the standard external index for full-text search. PostGIS handles geospatial queries in Postgres, Redis is a cache, and DynamoDB is a NoSQL database. External indexes like Elasticsearch typically sync from the primary database via change data capture.

## 2. [JUNIOR · TRUE_FALSE] A Layer 7 load balancer can route requests based on the content of the HTTP request, while a Layer 4 load balancer distributes traffic at the TCP connection level.

```json
{
 "correctAnswer": true
}
```

**Explanation:** Layer 7 load balancers operate at the application level, so they can inspect the HTTP request and route API calls to one service and web pages to another. Layer 4 balancers work at the TCP level -- faster but dumber, distributing connections without looking at content.

## 3. [MID_LEVEL · RANKING] Order these operations by typical latency, with the fastest (lowest latency) at the top of the list and the slowest (highest latency) at the bottom:

```json
{
 "items": [
  "SSD read",
  "Memory access",
  "Network call within a data center",
  "Cross-continent network call"
 ],
 "correctOrder": [
  1,
  0,
  2,
  3
 ]
}
```

**Explanation:** Memory access takes nanoseconds, SSD reads take microseconds, network calls within a data center take 1-10 milliseconds, and cross-continent calls take tens to hundreds of milliseconds. These gaps drive design decisions like whether to cache and whether geographic distribution is worth the complexity.

## 4. [MID_LEVEL · MULTIPLE_CHOICE] When is cursor-based pagination a better fit than offset-based pagination?

```json
{
 "options": [
  "When the result set is small and rarely changes",
  "When you need to jump directly to an arbitrary page number",
  "When results must be filtered by multiple fields",
  "When paginating real-time data where new items are added frequently"
 ],
 "correctAnswer": 3
}
```

**Explanation:** With offset-based pagination, items inserted while a user is paging shift every subsequent page, causing duplicates or skipped items. Cursor-based pagination anchors to a stable position (the last item seen), so it stays correct as new data arrives. For mostly-static data, offset-based is fine and simpler.

## 5. [MID_LEVEL · MATCHING_PAIRS] Match each technique to the problem it solves:

```json
{
 "leftItems": [
  "Cache-aside with Redis",
  "Consistent hashing",
  "Change data capture (CDC)",
  "Sharding"
 ],
 "rightItems": [
  "Splitting data across servers once a single database hits its limits",
  "Keeping an external search index in sync with the primary database",
  "Reducing read load on the database",
  "Minimizing data movement when servers are added or removed"
 ],
 "correctPairs": [
  2,
  3,
  1,
  0
 ]
}
```

**Explanation:** Cache-aside serves frequent reads from memory to reduce database load. Consistent hashing keeps data movement small when cluster membership changes. CDC streams changes from the primary database to external indexes like Elasticsearch. Sharding splits data across independent servers when storage or write throughput outgrows one machine.

## 6. [MID_LEVEL · MULTIPLE_CHOICE] Which of these systems has the strongest case for strong consistency rather than eventual consistency?

```json
{
 "options": [
  "A social media feed showing recent posts",
  "A seat booking system for concert tickets",
  "An analytics dashboard for internal metrics",
  "A product review section on an e-commerce site"
 ],
 "correctAnswer": 1
}
```

**Explanation:** Booking systems must prevent two people from buying the same seat, so reading stale data for even a few seconds creates real problems. Feeds, dashboards, and reviews all tolerate staleness fine -- nobody is harmed if a post or review shows up a few seconds late. The rule of thumb: money, inventory, and limited resources need strong consistency.

## 7. [MID_LEVEL · TRUE_FALSE] gRPC is generally avoided for public-facing APIs because browsers don't natively support it.

```json
{
 "correctAnswer": true
}
```

**Explanation:** Browsers can't speak gRPC natively -- gRPC-Web exists as a workaround but requires a proxy and doesn't support all features. That's why the common pattern is REST for external APIs and gRPC internally, where its binary serialization and HTTP/2 transport make service-to-service calls significantly faster.

## 8. [MID_LEVEL · MULTIPLE_CHOICE] A DynamoDB table for a social app uses user_id as its partition key. Why does the query "get all posts mentioning hashtag Y" perform poorly?

```json
{
 "options": [
  "DynamoDB can't store text fields like hashtags efficiently",
  "Hashtag queries require a SQL JOIN, which DynamoDB doesn't support",
  "The table wasn't designed for that access pattern, so the query has to scan the entire table",
  "The partition key makes writes slow, which backs up reads"
 ],
 "correctAnswer": 2
}
```

**Explanation:** DynamoDB requires designing partition and sort keys around your access patterns upfront. Partitioning by user_id makes "get all posts for user X" a fast single-partition lookup, but a hashtag query matches no key structure, so it must scan the whole table. With NoSQL, you have to know your queries before you design the table.

## 9. [MID_LEVEL · MULTIPLE_CHOICE] An Instagram-like app shards its database by user_id. Which query becomes expensive as a result?

```json
{
 "options": [
  "Fetching all posts for a specific user",
  "Computing trending posts across all users",
  "Fetching a user's profile and follower count",
  "Loading all comments a user has made"
 ],
 "correctAnswer": 1
}
```

**Explanation:** Sharding by user_id keeps all of a user's data on one shard, so user-scoped queries stay fast single-shard lookups. But any global query -- like trending posts across all users -- now has to hit every shard and aggregate the results. Every shard key choice makes some queries fast and others expensive.

## 10. [MID_LEVEL · TRUE_FALSE] With consistent hashing, adding one server to a 10-server cluster requires moving roughly 90% of the keys.

```json
{
 "correctAnswer": false
}
```

**Explanation:** It's roughly the opposite: consistent hashing moves only about 10% of keys (those in the range claimed by the new server), while simple modulo hashing is what forces ~90% of keys to move because nearly every hash maps to a different server when N changes. That difference is the entire reason consistent hashing exists.

## 11. [SENIOR · MULTIPLE_CHOICE] A popular cache entry expires, and hundreds of concurrent requests miss simultaneously and hammer the database to regenerate it. Which approach directly addresses this problem?

```json
{
 "options": [
  "Shorter TTLs on all cache entries",
  "Adding read replicas to absorb the load",
  "Moving the cache in-process to eliminate network hops",
  "Locking so one request regenerates the entry while the others wait"
 ],
 "correctAnswer": 3
}
```

**Explanation:** This is a cache stampede (thundering herd). Locking ensures only one request pays the regeneration cost; early recomputation and staggered TTLs are the other standard defenses. Shorter TTLs make stampedes more frequent, and read replicas just spread the spike rather than preventing it.

## 12. [SENIOR · TRUE_FALSE] According to PACELC, even when the network is healthy, choosing strong consistency typically costs extra latency.

```json
{
 "correctAnswer": true
}
```

**Explanation:** CAP only describes behavior during partitions, which are rare. PACELC adds: Else (during normal operation), you trade Latency against Consistency -- strong consistency requires nodes to coordinate before responding, and that coordination takes time. This is why strongly consistent systems are slower even on a healthy network.

## 13. [SENIOR · MULTIPLE_CHOICE] Your Postgres database handles 2,000 writes per second and stores 50GB, with growth projected to roughly double over two years. An engineer proposes sharding now. What's the strongest counterargument?

```json
{
 "options": [
  "Sharding only helps read throughput, and this is a write-bound workload",
  "These numbers are well within a single well-tuned instance's capacity, so sharding adds major complexity for no current benefit",
  "Consistent hashing hasn't been implemented yet, so sharding would cause excessive data movement",
  "Postgres doesn't support sharding, so the system would need to migrate to DynamoDB first"
 ],
 "correctAnswer": 1
}
```

**Explanation:** At 2K writes/sec and 50GB (even doubled), you're nowhere near the tens-of-thousands-of-writes-per-second range where a single well-tuned instance starts to struggle, so there's nothing to prove single-node won't scale yet. Sharding costs you cross-shard transactions, hot spot management, and painful resharding, so the numbers have to justify it first. Do the capacity math before reaching for it.

## 14. [SENIOR · MULTIPLE_CHOICE] A banking app sharded by account_id needs to support transfers between arbitrary accounts, which may live on different shards. What's the key design implication?

```json
{
 "options": [
  "Transfers now require distributed transactions or sagas, so it's worth designing shard boundaries to keep related accounts together",
  "The database will handle cross-shard transactions transparently, so no design change is needed",
  "Transfers must be made eventually consistent, since atomicity is impossible across shards",
  "Switching from hash-based to range-based sharding eliminates the problem"
 ],
 "correctAnswer": 0
}
```

**Explanation:** Cross-shard transactions are one of sharding's biggest costs: updating two accounts atomically across shards requires distributed transactions or sagas, which are complex and slow. The best defense is choosing shard boundaries that keep transactional units on the same shard. Range-based sharding doesn't fix this -- arbitrary account pairs can still land on different shards.

## 15. [SENIOR · MULTIPLE_CHOICE] An e-commerce platform is debating whether to use strong or eventual consistency. What's the most defensible position?

```json
{
 "options": [
  "Strong consistency everywhere, since correctness always outweighs performance",
  "Eventual consistency everywhere, since e-commerce traffic demands availability",
  "Strong consistency for inventory and orders, eventual consistency for product descriptions and reviews",
  "Eventual consistency for inventory, strong consistency for reviews, since reviews are user-generated"
 ],
 "correctAnswer": 2
}
```

**Explanation:** You don't have to pick one model for the whole system -- different parts have different requirements. Inventory and order processing need strong consistency to prevent overselling, while nobody is harmed if a review takes 5 seconds to appear. Applying strong consistency everywhere costs latency and availability where it buys nothing.
