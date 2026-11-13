# Apache Flink System Design Quiz

## 1. [JUNIOR · MULTIPLE_CHOICE] In Flink's cluster architecture, what is the primary role of the Job Manager?

```json
{
 "options": [
  "Execute data processing tasks across distributed worker slots",
  "Coordinate scheduling, checkpoints, and failures",
  "Store application state",
  "Manage network connections"
 ],
 "correctAnswer": 1
}
```

**Explanation:** The Job Manager serves as the coordinator of the Flink cluster, responsible for scheduling tasks, coordinating checkpoints, handling failures, and managing the overall execution of jobs.

## 2. [JUNIOR · MULTIPLE_CHOICE] What is the purpose of watermarks in Flink?

```json
{
 "options": [
  "To compress data streams for lower overhead",
  "To handle out-of-order and late-arriving events",
  "To encrypt streaming data",
  "To balance load across task managers"
 ],
 "correctAnswer": 1
}
```

**Explanation:** Watermarks are timestamps that flow through the system declaring 'all events with timestamps before this watermark have arrived,' enabling Flink to handle out-of-order events and decide when to trigger window computations.

## 3. [MID_LEVEL · TRUE_FALSE] Flink's exactly-once guarantees automatically extend to all external systems like databases and APIs.

```json
{
 "correctAnswer": false
}
```

**Explanation:** Flink guarantees exactly-once semantics for internal state operations, but external systems may still see duplicate writes during failure recovery. You need idempotent operations or transactional behavior for end-to-end exactly-once processing.

## 4. [MID_LEVEL · TRUE_FALSE] Flink's checkpointing mechanism enables exactly-once processing guarantees even when task failures occur.

```json
{
 "correctAnswer": true
}
```

**Explanation:** Flink uses checkpointing based on the Chandy-Lamport algorithm to create consistent snapshots of the entire job state, allowing recovery to the exact point before failure occurred.

## 5. [MID_LEVEL · MULTIPLE_CHOICE] A team wants to generate a daily click analytics report, and stakeholders are fine receiving it several hours later. Based on the article, what is the best reason to prefer a batch system like Spark over Flink for this case?

```json
{
 "options": [
  "Spark provides stronger exactly-once guarantees than Flink for all sinks.",
  "If real-time latency is not needed, batch processing can avoid the operational complexity of stream processing.",
  "Flink cannot read from Kafka topics when data volume is high.",
  "Batch systems handle out-of-order events by using watermarks."
 ],
 "correctAnswer": 1
}
```

**Explanation:** The article emphasizes asking whether real-time latency is actually required before choosing stream processing. If the business can tolerate delayed results, a batch approach may be simpler and cheaper to operate than a Flink streaming pipeline.

## 6. [MID_LEVEL · TRUE_FALSE] A design that relies on replaying intermediate Flink streams by offset is treating those streams like Kafka logs, which is not the right abstraction according to the article.

```json
{
 "correctAnswer": true
}
```

**Explanation:** The article notes that Flink streams are not necessarily append-only logs and do not have Kafka-like offsets or persistence expectations. Flink handles durability through checkpoints, so replay and recovery should be reasoned about through checkpointed state rather than intermediate stream offsets.

## 7. [MID_LEVEL · TRUE_FALSE] When a Flink task fails, only the failed task needs to be restarted while other tasks continue processing.

```json
{
 "correctAnswer": false
}
```

**Explanation:** When a failure occurs, Flink stops the entire job, restores from the latest checkpoint, and restarts all tasks to maintain exactly-once processing guarantees and consistent state.

## 8. [MID_LEVEL · MULTIPLE_CHOICE] What happens to Kafka consumer offsets during Flink's failure recovery process?

```json
{
 "options": [
  "They continue from the last committed offset in the consumer group",
  "They are reset to the beginning",
  "They rewind to the checkpoint position",
  "They are randomly assigned"
 ],
 "correctAnswer": 2
}
```

**Explanation:** During recovery, Flink sources rewind to their checkpoint positions. For Kafka consumers, this means going back to the offset stored in the checkpoint to ensure exactly-once processing.

## 9. [MID_LEVEL · MULTIPLE_CHOICE] In a Flink job that computes 5-minute click counts per advertisement, why would you apply `keyBy(event -> event.getAdId())` before the windowed aggregation?

```json
{
 "options": [
  "To persist the raw click stream like a Kafka topic.",
  "To guarantee that late events are dropped before aggregation.",
  "To partition the stream so each advertisement's windowed count is computed independently.",
  "To convert the stream into a batch dataset."
 ],
 "correctAnswer": 2
}
```

**Explanation:** `keyBy` groups the stream logically by a key, such as `adId`, so stateful operations like windows and reductions are maintained per key. Without keying, the aggregation would not naturally produce separate counts for each advertisement.

## 10. [MID_LEVEL · MULTIPLE_CHOICE] Which windowing strategy would be best for detecting user activity patterns where you want overlapping 10-minute windows updated every 2 minutes?

```json
{
 "options": [
  "Tumbling windows of 10 minutes",
  "Sliding windows, 10-min size, 2-min slide",
  "Session windows with a 10-minute inactivity timeout gap",
  "Global windows with custom triggers"
 ],
 "correctAnswer": 1
}
```

**Explanation:** Sliding windows with a 10-minute window size and 2-minute slide interval create overlapping windows that update every 2 minutes, perfect for detecting patterns that require temporal overlap.

## 11. [SENIOR · MULTIPLE_CHOICE] A team wants to compute click metrics for a dashboard that is refreshed once per day. Events already land in Kafka, and there is no user-facing need for minute-level freshness. According to the article’s guidance, what is the best design judgment?

```json
{
 "options": [
  "Use Flink anyway because Kafka sources imply the problem is stream processing.",
  "Prefer a batch-oriented solution such as Spark unless real-time latency is actually required.",
  "Use Flink only if the source is changed from Kafka to a file system.",
  "Implement the aggregation in a custom service with in-memory counters to avoid Flink overhead."
 ],
 "correctAnswer": 1
}
```

**Explanation:** The article explicitly warns that stream processing is hard and operationally expensive, so teams should first ask whether real-time latency is truly needed. If daily freshness is acceptable, batch processing is usually simpler and avoids unnecessary Flink operational complexity.

## 12. [SENIOR · MULTIPLE_CHOICE] An engineer argues that because a Flink stream is like a Kafka topic, downstream operators can rely on it as a durable append-only log and replay it later using offsets. Which correction is grounded in the article?

```json
{
 "options": [
  "Flink streams are edges in the dataflow graph, not persistent logs with offsets; durability is provided through checkpoints.",
  "Flink streams are durable only when the upstream source is Kafka, because Kafka offsets are copied to every stream edge.",
  "Flink streams persist data by default, but only for operators that use tumbling event-time windows.",
  "Flink streams provide replayable offsets, but only sinks are allowed to seek them."
 ],
 "correctAnswer": 0
}
```

**Explanation:** The article warns that Flink streams are not necessarily append-only logs like Kafka and have no offset or persistence expectation. Flink’s durability model is based on checkpoints, not treating each internal stream edge as a replayable log.

## 13. [SENIOR · TRUE_FALSE] A Flink design that reads clicks from Kafka, performs only a trivial stateless reformatting, and writes to a database is less compelling than one involving windows, joins, late events, or other stateful logic, because the operational cost of stream processing is harder to justify when there is little state-management benefit.

```json
{
 "correctAnswer": true
}
```

**Explanation:** The article presents simple Kafka-to-database transformation as the easy case, then motivates Flink when state, scaling, fault tolerance, and out-of-order events make the problem harder. Senior design judgment is to avoid adding a heavy stream processor unless its abstractions solve real complexity in the problem.

## 14. [SENIOR · TRUE_FALSE] For a per-user click-counting operator, using Flink-managed ValueState is not sufficient by itself to make the counts scalable and correct; the stream also needs to be partitioned by the same key, such as userId, so each key’s state is colocated with the records that update it.

```json
{
 "correctAnswer": true
}
```

**Explanation:** Flink state is scoped per key for keyed operators, and the article’s examples use keyBy before applying keyed/windowed aggregation. If records for the same user were not routed consistently to the same keyed state partition, scaling the job would create correctness and redistribution problems similar to the hand-rolled in-memory service the article warns about.

## 15. [SENIOR · MULTIPLE_CHOICE] A Flink job computes per-user click counts, but the operator stores counts in a normal in-memory HashMap field instead of Flink-managed ValueState/ListState/etc. What is the key failure mode?

```json
{
 "options": [
  "The job cannot read from Kafka because sources require ValueState.",
  "The operator will automatically become stateless and emit only raw events.",
  "Flink will not know about that state, so checkpoint restore and rescaling will not reliably preserve or redistribute it.",
  "Watermarks will stop advancing because all keyed state must be event-time state."
 ],
 "correctAnswer": 2
}
```

**Explanation:** The article emphasizes that state must be managed internally by Flink so the framework can provide scaling and fault tolerance guarantees. Ordinary in-memory state may work until a crash or rescale, but Flink cannot checkpoint and restore it as part of the job’s managed state.
