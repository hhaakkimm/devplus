# Apache Cassandra

## 1. [JUNIOR · TRUE_FALSE] In Cassandra's consistent-hashing scheme, assigning multiple virtual nodes (vnodes) to each physical node can spread data more evenly across the cluster.

```json
{
 "correctAnswer": true
}
```

**Explanation:** True. Cassandra maps multiple virtual nodes (vnodes) on the ring to physical nodes. This distributes load more evenly across the cluster and allows different physical nodes to handle different numbers of vnodes based on their resources.

## 2. [JUNIOR · MULTIPLE_CHOICE] What does a partition key determine in Cassandra?

```json
{
 "options": [
  "The sorted order of rows within a table",
  "Which partition and node the row belongs to",
  "The replication strategy for the keyspace",
  "The consistency level for read operations against that partition"
 ],
 "correctAnswer": 1
}
```

**Explanation:** The partition key consists of one or more columns that determine what partition the row is in. This is crucial for data distribution across nodes in the cluster using consistent hashing.

## 3. [MID_LEVEL · MULTIPLE_CHOICE] For a production Cassandra cluster spanning multiple data centers, which replication strategy should you choose to improve resilience to data-center or rack-level failures?

```json
{
 "options": [
  "NetworkTopologyStrategy",
  "SimpleStrategy",
  "ModuloReplicationStrategy",
  "SingleRackStrategy"
 ],
 "correctAnswer": 0
}
```

**Explanation:** NetworkTopologyStrategy is recommended for production because it is aware of data centers and racks. That awareness lets Cassandra place replicas with physical separation, reducing the chance that one outage takes out many replicas.

## 4. [MID_LEVEL · TRUE_FALSE] In Cassandra CQL, `PRIMARY KEY (a, b, c)` treats `a` as the partition key and `b` and `c` as clustering keys.

```json
{
 "correctAnswer": true
}
```

**Explanation:** The article notes that `PRIMARY KEY (a, b, c)` is alternative syntax for `PRIMARY KEY ((a), b, c)`. That means rows are partitioned by `a`, while `b` and `c` control ordering within that partition.

## 5. [MID_LEVEL · TRUE_FALSE] If some Cassandra physical nodes have more resources than others, assigning them more vnodes can let them take responsibility for a larger share of the token ring.

```json
{
 "correctAnswer": true
}
```

**Explanation:** Vnodes are virtual positions on the consistent-hashing ring that are owned by physical nodes. The article explains that larger physical machines can own more vnodes, allowing the cluster to account for different node capacities.

## 6. [MID_LEVEL · MULTIPLE_CHOICE] Why did Discord modify their original Cassandra messages schema to include a 'bucket' in the partition key?

```json
{
 "options": [
  "To improve query performance for message searches across channel history",
  "To prevent large partitions from growing indefinitely",
  "To enable better compression of message data",
  "To support real-time message notifications"
 ],
 "correctAnswer": 1
}
```

**Explanation:** Discord added a 'bucket' (representing 10 days of data) to the partition key to solve large partition performance problems in busy channels and prevent partitions from growing monotonically. This ensured even very active channels would fit in a single partition over the bucket timeframe.

## 7. [MID_LEVEL · MULTIPLE_CHOICE] A Cassandra column is updated concurrently on different replicas with conflicting values. During reconciliation, which value will Cassandra keep?

```json
{
 "options": [
  "The value from the replica with the lowest token on the ring",
  "The value written by the coordinator node for the request",
  "The value with the most recent write timestamp",
  "The value stored on the majority of replicas before reconciliation"
 ],
 "correctAnswer": 2
}
```

**Explanation:** Cassandra stores timestamp metadata with each column and resolves write conflicts using a “last write wins” rule. This means the value with the newest timestamp is kept, which is not necessarily the value that arrived at a replica last in real time.

## 8. [MID_LEVEL · MULTIPLE_CHOICE] You are modeling an events table where queries always fetch all events for a user in chronological order. Which primary key design best uses Cassandra’s data model for this access pattern?

```json
{
 "options": [
  "Use event_time as the partition key so events are globally ordered by time.",
  "Use user_id as a clustering key and event_time as the partition key.",
  "Use user_id as the partition key and event_time as a clustering key.",
  "Use no clustering key because Cassandra automatically sorts rows by every column."
 ],
 "correctAnswer": 2
}
```

**Explanation:** The partition key determines where the data is stored, so user_id groups a user’s events together. The clustering key controls the sorted order of rows within that partition, making event_time appropriate for chronological reads.

## 9. [MID_LEVEL · TRUE_FALSE] Cassandra data modeling should be query-driven rather than entity-relationship-driven.

```json
{
 "correctAnswer": true
}
```

**Explanation:** True. Unlike relational databases that focus on normalized entity-relationship modeling, Cassandra data modeling is query-driven. You must consider access patterns first and design tables to support specific queries, often denormalizing data across tables.

## 10. [MID_LEVEL · MULTIPLE_CHOICE] When Cassandra selects replicas on the token ring, why does it skip vnodes that belong to a physical node already chosen for that replica set?

```json
{
 "options": [
  "To make reads always strongly consistent without requiring quorum.",
  "To ensure all replicas are stored in the same rack for faster communication.",
  "To prevent SSTables from being flushed too frequently on large machines.",
  "To avoid losing multiple replicas when a single physical node fails."
 ],
 "correctAnswer": 3
}
```

**Explanation:** Multiple vnodes can belong to the same physical machine. If Cassandra placed several replicas on vnodes owned by one machine, a single node failure could remove multiple copies of the same data.

## 11. [SENIOR · TRUE_FALSE] In a Cassandra table defined with PRIMARY KEY ((a, b), c), changing b for a logical record can change which partition/node owns it, whereas in PRIMARY KEY ((a), b, c), b affects ordering within the partition rather than partition placement.

```json
{
 "correctAnswer": true
}
```

**Explanation:** In the first schema, a and b together form the composite partition key, so both are hashed to choose the partition. In the second schema, only a is the partition key; b and c are clustering keys used to sort rows inside that partition.

## 12. [SENIOR · MULTIPLE_CHOICE] A keyspace uses SimpleStrategy with replication_factor = 3. A partition hashes to a vnode owned by physical node A, so A holds the first replica. Continuing clockwise around the ring, the next vnode owners are A, B, B, C, D. Applying Cassandra's replica selection rule from the article, which three physical nodes end up holding this partition's replicas?

```json
{
 "options": [
  "A, A, B",
  "A, B, D",
  "A, B, C",
  "B, C, D"
 ],
 "correctAnswer": 2
}
```

**Explanation:** The first replica is placed on the vnode the partition hashes to, owned by A. Cassandra skips vnodes on physical nodes already in the replica set, so it skips the next A, chooses B, skips the second B, then chooses C.

## 13. [SENIOR · MULTIPLE_CHOICE] Two replicas contain conflicting values for the same Cassandra column: value = 'paid' with timestamp 1000, and value = 'refunded' with timestamp 995. If the 'refunded' write actually happened later in real time but received the lower timestamp due to clock skew, what value survives reconciliation?

```json
{
 "options": [
  "'refunded', because the application issued it later in real time",
  "Both values, because Cassandra keeps conflicting versions for application-side resolution",
  "Neither value, because the read fails until replicas are manually repaired",
  "'paid', because Cassandra resolves column conflicts using last-write-wins by timestamp"
 ],
 "correctAnswer": 3
}
```

**Explanation:** The article notes that Cassandra stores timestamp metadata with columns and resolves conflicts using last-write-wins. That means timestamp ordering, not real-world intent, determines the surviving value, making clock skew an important failure mode.

## 14. [SENIOR · MULTIPLE_CHOICE] You are configuring a production Cassandra keyspace across two data centers and want 3 replicas in dc1 and 2 replicas in dc2, with placement aware of data centers and racks. Which replication configuration best matches that requirement?

```json
{
 "options": [
  "SimpleStrategy with replication_factor = 5",
  "NetworkTopologyStrategy with dc1: 3 and dc2: 2",
  "SimpleStrategy with dc1: 3 and dc2: 2",
  "NetworkTopologyStrategy with replication_factor = 5 only"
 ],
 "correctAnswer": 1
}
```

**Explanation:** NetworkTopologyStrategy is the production-oriented strategy because it is data-center and rack aware. SimpleStrategy only scans clockwise around the ring and is more appropriate for simple deployments or testing.

## 15. [SENIOR · TRUE_FALSE] For a production multi-datacenter Cassandra deployment, using SimpleStrategy with replication_factor = 5 provides the same datacenter and rack failure isolation as NetworkTopologyStrategy configured with 3 replicas in one datacenter and 2 in another.

```json
{
 "correctAnswer": false
}
```

**Explanation:** SimpleStrategy chooses replicas by scanning clockwise around the ring and is not datacenter- or rack-aware. NetworkTopologyStrategy is recommended for production because it deliberately places replicas across datacenters and racks to reduce correlated failure risk.
