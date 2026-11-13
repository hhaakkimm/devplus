# Distributed Rate Limiter System Design Quiz

## 1. [JUNIOR · MATCHING_PAIRS] Match each rate limiting algorithm to its defining characteristic:

```json
{
 "leftItems": [
  "Fixed Window Counter",
  "Sliding Window Log",
  "Sliding Window Counter",
  "Token Bucket"
 ],
 "rightItems": [
  "Stores individual request timestamps for perfect accuracy",
  "Allows burst capacity with steady refill rate",
  "Simple buckets that reset at fixed intervals",
  "Weighted average of current and previous window counts"
 ],
 "correctPairs": [
  2,
  0,
  3,
  1
 ]
}
```

**Explanation:** Fixed Window uses simple counters that reset at intervals. Sliding Window Log stores every timestamp for perfect accuracy but uses more memory. Sliding Window Counter approximates sliding windows using weighted averages. Token Bucket allows burst traffic while maintaining steady-state limits via refill rate.

## 2. [JUNIOR · TRUE_FALSE] Client-side rate limiting alone is sufficient to protect server resources from malicious traffic.

```json
{
 "correctAnswer": false
}
```

**Explanation:** Client-side rate limiting can't be relied on for protection since a malicious client controls its own code and can bypass any client-side restriction. Server-side rate limiting is required to actually protect server resources from abuse.

## 3. [MID_LEVEL · MULTIPLE_CHOICE] Which rate limiting algorithm best handles bursty traffic patterns while maintaining long-term limits?

```json
{
 "options": [
  "Fixed Window Counter",
  "Sliding Window Log",
  "Token Bucket",
  "Sliding Window Counter"
 ],
 "correctAnswer": 2
}
```

**Explanation:** Token Bucket allows burst capacity (bucket size) while enforcing steady-state limits (refill rate). A client can make many requests immediately if tokens are available, then must wait for the bucket to refill, naturally handling real-world traffic patterns.

## 4. [MID_LEVEL · TRUE_FALSE] With a Fixed Window Counter, a client can send up to twice its per-window limit within a short span that straddles a window boundary.

```json
{
 "correctAnswer": true
}
```

**Explanation:** Fixed windows have boundary effects where a client can use its full limit at the end of one window (e.g., 12:00:59) and immediately use another full limit at the start of the next window (12:01:00), sending up to 2x the intended rate across that boundary.

## 5. [MID_LEVEL · MULTIPLE_CHOICE] When Redis shards become unavailable, which factor MOST influences the choice between fail-open vs fail-closed for rate limiters?

```json
{
 "options": [
  "The programming language used",
  "Whether the system can tolerate abuse during outages",
  "The number of Redis shards deployed across availability zones",
  "The geographic distribution of users"
 ],
 "correctAnswer": 1
}
```

**Explanation:** The choice depends on what's worse for your system: brief API unavailability (fail-closed) or temporary uncontrolled traffic (fail-open). Consumer apps often fail-open to maintain availability. Financial systems, payment processors, or APIs vulnerable to abuse may fail-closed to prevent system collapse or fraud, even if it means downtime.

## 6. [MID_LEVEL · TRUE_FALSE] Lua scripts in Redis execute atomically, making them suitable for read-modify-write operations in rate limiting.

```json
{
 "correctAnswer": true
}
```

**Explanation:** Lua scripts execute atomically on Redis - no other command can run between script operations. This is essential for rate limiting where you need to read current state, calculate new values, and update state without race conditions between concurrent requests.

## 7. [MID_LEVEL · MULTIPLE_CHOICE] For dynamic rate limit configuration updates, what is the main trade-off between poll-based and push-based approaches?

```json
{
 "options": [
  "Complexity vs update speed",
  "Memory usage vs CPU usage",
  "Consistency vs availability",
  "Security vs performance"
 ],
 "correctAnswer": 0
}
```

**Explanation:** Poll-based systems are simpler to implement but have update delays (30+ seconds). Push-based systems like ZooKeeper provide immediate updates but add significant complexity around connection failures, partial updates, and fallback mechanisms.

## 8. [MID_LEVEL · MULTIPLE_CHOICE] Which approach keeps rate limiting accurate when state is spread across multiple Redis shards?

```json
{
 "options": [
  "Distribute requests randomly across shards",
  "Assign requests round-robin",
  "Map each client identifier deterministically to a single shard",
  "Use a load balancer with session affinity"
 ],
 "correctAnswer": 2
}
```

**Explanation:** Deterministically mapping a client identifier (user/IP/API key) to one shard means all of that client's requests hit the same shard, so its counter stays accurate. Random or round-robin assignment splits a client's requests across shards, so no single shard sees the true count and limits become ineffective.

## 9. [MID_LEVEL · TRUE_FALSE] In-process rate limiting can work effectively in distributed systems with multiple application servers.

```json
{
 "correctAnswer": false
}
```

**Explanation:** In-process rate limiting fails in distributed systems because each server only sees a portion of a user's total traffic. If requests are distributed across 5 servers, each server might think a user is under their limit while globally they're exceeding it by 5x.

## 10. [MID_LEVEL · MULTIPLE_CHOICE] When implementing Token Bucket, why does each bucket store both a token count and a last-refill timestamp?

```json
{
 "options": [
  "To support multiple separate rate limits per user",
  "So tokens can be refilled lazily based on the time elapsed since the last request",
  "To keep an audit log of every request",
  "To detect clock skew between gateway servers"
 ],
 "correctAnswer": 1
}
```

**Explanation:** Token Bucket refills lazily. On each request you compute how many tokens to add from the time elapsed since the last refill, consume one, then store the new count and timestamp. Without the timestamp you couldn't know how many tokens to add, so a bare counter isn't enough.

## 11. [SENIOR · TRUE_FALSE] At 1M requests/second, a Sliding Window Log that stores one timestamp per accepted request is a poor default when approximate enforcement is acceptable, because its state and cleanup work scale with request volume rather than with the number of active client-rule buckets.

```json
{
 "correctAnswer": true
}
```

**Explanation:** A Sliding Window Log is accurate, but it keeps per-request timestamps and must remove expired entries, which creates high memory and maintenance overhead at large scale. Since the article’s requirements allow eventual consistency and do not require strong precision, bounded-state approaches like token bucket or counter-based windows fit the scale/latency goals better.

## 12. [SENIOR · MULTIPLE_CHOICE] A team puts the rate limiter in the API gateway. Later, product requires limits based on subscription tier, account status, and a temporary Black Friday exception, but the gateway currently only sees IP address and a raw API key and does not call an auth/user service. What is the best design conclusion?

```json
{
 "options": [
  "Keep the gateway limiter unchanged because API keys are enough to infer all user-specific rules.",
  "Move rate limiting entirely client-side so clients can apply their own subscription-specific limits.",
  "Either enrich the gateway with authenticated user context or use a dedicated rate-limiting service that receives that context; otherwise those rules cannot be applied correctly at the edge.",
  "Switch to fixed-window counters because they do not require user context."
 ],
 "correctAnswer": 2
}
```

**Explanation:** The article notes that gateway placement is strong for protecting downstream services, but it can only enforce rules using information available at the edge. Rich business-context rules, like subscription tier or account status, require authenticated/enriched context or a dedicated service that application servers can call with that context.

## 13. [SENIOR · MULTIPLE_CHOICE] A rate limiter handles 1M requests/second, and every request waits on a rate-limit check that takes 8ms on average. Ignoring queuing, about how many rate-limit checks are in flight at any given moment?

```json
{
 "options": [
  "About 125",
  "About 8,000",
  "About 1 million",
  "About 8 million"
 ],
 "correctAnswer": 1
}
```

**Explanation:** By Little’s Law, concurrency equals throughput times latency: 1,000,000 requests/sec × 0.008 sec = 8,000 checks in flight. The distractors come from common slips: 125 is 1 / 0.008 with the request rate dropped, 1 million confuses throughput with concurrency, and 8 million forgets to convert milliseconds to seconds. Thousands of outstanding checks at any moment is why the article treats the per-request round trip as a real cost that the rate-limit store must be scaled for.

## 14. [SENIOR · RANKING] Rank these rate limiter placement options from WEAKEST to STRONGEST protection for a distributed system:

```json
{
 "items": [
  "Dedicated Service (separate microservice)",
  "In-Process (local memory in each app server)",
  "API Gateway (edge-level filtering)"
 ],
 "correctOrder": [
  1,
  0,
  2
 ]
}
```

**Explanation:** In-Process is weakest because each server only sees partial traffic, making limits ineffective in distributed systems. Dedicated Service provides centralized state but adds latency since requests reach app servers before being checked. API Gateway is strongest because it filters malicious traffic at the edge before it consumes any backend resources.

## 15. [SENIOR · MULTIPLE_CHOICE] The requirements say long-term persistence of rate-limiting data is out of scope, while the platform has 100M daily active users. Which state-management choice best follows from those requirements?

```json
{
 "options": [
  "Persist every per-client counter forever so future rate-limit decisions can use complete historical traffic.",
  "Delete a client’s counter immediately after an allowed request because the request has already passed.",
  "Store only one global counter per rule, because per-client state is too large at this scale.",
  "Keep short-lived per-client/per-rule state with expiration tied to the relevant window or idle bucket lifetime, while storing rule configuration separately."
 ],
 "correctAnswer": 3
}
```

**Explanation:** Rate limiting needs recent usage state, not permanent analytics history. Expiring per-client state prevents unbounded growth across a large user base while still allowing the limiter to enforce the active rule window.
