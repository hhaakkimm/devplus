# Scaling Writes System Design Quiz

## 1. [JUNIOR · MATCHING_PAIRS] Match each write-scaling technique to its primary purpose as described in the article.

```json
{
 "leftItems": [
  "Horizontal sharding",
  "Vertical partitioning",
  "Write queue",
  "Load shedding"
 ],
 "rightItems": [
  "Buffers writes to absorb short-lived traffic bursts",
  "Splits rows across multiple servers to spread write load",
  "Drops the least important writes when the system is overwhelmed",
  "Splits columns into separate tables by access pattern"
 ],
 "correctPairs": [
  1,
  3,
  0,
  2
 ]
}
```

**Explanation:** Horizontal sharding splits rows across servers so each handles a portion of the writes. Vertical partitioning splits columns into specialized tables based on how the data is accessed. A queue buffers writes to smooth short-lived bursts, while load shedding drops the least important writes when the system is overwhelmed rather than letting everything fail.

## 2. [JUNIOR · MULTIPLE_CHOICE] According to the article, what are writes commonly bottlenecked by when considering vertical scaling?

```json
{
 "options": [
  "Cache hit rate, CDN location, and browser rendering speed",
  "Schema naming, API versioning, and deployment frequency",
  "Disk I/O, CPU, or network bandwidth",
  "User interface complexity, image size, and session duration"
 ],
 "correctAnswer": 2
}
```

**Explanation:** The article says that before adding architectural complexity, you should check whether the current hardware is actually hitting limits. For write-heavy systems, the key vertical-scaling bottlenecks are disk I/O, CPU, and network bandwidth.

## 3. [MID_LEVEL · RANKING] In the live-comments hierarchical aggregation example, likes are aggregated on the way in and fanned out on the way out. Order these stages by the sequence an incoming like event flows through, from the stage that receives it first to the stage that delivers the result last.

```json
{
 "items": [
  "Root processor (merges batched updates from all its upstream nodes)",
  "Write processor (owns a subset of comments and batches their likes over a time window)",
  "Recipient viewer (sees the updated like count)",
  "Broadcast node (forwards updates to the viewers assigned to it)"
 ],
 "correctOrder": [
  1,
  0,
  3,
  2
 ]
}
```

**Explanation:** An incoming like is first routed to the write processor that owns its comment (chosen by comment ID), which aggregates likes over a window. It forwards one batch of updates to the root processor, which only needs to merge batches instead of handling every raw event. The merged updates then flow out to broadcast nodes, which each forward them to their assigned viewers, so the root writes to M broadcast nodes rather than N viewers.

## 4. [MID_LEVEL · MULTIPLE_CHOICE] In the social media post example, why would you separate post_content, post_metrics, and post_analytics into different tables?

```json
{
 "options": [
  "To save storage space by reducing column duplication across tables",
  "Each has different access patterns and scaling needs",
  "To improve security through table-level access controls and row isolation",
  "To reduce code complexity"
 ],
 "correctAnswer": 1
}
```

**Explanation:** Post content is write-once/read-many, post metrics have high-frequency writes, and post analytics are append-only time-series. Each can be optimized for its specific access pattern.

## 5. [MID_LEVEL · TRUE_FALSE] A queue in front of your database lets you keep up indefinitely even when your sustained write rate is higher than what the database can handle.

```json
{
 "correctAnswer": false
}
```

**Explanation:** Queues absorb short-lived bursts -- they smooth spikes by buffering writes and draining them when load drops. But if your sustained write rate exceeds the database's capacity, the queue just grows without bound until it runs out of space. Beating a sustained overload requires more write capacity (e.g., sharding), not a buffer.

## 6. [MID_LEVEL · MULTIPLE_CHOICE] How do you handle a 'hot key' that's too popular for even a single shard?

```json
{
 "options": [
  "Add more indexes to distribute write load across B-tree structures",
  "Use a faster database",
  "Split the key into sub-keys",
  "Implement caching"
 ],
 "correctAnswer": 2
}
```

**Explanation:** For viral content causing hot keys, you can split the key into multiple sub-keys (like post1Likes-0, post1Likes-1, etc.) to distribute the write load across multiple shards.

## 7. [MID_LEVEL · TRUE_FALSE] Sharding by user's country spreads write load evenly across shards for a global application.

```json
{
 "correctAnswer": false
}
```

**Explanation:** Country populations vary enormously, so a country-based shard key concentrates writes on a few shards (think China or India) while others sit nearly idle, creating hot spots. Even write distribution usually comes from hashing a high-cardinality key like userId. Country-based partitioning can still be the right call for data-residency or legal-compliance reasons, but that's a different goal from balancing write load.

## 8. [MID_LEVEL · MULTIPLE_CHOICE] You're sharding a database because write throughput has become the bottleneck. What should primarily drive your choice of partition key?

```json
{
 "options": [
  "Keeping the total number of shards as small as possible",
  "Spreading writes as evenly as possible so no single shard becomes a hot spot",
  "Co-locating related entities so you never need a cross-shard query",
  "Making individual queries as fast as possible"
 ],
 "correctAnswer": 1
}
```

**Explanation:** When writes are the bottleneck, the partition key's primary job is to minimize variance in writes per shard -- 'flat is good' -- so no single shard becomes a hot spot. Hashing a high-cardinality identifier like userId achieves this well. Data locality and query speed are real concerns in any sharding design, but they're secondary when the specific reason you're sharding is that writes have hit a ceiling.

## 9. [MID_LEVEL · MULTIPLE_CHOICE] You have 10,000 writes/second hitting a single database that can only handle 2,000 writes/second. Which approach works?

```json
{
 "options": [
  "Add a queue to buffer writes",
  "Shard across 5+ databases",
  "Add read replicas",
  "Increase connection pool size"
 ],
 "correctAnswer": 1
}
```

**Explanation:** When your sustained write rate exceeds database capacity, you need more write capacity. Sharding across 5+ databases gives you 10,000+ writes/sec total. Queues only help with temporary bursts, read replicas don't help writes, and connection pools don't increase write throughput.

## 10. [MID_LEVEL · MULTIPLE_CHOICE] When might load shedding be preferable to queuing for handling write bursts?

```json
{
 "options": [
  "When you need perfect consistency across all replicas",
  "When writes are frequently updated (like location updates)",
  "When writes are irreversible",
  "When you have unlimited storage"
 ],
 "correctAnswer": 1
}
```

**Explanation:** For frequently updated data like location reports, dropping older writes makes sense since newer writes will arrive shortly. This is better than queuing outdated location data.

## 11. [SENIOR · TRUE_FALSE] If a single-node system is handling 100,000 writes/sec with 2 KB payloads, the raw payload bandwidth is roughly 200 MB/sec, so a 10 Gbit/sec network interface is not the first bottleneck indicated by that estimate.

```json
{
 "correctAnswer": true
}
```

**Explanation:** 100,000 × 2 KB is about 200 MB/sec, which is well below the roughly 1.25 GB/sec raw capacity of a 10 Gbit/sec link before overheads. The point is not that vertical scaling solves everything, but that senior candidates should quantify CPU, disk, and network limits before adding distributed-system complexity.

## 12. [SENIOR · MULTIPLE_CHOICE] Clients send writes to a queue that accepts every write as it arrives. A consumer drains the queue into a database that can persist at most 5,000 writes/sec. Traffic spikes to 20,000 writes/sec for 60 seconds, then drops to 2,000 writes/sec. With no load shedding and an empty queue at the start, how large does the backlog get, and how long after the spike ends does it take to clear?

```json
{
 "options": [
  "300,000 writes, cleared about 60 seconds after the spike ends.",
  "No backlog forms, because the queue accepts writes as fast as they arrive.",
  "900,000 writes, cleared about 300 seconds after the spike ends.",
  "1,200,000 writes, cleared about 240 seconds after the spike ends."
 ],
 "correctAnswer": 2
}
```

**Explanation:** The database, not the queue, is the bottleneck: during the spike, writes arrive 15,000/sec faster than the database persists them, so 60 seconds builds a 900,000-write backlog. After the spike, the database still persists 5,000/sec while 2,000/sec keep arriving, so the backlog shrinks at 3,000/sec and clears in about 300 seconds. Writes accepted at the end of the spike are not in the database for roughly five minutes, so the requirements must tolerate that delay before a queue is the right fix.

## 13. [SENIOR · TRUE_FALSE] For a write-heavy workload, choosing a database such as Cassandra can improve ingest throughput while making some read paths slower, so it may be reasonable to use different storage choices for different parts of the system.

```json
{
 "correctAnswer": true
}
```

**Explanation:** The article emphasizes that Cassandra’s append-only write path trades read efficiency for write throughput. Senior designs should identify whether reads or writes are the bottleneck and avoid forcing one storage model onto workloads with different access patterns.

## 14. [SENIOR · MULTIPLE_CHOICE] A relational table is on the critical write path for an event-ingestion system. It has several secondary indexes and a full-text index used only by rare admin searches, while sustained write throughput is the bottleneck. Which change best matches the article's write-scaling guidance?

```json
{
 "options": [
  "Remove expensive indexes from the hot write table and serve rare searches from a separate asynchronous/read-optimized path if needed.",
  "Add more indexes so inserts can locate existing rows faster.",
  "Keep all indexes but put a queue in front of the database; this eliminates the write cost of index maintenance.",
  "Shard by the admin search field because that is the field most queries use."
 ],
 "correctAnswer": 0
}
```

**Explanation:** The article notes that secondary indexes, full-text indexing, triggers, and constraints can add significant write overhead because each write must update more structures. Removing them from the hot path improves write throughput, but it deliberately trades off read/query convenience, often requiring a separate projection or analytics store.

## 15. [SENIOR · MULTIPLE_CHOICE] You are evaluating whether vertical scaling is still plausible before sharding. The workload is 100,000 writes/sec, each write payload is about 2 KB before protocol overhead, and the candidate machine has a 10 Gbit/sec network interface. What is the best conclusion from this back-of-the-envelope check?

```json
{
 "options": [
  "The network is definitely the bottleneck because 100,000 writes/sec is too high for one machine.",
  "Raw network bandwidth alone does not rule out one machine; the payload is roughly 1.6 Gbit/sec, so disk I/O, CPU, indexes, and durability costs still need checking.",
  "The workload is guaranteed to fit because 1.6 Gbit/sec is below 10 Gbit/sec.",
  "Sharding is mandatory because write throughput scales only by adding shards, not by using larger hardware."
 ],
 "correctAnswer": 1
}
```

**Explanation:** 100,000 × 2 KB/sec is about 200 MB/sec, or roughly 1.6 Gbit/sec before overhead, which is below a 10 Gbit/sec NIC. The article emphasizes doing this kind of capacity math before adding distributed-system complexity, but passing the network check does not prove CPU, disk, WAL, or index updates can keep up.
