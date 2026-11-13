# Distributed Cache System Design Quiz

## 1. [JUNIOR · MULTIPLE_CHOICE] What does write batching accomplish in high-throughput systems?

```json
{
 "options": [
  "Improves read consistency across distributed replicas",
  "Reduces per-operation overhead",
  "Eliminates network partitions",
  "Guarantees atomic operations"
 ],
 "correctAnswer": 1
}
```

**Explanation:** Write batching combines multiple operations into single requests, reducing per-operation network overhead, connection usage, and processing costs. This technique significantly improves throughput for systems handling many small operations, though it may slightly increase latency.

## 2. [JUNIOR · TRUE_FALSE] Connection pooling reduces network latency by eliminating connection establishment overhead.

```json
{
 "correctAnswer": true
}
```

**Explanation:** Connection pooling maintains persistent connections between clients and servers, eliminating the TCP handshake overhead for each request. This reduces both average latency and tail latencies, especially important for high-frequency operations typical in distributed caches.

## 3. [MID_LEVEL · MULTIPLE_CHOICE] A key was set with a 60-second TTL, but the background cleanup process has not run yet. If a client calls get on that key after 90 seconds, what should the cache do in the design from the article?

```json
{
 "options": [
  "Return the value because only the cleanup process removes expired keys",
  "Check the expiry timestamp, delete the key, and return null",
  "Refresh the TTL automatically and return the value",
  "Reject the request until the cleanup process finishes"
 ],
 "correctAnswer": 1
}
```

**Explanation:** The article’s TTL design stores an expiry timestamp with each value and checks it during get operations. The background janitor is an optimization for removing expired entries that are never accessed, not the only mechanism enforcing expiration.

## 4. [MID_LEVEL · MULTIPLE_CHOICE] What happens when a cache node fails in an asynchronously replicated system?

```json
{
 "options": [
  "All writes immediately fail across every partition",
  "Recent writes may be lost but reads continue",
  "System becomes strongly consistent across all replicas automatically",
  "All nodes must restart"
 ],
 "correctAnswer": 1
}
```

**Explanation:** In asynchronous replication, recent writes that haven't propagated to replicas are lost when the primary fails. However, reads can continue from replicas, maintaining availability. This trade-off prioritizes system availability over perfect data durability.

## 5. [MID_LEVEL · MULTIPLE_CHOICE] An interviewer asks you to design cache eviction but does not specify an eviction policy. According to the article, what is the best next step before committing to LRU?

```json
{
 "options": [
  "Implement FIFO because it is simpler than LRU",
  "Avoid eviction and rely only on TTL expiration",
  "Clarify whether LRU is required or if another policy should be supported",
  "Use LFU because it handles hot keys better"
 ],
 "correctAnswer": 2
}
```

**Explanation:** The article uses LRU for its design, but explicitly notes that interviewers may expect a different or configurable eviction policy. Clarifying the requirement avoids optimizing for the wrong behavior.

## 6. [MID_LEVEL · MULTIPLE_CHOICE] For a viral content key receiving millions of reads per second, which strategy provides the most effective load distribution?

```json
{
 "options": [
  "Vertical scaling of the primary node",
  "Creating multiple copies with random suffix selection",
  "Implementing write-through caching with synchronous propagation",
  "Using stronger consistency guarantees"
 ],
 "correctAnswer": 1
}
```

**Explanation:** Creating multiple copies of hot keys with randomized access distributes read load across many nodes efficiently. Clients randomly select from available copies, spreading millions of requests across the cluster rather than overwhelming a single node with all traffic.

## 7. [MID_LEVEL · MULTIPLE_CHOICE] When should background cleanup processes run to optimize system performance?

```json
{
 "options": [
  "During peak traffic hours",
  "During low-traffic periods or based on memory pressure",
  "Only when the cache is completely full",
  "Continuously at maximum frequency"
 ],
 "correctAnswer": 1
}
```

**Explanation:** Background cleanup should run during low-traffic periods to avoid competing with user requests for CPU and memory resources. It can also be triggered by memory pressure thresholds, balancing cleanup efficiency with system responsiveness to user traffic.

## 8. [MID_LEVEL · MULTIPLE_CHOICE] Which approach BEST handles hot keys receiving excessive read traffic?

```json
{
 "options": [
  "Increase hardware capacity on all nodes uniformly",
  "Create copies of hot keys across nodes",
  "Switch to synchronous replication",
  "Implement stronger consistency"
 ],
 "correctAnswer": 1
}
```

**Explanation:** Creating copies of hot keys distributes read load across multiple nodes without the overhead of replicating entire datasets. This targeted approach scales read capacity for specific keys while minimizing resource waste and operational complexity.

## 9. [MID_LEVEL · MULTIPLE_CHOICE] When prioritizing availability over consistency in distributed caches, which replication approach works best?

```json
{
 "options": [
  "Synchronous replication to all replicas",
  "Asynchronous replication from primary",
  "No replication for simplicity",
  "Consensus-based replication"
 ],
 "correctAnswer": 1
}
```

**Explanation:** Asynchronous replication allows writes to complete immediately on the primary without waiting for replica acknowledgment, maximizing availability. While this introduces temporary inconsistency, it aligns with typical cache requirements where availability matters more than perfect consistency.

## 10. [MID_LEVEL · MULTIPLE_CHOICE] Which approach BEST handles scaling distributed cache storage to multiple terabytes?

```json
{
 "options": [
  "Single large-memory nodes with maximum RAM capacity",
  "Horizontal sharding across nodes",
  "Vertical scaling with SSDs",
  "In-memory compression only"
 ],
 "correctAnswer": 1
}
```

**Explanation:** Horizontal sharding distributes data across many commodity nodes, providing cost-effective scaling and fault isolation. This approach allows systems to grow beyond single-node memory limits while maintaining performance through parallel processing and load distribution.

## 11. [SENIOR · MULTIPLE_CHOICE] A primary cache node accepts `set(K, V, ttl=60)` at time t=100s, but asynchronous replication delivers the write to a replica at t=130s. To preserve the intended expiration semantics, what should the primary replicate?

```json
{
 "options": [
  "The original relative TTL of 60 seconds, letting the replica expire it at t=190s",
  "An absolute expiry timestamp of t=160s, or an adjusted remaining TTL of 30 seconds",
  "Only the value; replicas should not enforce TTLs in an eventually consistent cache",
  "A background-cleanup instruction scheduled 60 seconds after the replica receives the write"
 ],
 "correctAnswer": 1
}
```

**Explanation:** The article’s TTL design stores an expiry timestamp, not just a value. Replicating the original relative TTL after a delay would extend the key’s lifetime on lagging replicas and serve stale data longer than intended.

## 12. [SENIOR · MULTIPLE_CHOICE] In an LRU cache implemented with a hash map from key to linked-list node, TTLs are checked on `get`. If `get(X)` finds that X has expired, which behavior is required to avoid corrupting future capacity and eviction behavior?

```json
{
 "options": [
  "Return null but leave X in the linked list until it naturally reaches the LRU tail",
  "Move X to the most-recently-used position, because it was just accessed",
  "Delete X from the hash map only; the linked list can be cleaned up lazily later",
  "Remove X from both the hash map and the linked list, then return null"
 ],
 "correctAnswer": 3
}
```

**Explanation:** The hash map and doubly linked list together represent one cache entry, so they must stay consistent. Leaving an expired node in either structure can make the cache think it is fuller than it is or cause later evictions to operate on stale nodes.

## 13. [SENIOR · TRUE_FALSE] At 100k requests per second with a 10ms latency target, a single worker that performs one blocking 10ms cache operation at a time could satisfy the throughput requirement because each individual operation meets the latency budget.

```json
{
 "correctAnswer": false
}
```

**Explanation:** Latency per request and total throughput are different constraints. A worker doing one blocking 10ms operation at a time can handle roughly 100 requests per second, while 100k requests per second at 10ms implies about 1,000 concurrent in-flight operations by Little’s Law.

## 14. [SENIOR · TRUE_FALSE] In a partitioned distributed cache where each key is stored only on its assigned shard or replicas, a round-robin load balancer directly in front of cache nodes is sufficient if each node simply checks its local hash table.

```json
{
 "correctAnswer": false
}
```

**Explanation:** Partitioning requires key-aware routing: the client, load balancer, or proxy must send a request to the node responsible for that key, or to one of its replicas. Round-robin routing can send a valid get to a node that does not own the key, producing false cache misses and unnecessary load.

## 15. [SENIOR · MULTIPLE_CHOICE] The cache must store 1TB of logical data and be highly available using 2x replication. If each node can safely dedicate 64GB of memory to cached values after reserving overhead, what is the minimum node count, ignoring metadata and imbalance?

```json
{
 "options": [
  "16 nodes",
  "24 nodes",
  "32 nodes",
  "64 nodes"
 ],
 "correctAnswer": 2
}
```

**Explanation:** With 2x replication, the cluster must hold about 2TB of physical cached data. Using 1TB = 1024GB, that is 2048GB / 64GB = 32 nodes before accounting for metadata, safety margin, or uneven shard distribution.
