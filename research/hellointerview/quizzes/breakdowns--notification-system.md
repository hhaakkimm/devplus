# Notification System Quiz

## 1. [JUNIOR · TRUE_FALSE] Every send declares a priority at the API, which is what later lets the system treat an OTP differently from a promo.

```json
{
 "correctAnswer": true
}
```

**Explanation:** Both the notification and campaign endpoints carry a priority of high or standard. The two traffic classes have completely different needs, low volume and latency sensitive versus bursty and latency tolerant, and getting both through one system is the heart of the problem.

## 2. [JUNIOR · MULTIPLE_CHOICE] The system delivers about 10M notifications a day. What does the design actually size for?

```json
{
 "options": [
  "The sustained rate of roughly 100 per second, since surges even out over the day",
  "Surges of about 5,000 per second, roughly 50x the sustained rate",
  "The peak of a single campaign, about 1M per second",
  "Whatever the providers allow, since the platform itself is never the bottleneck"
 ],
 "correctAnswer": 1
}
```

**Explanation:** Spread evenly, 10M a day is about 100 per second, which is almost nothing. Notifications don't spread evenly though, and a 1M-user campaign delivered inside five minutes is already over 3,000 per second, so the design targets surges of 5,000 per second.

## 3. [MID_LEVEL · MULTIPLE_CHOICE] Why does the accept path publish to the queue instead of writing the notification row first and then publishing?

```json
{
 "options": [
  "Writing the row first would violate the 202 contract the API promises",
  "The database write is slower than the queue write, which would blow the latency budget on the accept path",
  "Accepting a notification is a single publish, and writing both creates a dual write where a crash in between leaves a row no message represents",
  "Postgres can't hold the notification content, so there's nothing to write until a worker has resolved the recipient"
 ],
 "correctAnswer": 2
}
```

**Explanation:** The outbox pattern exists to fix exactly that dual write, but an outbox earns its complexity when you need to commit database state and produce a message together. Here the accept path has nothing else to commit, so a single durable publish is the whole job.

## 4. [MID_LEVEL · TRUE_FALSE] The design settles on Kafka over SQS because replaying a bad worker build is one of the stated requirements.

```json
{
 "correctAnswer": false
}
```

**Explanation:** The breakdown picks SQS. Kafka's rewind-and-replay is a real advantage and a fine choice to defend in an interview, but nothing in the requirements asked for it, so it doesn't justify the swap on its own.

## 5. [MID_LEVEL · TRUE_FALSE] With a polling dispatcher reading PENDING rows out of Postgres, a notification that arrives just after a poll waits nearly a full poll interval before dispatch even begins.

```json
{
 "correctAnswer": true
}
```

**Explanation:** The poll interval bounds how long a PENDING row can sit before anyone looks at it, so a 10 second poll means up to 10 seconds of dead time before the provider is called at all. That's on top of having to hand-build claiming with SKIP LOCKED, retry bookkeeping, and pruning a table that's both queue and history.

## 6. [MID_LEVEL · TRUE_FALSE] Segment membership is read as a snapshot when fan-out starts, so a user who joins the segment mid-publish misses that campaign.

```json
{
 "correctAnswer": true
}
```

**Explanation:** They catch the next one, which is a fine trade for a marketing campaign. The point worth making in an interview is noticing the behavior and naming it rather than letting it be an accident.

## 7. [MID_LEVEL · RANKING] Order the steps a delivery worker takes on a notification the user's preferences allow:

```json
{
 "items": [
  "Delete the message from the queue",
  "Write the outcome row to Postgres",
  "Receive the message, which hides it from other workers for the visibility timeout",
  "Look up the recipient's address or token and check their preferences",
  "Call the provider"
 ],
 "correctOrder": [
  2,
  3,
  4,
  1,
  0
 ]
}
```

**Explanation:** Deleting the message last is what makes the whole thing crash safe. A worker that dies anywhere before that delete leaves the message in the queue, so it reappears after the visibility timeout and another worker tries again.

## 8. [MID_LEVEL · MULTIPLE_CHOICE] Campaign messages are stamped with an ID derived from campaignId and userId. What does that buy?

```json
{
 "options": [
  "It lets a worker route the message to the right per-campaign queue",
  "It gives the segment snapshot a stable ordering to fan out in",
  "It keeps campaign traffic from colliding with direct sends in the dedup store",
  "A cron job that crashes mid fan-out republishes exactly the IDs the first pass produced"
 ],
 "correctAnswer": 3
}
```

**Explanation:** Deriving each message ID from the campaign and the recipient means a re-run is recognizable as the same work rather than new work. That only holds if the campaign itself has a stable id, which is why campaign creation takes an idempotency key too.

## 9. [MID_LEVEL · MATCHING_PAIRS] Match each mechanism to what it buys you:

```json
{
 "leftItems": [
  "Visibility timeout",
  "Dead-letter queue",
  "Token bucket in Redis",
  "Idempotency key on the request"
 ],
 "rightItems": [
  "A retried POST produces the same notification ID the original did",
  "A message a crashed worker was holding becomes available to another worker",
  "High priority keeps a reserved slice of the provider's rate limit",
  "A message that keeps failing stops being retried forever"
 ],
 "correctPairs": [
  1,
  3,
  2,
  0
 ]
}
```

**Explanation:** The visibility timeout is what makes a worker crash safe, since the message reappears rather than being lost. The dead-letter queue bounds retries, the shared token bucket carves the provider's allocation up by tier, and a stable key from the caller is what makes a retried send recognizable as the same send.

## 10. [MID_LEVEL · MULTIPLE_CHOICE] Splitting into a high priority queue and a standard queue helps, but it doesn't finish the job. What's still shared?

```json
{
 "options": [
  "The provider rate allocation and the worker pool, so standard traffic can still starve or block a high priority send",
  "The database, which becomes the bottleneck once both queues are draining at once",
  "The API gateway, which rate limits both tiers under one budget",
  "The dedup store, which serializes every send behind one Redis key"
 ],
 "correctAnswer": 0
}
```

**Explanation:** If standard traffic is consuming the whole Twilio allocation, the high priority SMS gets throttled by the provider even though it sat in a nearly empty queue on our side. A worker pinned on a slow provider call is the compute version of the same problem, which is why the tier gets its own pool as well as its own budget.

## 11. [SENIOR · MULTIPLE_CHOICE] Twilio's p99 climbs to 30 seconds. What does a bulkhead do that a circuit breaker doesn't?

```json
{
 "options": [
  "It caps how many calls to that provider can be in flight at once, so the rest of the fleet's capacity stays free",
  "It fails calls immediately once the error rate crosses a threshold, instead of waiting out the timeout",
  "It reroutes the affected channel to a backup provider",
  "It moves the affected messages to the dead-letter queue for inspection"
 ],
 "correctAnswer": 0
}
```

**Explanation:** A bulkhead is a semaphore on concurrency, so a degraded provider can only pin a bounded number of workers rather than all of them. Failing fast on a threshold is the circuit breaker, and swapping to a backup is the provider router, and the three are complementary rather than alternatives.

## 12. [SENIOR · TRUE_FALSE] Autoscaling the worker pool is a reasonable way to get an OTP out within 5 seconds during a 1M-message campaign backlog.

```json
{
 "correctAnswer": false
}
```

**Explanation:** Draining 1M messages in under 5 seconds needs about 200,000 sends per second, 40x the design target, and servers take seconds to minutes to come up under account limits that exist specifically to stop this. The real ceiling is the providers anyway, so more workers buy nothing.

## 13. [SENIOR · MULTIPLE_CHOICE] What's the correct dedup ordering, and what duplicate can still slip through?

```json
{
 "options": [
  "Check Redis before dispatch and write the marker after the provider accepts, leaving a window where the provider took the message and the worker died before recording it",
  "Write the marker before dispatch and clear it on failure, leaving a window where the clear itself fails",
  "Check and write in one atomic SET NX, leaving a window where Redis fails over between the two",
  "Check the outcome table before dispatch and skip Redis, leaving a window where replication lag hides a recent send"
 ],
 "correctAnswer": 0
}
```

**Explanation:** Recording only after the provider has taken the message means the marker tracks what was actually sent rather than what someone intended to send. The residual risk is a worker dying in the gap between the provider accepting and the outcome being written, and a rare duplicate is the price of making a drop impossible.

## 14. [SENIOR · MULTIPLE_CHOICE] The Redis dedup cache goes down mid-surge. What does the design do?

```json
{
 "options": [
  "Hold messages in the queue until Redis recovers, since sending without the check risks duplicates",
  "Fail the sends fast and let the dead-letter queue collect them for replay",
  "Fall through to the outcome table looking for a successful send, and if that's unreachable too, send anyway while tracking the skipped checks",
  "Switch every send to the high priority tier so the smaller volume can be deduped in memory"
 ],
 "correctAnswer": 2
}
```

**Explanation:** Redis is a cache in front of the outcome table, not the source of truth, so the check degrades to a slower but still correct database read. Beyond that the system prefers a possible duplicate to a definite drop, and it counts the skipped checks so an alert fires when that rate climbs.

## 15. [SENIOR · MULTIPLE_CHOICE] A worker claims the notification ID in Redis with SET NX before calling the provider. Why does that quietly turn at-least-once into at-most-once?

```json
{
 "options": [
  "SET NX isn't atomic across a Redis failover, so two workers can both win the claim",
  "If the worker dies after claiming and before sending, the key outlives it and every redelivery reads it as already handled",
  "The claim has no expiry, so the key eventually fills Redis and later claims start failing",
  "The queue deletes the message when the claim succeeds, so nothing is left to redeliver"
 ],
 "correctAnswer": 1
}
```

**Explanation:** The lock records that someone took the work, not that anything was actually sent. A deploy that nukes the worker between the claim and the provider call leaves a marker that causes every subsequent redelivery to be dropped, and nobody ever gets the OTP.
