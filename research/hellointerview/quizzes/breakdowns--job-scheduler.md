# Job Scheduler System Design Quiz

## 1. [JUNIOR · TRUE_FALSE] In the article, a Schedule represents when a job should be executed, such as a CRON expression or a specific DateTime.

```json
{
 "correctAnswer": true
}
```

**Explanation:** The article defines Schedule as a core entity that captures when a job should run. It can represent recurring schedules with CRON expressions or one-time schedules with a specific DateTime.

## 2. [JUNIOR · MATCHING_PAIRS] Match each job scheduler component to its primary purpose:

```json
{
 "leftItems": [
  "Jobs table",
  "Executions table",
  "Message queue with delay",
  "Visibility timeout"
 ],
 "rightItems": [
  "Tracks individual scheduled run instances",
  "Enables precise timing without polling",
  "Stores reusable job definitions",
  "Detects worker failures automatically"
 ],
 "correctPairs": [
  2,
  0,
  1,
  3
 ]
}
```

**Explanation:** The Jobs table stores job definitions (task, schedule, parameters). The Executions table tracks each run instance with status. The message queue with delay enables sub-second precision. Visibility timeouts detect failures when workers crash without deleting messages.

## 3. [MID_LEVEL · MULTIPLE_CHOICE] What does an SQS visibility timeout do after a worker receives a message?

```json
{
 "options": [
  "Deletes the message as soon as the worker receives it",
  "Hides it, then redelivers it if it is not deleted",
  "Checks whether the worker process is still alive",
  "Routes every retry back to the same worker instance"
 ],
 "correctAnswer": 1
}
```

**Explanation:** The timeout gives a worker time to process and delete a message before it becomes eligible for redelivery. Expiration is not proof of a crash, and standard queues can deliver duplicates, so processing should be idempotent.

## 4. [MID_LEVEL · MULTIPLE_CHOICE] A job scheduler queries the database every minute to find upcoming jobs, but these queries are consuming too many database resources. Which optimization works best?

```json
{
 "options": [
  "Query more frequently with smaller result sets",
  "Add more database connections",
  "Query a read replica instead of the primary",
  "Replace the database with a message queue"
 ],
 "correctAnswer": 2
}
```

**Explanation:** Read replicas can handle the periodic job sync queries without impacting the primary database that serves the main application. These queries are read-only (fetching jobs due soon), so they're perfect candidates for read replicas. This is a common pattern for batch-loading jobs into memory queues.

## 5. [MID_LEVEL · MULTIPLE_CHOICE] Which approach BEST handles scaling job processing to 10,000 jobs per second?

```json
{
 "options": [
  "Vertical scaling with larger database instances and more CPU cores",
  "Container-based worker pool with auto-scaling",
  "Single-threaded processing for consistency",
  "Manual worker deployment and monitoring"
 ],
 "correctAnswer": 1
}
```

**Explanation:** Container-based workers with auto-scaling groups provide elastic scaling based on queue depth, cost efficiency with resource sharing, and operational simplicity. This approach can dynamically adjust capacity to handle varying job loads while maintaining cost effectiveness.

## 6. [MID_LEVEL · TRUE_FALSE] In an at-least-once execution model, job operations should be idempotent to avoid duplicate side-effects.

```json
{
 "correctAnswer": true
}
```

**Explanation:** At-least-once delivery means jobs may execute more than once due to retries or failures. While the delivery guarantee doesn't automatically make operations idempotent, developers should design job operations to be idempotent to safely handle the potential duplicate executions. This prevents issues like double-billing or inconsistent state when jobs are retried. Exactly-once systems avoid this issue entirely, but at-least-once systems require careful idempotent design.

## 7. [MID_LEVEL · MULTIPLE_CHOICE] How does storing recurring job definitions separately from timestamped execution instances help the scheduler find jobs due soon?

```json
{
 "options": [
  "It stores every future recurrence without extra space",
  "It lets the scheduler query a due-time range directly",
  "It removes the need to calculate future execution times",
  "It makes recurring job definitions immutable and cacheable"
 ],
 "correctAnswer": 1
}
```

**Explanation:** Concrete execution timestamps let the scheduler query a due-time range. The recurrence rule stays in the job definition and is used to create subsequent execution instances.

## 8. [MID_LEVEL · MULTIPLE_CHOICE] Which property makes message queues suitable for handling traffic spikes in distributed systems?

```json
{
 "options": [
  "Persistent storage capabilities with write-ahead logging",
  "Buffering and decoupling producers from consumers",
  "Built-in authentication and authorization mechanisms for queue access",
  "Automatic data compression"
 ],
 "correctAnswer": 1
}
```

**Explanation:** Message queues buffer incoming requests and decouple producers from consumers, allowing producers to continue sending messages even when consumers are temporarily overwhelmed. This buffering smooths out traffic spikes and prevents cascading failures.

## 9. [MID_LEVEL · TRUE_FALSE] Worker failure detection systems must balance detection speed against false positive rates.

```json
{
 "correctAnswer": true
}
```

**Explanation:** Fast failure detection (short timeouts) can trigger false positives due to network delays or temporary overload, while slow detection (long timeouts) delays recovery. Systems must balance these trade-offs based on their tolerance for duplicate work versus recovery speed.

## 10. [MID_LEVEL · MULTIPLE_CHOICE] An SQS worker crashes while processing a message, without deleting it or changing its visibility again. What controls when the message normally becomes eligible for another worker to receive?

```json
{
 "options": [
  "The job's original schedule time",
  "The worker's heartbeat interval and health check frequency",
  "The queue's visibility timeout",
  "The database transaction timeout"
 ],
 "correctAnswer": 2
}
```

**Explanation:** The message normally becomes eligible when its current visibility timeout expires. Actual retry start also depends on when another worker receives it, and standard SQS delivery can include duplicates.

## 11. [SENIOR · MULTIPLE_CHOICE] The design stores execution instances in DynamoDB with `time_bucket` rounded to the hour as the partition key. At the target scale of 10k jobs/sec, what is the main risk if many jobs are scheduled for the same hour, and what is the best mitigation?

```json
{
 "options": [
  "The sort key will no longer be unique; replace it with a random UUID only.",
  "The hour bucket can become a hot partition; add shard suffixes to the time bucket and query all shards for the scheduling window.",
  "The database will lose ordering within the hour; store CRON expressions directly in the Jobs table instead.",
  "The workers will execute jobs too early; reduce the bucket size from one hour to one day."
 ],
 "correctAnswer": 1
}
```

**Explanation:** A single hourly partition can concentrate all reads and writes for near-term executions, which is dangerous at 10k jobs/sec. Sharding the bucket spreads load while still allowing schedulers to query the bounded set of shards for the relevant time window.

## 12. [SENIOR · TRUE_FALSE] In the Executions table, making the sort key start with the exact execution timestamp, rather than just using `job_id`, is important because it lets the scheduler range-query a time bucket for the next few seconds of due work instead of scanning or filtering the whole hour.

```json
{
 "correctAnswer": true
}
```

**Explanation:** The article’s schema uses `time_bucket` as the partition key and `execution_time` as the sort key, where `execution_time` begins with the exact scheduled timestamp. That preserves efficient time-range queries within an hourly bucket, which matters at 10k jobs/sec because filtering an entire hour of executions would be far too expensive.

## 13. [SENIOR · MULTIPLE_CHOICE] The system uses a key-value store for Jobs and must support `GET /jobs?user_id={user_id}&status={status}&start_time={start_time}&end_time={end_time}`. Which data-modeling choice best supports this access pattern without scanning all jobs?

```json
{
 "options": [
  "Store all jobs under a single `status` partition key so each status query is ordered globally.",
  "Use `job_id` as the only key and filter by `user_id`, `status`, and time in application code.",
  "Maintain a secondary index or denormalized view keyed by `user_id`, with status and time encoded for efficient range queries.",
  "Store only the latest status in the Task table because tasks are reusable across jobs."
 ],
 "correctAnswer": 2
}
```

**Explanation:** A key-value store scales well only when queries match its keys or indexes. Since status monitoring is per user and often time-bounded, the design needs an index or denormalized table aligned to `user_id` plus status/time rather than scanning by `job_id`.

## 14. [SENIOR · MULTIPLE_CHOICE] Which architecture BEST achieves sub-second job execution precision at scale?

```json
{
 "options": [
  "Single database polling every second",
  "Two-phase: periodic query plus priority queue",
  "Distributed locks with heartbeats and lease-based coordination",
  "Real-time database triggers"
 ],
 "correctAnswer": 1
}
```

**Explanation:** Two-phase architecture combines durable storage with fast in-memory queuing. Periodic database queries (every few minutes) load upcoming jobs into a priority queue, which can then execute jobs with sub-second precision without overwhelming the database.

## 15. [SENIOR · MULTIPLE_CHOICE] An SQS message is received at t = 0 with a 60-second visibility timeout. At t = 40, the worker extends visibility to 90 seconds from that moment, then crashes at t = 50. With no further visibility changes, when does the timeout expire?

```json
{
 "options": [
  "t = 60 seconds",
  "t = 90 seconds",
  "t = 130 seconds",
  "t = 140 seconds"
 ],
 "correctAnswer": 2
}
```

**Explanation:** The extension starts a new 90-second visibility interval at t = 40, so it expires at t = 130. The crash does not reset that interval; expiration makes the message eligible for another receive.
