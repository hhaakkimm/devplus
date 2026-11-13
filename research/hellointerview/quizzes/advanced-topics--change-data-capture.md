# Change Data Capture Quiz

## 1. [JUNIOR · TRUE_FALSE] CDC captures changes by reading the log a database already maintains for crash recovery and replication, rather than requiring the application to write to each downstream system.

```json
{
 "correctAnswer": true
}
```

**Explanation:** Databases like Postgres and MySQL write every change to an ordered log (the WAL or binary log) before it lands in the data files. CDC reads from that existing mechanism, so the application keeps writing to a single database and downstream consumers receive changes without any extra write path in application code.

## 2. [JUNIOR · MULTIPLE_CHOICE] Which pattern records a business event by inserting an event row in the same database transaction as the state change it describes?

```json
{
 "options": [
  "Dual writing",
  "Polling",
  "The transactional outbox",
  "Log compaction"
 ],
 "correctAnswer": 2
}
```

**Explanation:** The transactional outbox inserts an event row (like OrderShipped) in the same transaction that updates the business data. Either both rows commit or neither does, so the event exists exactly when the business change actually happened. A relay then publishes those events downstream.

## 3. [MID_LEVEL · TRUE_FALSE] If a search index built from Postgres via CDC becomes corrupted, the standard recovery is to drop it, rebuild it from Postgres, and resume processing new changes.

```json
{
 "correctAnswer": true
}
```

**Explanation:** The index is a derived copy, meaning nothing lives there that doesn't live in the source first. That's what makes recovery straightforward: rebuild from the system of record and continue streaming. This rebuildability is one of the three properties shared by all the good CDC use cases.

## 4. [MID_LEVEL · MULTIPLE_CHOICE] An engineer watches the users table with CDC and runs account-cleanup work whenever a DELETE appears. Beyond the intent problem, what extra burden does this design take on?

```json
{
 "options": [
  "Kafka is unable to deliver DELETE records durably",
  "CDC connectors skip deletes when reading the Postgres WAL",
  "The database log grows faster once deletes are being captured",
  "The consumer ends up owning job state, retries, backoff, and delayed execution, effectively rebuilding a job system"
 ],
 "correctAnswer": 3
}
```

**Explanation:** Kafka can deliver CDC records durably and consumers can add retries, but background work needs more than delivery. Once the consumer owns job state, failure handling, and scheduling, it has built a job system around an implicit row change. Enqueueing a durable job or starting a workflow directly represents the work explicitly.

## 5. [MID_LEVEL · MULTIPLE_CHOICE] Which of the following is NOT one of the properties shared by the good CDC use cases in the article?

```json
{
 "options": [
  "The source stays authoritative while CDC runs",
  "Some staleness in the downstream system is acceptable",
  "The downstream system can be rebuilt or repaired from the source",
  "Each downstream consumer confirms the change before the original write completes"
 ],
 "correctAnswer": 3
}
```

**Explanation:** CDC is asynchronous by nature: the original write completes without waiting for any consumer, and downstream systems lag slightly behind. The three shared properties are an authoritative source, tolerance for some staleness, and a downstream target that can be reconstructed from the source if something goes wrong.

## 6. [MID_LEVEL · MATCHING_PAIRS] Match each downstream need to the mechanism the article recommends:

```json
{
 "leftItems": [
  "Keeping a search index current with the product catalog",
  "Sending an email when an order ships",
  "Serving user profiles where a minute of staleness is acceptable",
  "Releasing inventory 30 minutes after a reservation is created"
 ],
 "rightItems": [
  "A short cache TTL",
  "A durable job or workflow engine",
  "CDC",
  "A transactional outbox event"
 ],
 "correctPairs": [
  2,
  3,
  0,
  1
 ]
}
```

**Explanation:** The search index is a derived copy of state, which is exactly what CDC is for. Shipping an email is a business event, so the application should record it explicitly via an outbox. A slightly stale cache can simply age out through a TTL, and delayed work with timers belongs in a job or workflow system like Temporal.

## 7. [MID_LEVEL · TRUE_FALSE] Compared to periodic batch copies, CDC reduces load on a production database feeding a warehouse because it streams only the changes since its last processed position instead of repeatedly scanning the source tables.

```json
{
 "correctAnswer": true
}
```

**Explanation:** Batch jobs re-read large portions of the database on every run, competing with application traffic for resources, and the warehouse is only as fresh as the last completed batch. CDC reads the replication log the database already maintains and continuously captures just the new inserts, updates, and deletes.

## 8. [MID_LEVEL · RANKING] Rank the steps of a zero-downtime database migration using CDC in the order they occur:

```json
{
 "items": [
  "Backfill existing data into the new database",
  "Start CDC on the old database",
  "Apply captured changes until the new database catches up",
  "Move reads to the new database",
  "Move writes to the new database"
 ],
 "correctOrder": [
  1,
  0,
  2,
  3,
  4
 ]
}
```

**Explanation:** CDC starts first so that changes made during the backfill aren't lost. Once the backfill finishes, the captured changes are applied until the new database catches up, and only then do reads and eventually writes move over. The application writes to one database the whole way through and never knows the migration is happening.

## 9. [MID_LEVEL · TRUE_FALSE] The article recommends routing cache invalidation through CDC because the application that changed the row usually cannot tell which cache entry became stale.

```json
{
 "correctAnswer": false
}
```

**Explanation:** The opposite is true. The application that performed the write already has the user ID in hand, in the same request and code path, so invalidating the key directly is simple and immediate. Routing that through a connector, topic, and consumer just rediscovers something the writer already knew.

## 10. [MID_LEVEL · MULTIPLE_CHOICE] Why is having the application write to both Postgres and Elasticsearch on every product change considered fragile?

```json
{
 "options": [
  "One write can succeed while the other fails, leaving the two systems out of sync",
  "Elasticsearch rejects writes that originate from application code",
  "Postgres transactions block until Elasticsearch acknowledges the write",
  "The two systems store data in incompatible formats"
 ],
 "correctAnswer": 0
}
```

**Explanation:** The two writes are not atomic, so a failure or crash between them leaves the systems inconsistent. Patching this requires retry logic, idempotency, and crash recovery in the application. CDC sidesteps the problem entirely because the application commits once and the change propagates from the database's own log.

## 11. [SENIOR · MULTIPLE_CHOICE] A reservation must release inventory 30 minutes after creation. Even with durable Kafka delivery and consumer retries, why does the article steer this away from CDC?

```json
{
 "options": [
  "Kafka cannot retain records for a full 30 minutes",
  "CDC records for inserts exclude the reservation's creation timestamp",
  "A timer must be persisted, recovered after crashes, and eventually fired, and neither CDC nor Kafka manages that state",
  "Postgres is unable to capture inserts on reservation tables"
 ],
 "correctAnswer": 2
}
```

**Explanation:** CDC can tell you the reservation was inserted, but the delayed work still needs a timer that survives crashes and reliably fires later. Kafka's durability doesn't change where that timer lives. A durable job queue or a workflow engine like Temporal represents the scheduled work directly instead of forcing a consumer to reinvent it.

## 12. [SENIOR · MULTIPLE_CHOICE] A repair script re-applies a SHIPPED status that was already set correctly months ago, and the email consumer deduplicates CDC records. Why does the customer still get a second email?

```json
{
 "options": [
  "Kafka delivers every record at least twice by design",
  "The two writes sit at different positions in the log, so the database sees them as distinct changes with nothing for a dedup key to match",
  "CDC records omit the before image, so the consumer cannot compare states",
  "The repair script bypasses the WAL entirely"
 ],
 "correctAnswer": 1
}
```

**Explanation:** Deduplication works when the same record arrives twice, but these are two different writes at two different log positions. What's missing is a durable business-level fact, an OrderShipped event with its own event ID, which is exactly what the transactional outbox provides and what makes downstream dedup possible.

## 13. [SENIOR · MULTIPLE_CHOICE] Why is a duplicated change record harmless to the Elasticsearch consumer but harmful to the email consumer?

```json
{
 "options": [
  "Elasticsearch silently rejects duplicate documents while mail servers accept them",
  "Re-applying the same state to the index produces the same final result, while sending the email again repeats a side effect the customer sees",
  "The search consumer batches updates, so duplicates collapse into one write",
  "Email payloads are larger and overflow the consumer's buffers"
 ],
 "correctAnswer": 1
}
```

**Explanation:** Writing the same document state to a search index twice converges on the same result, so state-propagating consumers tolerate duplicates naturally. Side effects like emails, charges, or shipments happen again on every delivery. That asymmetry is why derived-copy consumers fit CDC while side-effecting consumers need explicit events with dedup keys.

## 14. [SENIOR · TRUE_FALSE] Because the outbox row commits in the same transaction as the order update, downstream consumers are guaranteed to receive each event exactly once.

```json
{
 "correctAnswer": false
}
```

**Explanation:** The shared transaction guarantees the event exists exactly when the business change committed, but it says nothing about delivery. The relay publishing outbox rows can still deliver an event more than once, which is why each row carries a stable event_id that consumers use to deduplicate.

## 15. [SENIOR · MULTIPLE_CHOICE] An engineer proposes triggering shipping emails from CDC on orders.status and handling migrations by filtering them out in the consumer. What is the core flaw in this plan?

```json
{
 "options": [
  "The reason for the write was never recorded in the log, so no consumer-side filter can recover it",
  "Kafka consumers cannot inspect the before image needed for filtering",
  "Filtering adds more latency than an email pipeline can tolerate",
  "The consumer would need direct write access to the production database"
 ],
 "correctAnswer": 0
}
```

**Explanation:** The application knew whether it was shipping an order or repairing data at the moment it wrote, but nothing about the write records which one it was. By the time CDC reads the log, all that's left is a column that changed. A filter can only work with information that made it into the log, and intent never did.
