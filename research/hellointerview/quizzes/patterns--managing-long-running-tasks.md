# Long-Running Tasks System Design Quiz

## 1. [JUNIOR · MULTIPLE_CHOICE] What is a Dead Letter Queue (DLQ) used for?

```json
{
 "options": [
  "Storing completed jobs for auditing and replay purposes",
  "Isolating jobs that repeatedly fail",
  "Caching frequently accessed data",
  "Balancing load across workers"
 ],
 "correctAnswer": 1
}
```

**Explanation:** A DLQ isolates jobs that fail repeatedly (after 3-5 retries) to prevent poison messages from crashing workers while allowing healthy work to continue.

## 2. [JUNIOR · MULTIPLE_CHOICE] Which message queue option is simple to set up but stores data primarily in memory, risking job loss during crashes?

```json
{
 "options": [
  "AWS SQS",
  "RabbitMQ with disk persistence",
  "Redis with Bull/BullMQ",
  "Apache Kafka"
 ],
 "correctAnswer": 2
}
```

**Explanation:** Redis with Bull/BullMQ is popular for its simplicity and works for most use cases. However, Redis stores data in memory by default, so a hard crash before persistence can lose queued jobs.

## 3. [MID_LEVEL · TRUE_FALSE] A video transcode that takes three hours is a good fit for a serverless function.

```json
{
 "correctAnswer": false
}
```

**Explanation:** Serverless functions cap how long one invocation can run (15 minutes on Lambda). Multi-hour work belongs on a server or container, or has to be split into shorter steps that track progress durably.

## 4. [MID_LEVEL · TRUE_FALSE] Rejecting new jobs when the queue exceeds a configured capacity is one way to apply backpressure.

```json
{
 "correctAnswer": true
}
```

**Explanation:** A bounded admission policy prevents accepting more work than the system can handle. Rate limiting or slowing producers are other options, depending on the workload and how clients should respond.

## 5. [MID_LEVEL · MULTIPLE_CHOICE] How do you prevent duplicate work when a user clicks 'Generate Report' multiple times?

```json
{
 "options": [
  "Rate limiting on the API gateway",
  "Idempotency keys",
  "Load balancing",
  "Caching"
 ],
 "correctAnswer": 1
}
```

**Explanation:** An idempotency key identifies the operation, for example user ID + action + a timestamp rounded to a time window, so repeated clicks within that window produce the same key. The server sees the key already exists and returns the existing job ID instead of creating duplicate work. A raw timestamp would change between clicks and defeat deduplication.

## 6. [MID_LEVEL · MULTIPLE_CHOICE] What is the main benefit of using Kafka for job queues compared to Redis?

```json
{
 "options": [
  "Lower latency due to kernel-level zero-copy optimizations",
  "Simpler setup",
  "Replay capability and strict ordering",
  "Better security"
 ],
 "correctAnswer": 2
}
```

**Explanation:** Kafka's append-only log allows message replay, fan-out to multiple consumers, and maintains strict ordering while handling high volumes, though it's more complex.

## 7. [MID_LEVEL · TRUE_FALSE] With the async worker pattern, the work is not finished when the API returns the job ID.

```json
{
 "correctAnswer": true
}
```

**Explanation:** The API returns as soon as the job is queued. The client polls the status endpoint or waits for a push to find out when the work actually finished.

## 8. [MID_LEVEL · MATCHING_PAIRS] Match each async-processing problem from the 'Common Deep Dives' section to the solution the article prescribes for it.

```json
{
 "leftItems": [
  "A poison job keeps failing and crashing workers forever",
  "An impatient user submits three identical jobs",
  "Black Friday floods the queue with 10x more jobs than workers can handle",
  "5-second reports and 5-hour reports share one queue, blocking each other"
 ],
 "rightItems": [
  "Idempotency keys",
  "Separate queues by job type or duration",
  "Dead Letter Queue (DLQ)",
  "Backpressure"
 ],
 "correctPairs": [
  2,
  0,
  3,
  1
 ]
}
```

**Explanation:** Repeatedly failing jobs are moved to a Dead Letter Queue after several retries. Duplicate submissions are deduplicated with idempotency keys. An overwhelmed queue is handled with backpressure that rejects new jobs. Mixed-duration workloads are split into separate queues to prevent head-of-line blocking.

## 9. [MID_LEVEL · MULTIPLE_CHOICE] How should you handle mixed workloads where some jobs take 5 seconds and others take 5 hours?

```json
{
 "options": [
  "Use faster servers with higher clock speeds and more cores",
  "Increase timeout limits",
  "Separate queues by job type or duration",
  "Add more workers"
 ],
 "correctAnswer": 2
}
```

**Explanation:** Separate queues prevent head-of-line blocking where long jobs block short ones. Use different queues with appropriate worker configurations for each job type.

## 10. [MID_LEVEL · MULTIPLE_CHOICE] When should you proactively suggest async workers in a system design interview?

```json
{
 "options": [
  "For any database operation involving joins",
  "When hearing about video transcoding, PDF generation, or bulk operations",
  "Only when asked about scaling",
  "For simple CRUD operations"
 ],
 "correctAnswer": 1
}
```

**Explanation:** Operations that take seconds to minutes (video transcoding, image processing, PDF generation, bulk emails) are clear signals for async processing.

## 11. [SENIOR · MULTIPLE_CHOICE] A system needs sophisticated job routing across multiple worker pools, and the team is willing to operate its own queue cluster to get that control. Which queue choice best matches the article's guidance?

```json
{
 "options": [
  "AWS SQS, because it removes operational overhead and is always best for complex routing.",
  "Redis with BullMQ, because it is memory-first and therefore the most durable option.",
  "Kafka, because append-only replay is the same thing as complex routing.",
  "RabbitMQ, because it supports complex routing patterns but requires self-hosting and operational care."
 ],
 "correctAnswer": 3
}
```

**Explanation:** The article positions RabbitMQ as a strong fit when you need more control and complex routing patterns. The trade-off is operational burden: managing clusters, upgrades, and disk usage yourself.

## 12. [SENIOR · TRUE_FALSE] In the article's architecture, a durable queue can serve as the user-facing job-status store, so workers do not need to persist job state updates in a database.

```json
{
 "correctAnswer": false
}
```

**Explanation:** The queue buffers pending work, but the article explicitly separates that from job status tracking. Workers update job status in a database so users can check progress or completion by job ID, which adds database load and API complexity.

## 13. [SENIOR · MULTIPLE_CHOICE] You choose AWS SQS for a report-generation system, but some report requests include an 8 MB filter/configuration object. Based on the article's trade-offs, what is the best design?

```json
{
 "options": [
  "Store the large configuration in a database or object store and enqueue only a job ID or pointer.",
  "Put the full 8 MB payload directly into SQS because SQS is managed and durable.",
  "Keep the HTTP request open until the worker has read the full payload from the client.",
  "Use Redis instead because memory-first queues avoid message-size limits."
 ],
 "correctAnswer": 0
}
```

**Explanation:** The article notes that SQS has a 1 MB message size limit, so large job data should live elsewhere while the queue carries an identifier. This also keeps queue messages small and lets job status and metadata be tracked independently.

## 14. [SENIOR · MULTIPLE_CHOICE] At month-end, 18,000 PDF generation jobs are queued at once. Each job takes 3 minutes of worker time, each worker processes one job at a time, and the product requirement is to drain the queue within 90 minutes. Ignoring overhead and retries, what is the minimum worker pool size you should plan for?

```json
{
 "options": [
  "90 workers",
  "200 workers",
  "600 workers",
  "1,800 workers"
 ],
 "correctAnswer": 2
}
```

**Explanation:** The total work is 18,000 jobs × 3 worker-minutes per job = 54,000 worker-minutes. Dividing by 90 minutes gives 600 workers, assuming each worker processes one job at a time with no overhead or retries.

## 15. [SENIOR · TRUE_FALSE] For GPU-heavy video transcoding requests, placing GPU capacity in the worker pool rather than the web tier preserves one of the pattern's key scaling benefits.

```json
{
 "correctAnswer": true
}
```

**Explanation:** The article emphasizes independent scaling and resource specialization: web servers can stay lightweight while specialized workers use GPU-optimized machines. Scaling the API tier and GPU workers together would waste expensive GPU capacity on request handling that does not need it.
