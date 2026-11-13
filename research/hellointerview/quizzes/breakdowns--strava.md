# Strava System Design Quiz

## 1. [JUNIOR · MULTIPLE_CHOICE] Why does the article use PATCH for updating an activity's state?

```json
{
 "options": [
  "Because PATCH is required for creating new activity resources",
  "Because only a subset of the activity's fields needs to be updated",
  "Because PATCH automatically stores GPS coordinates locally",
  "Because PATCH is the only HTTP method that supports pagination"
 ],
 "correctAnswer": 1
}
```

**Explanation:** The article uses PATCH for activity state updates because the client only needs to send the fields being changed, such as the activity state. It contrasts this with PUT, which typically requires sending the entire resource.

## 2. [JUNIOR · MULTIPLE_CHOICE] Redis sorted sets enable efficient leaderboard operations because they provide which time complexity for rank retrieval?

```json
{
 "options": [
  "O(1) constant time",
  "O(log n) logarithmic time, using a skip list internally",
  "O(n) linear time",
  "O(n log n) linearithmic"
 ],
 "correctAnswer": 1
}
```

**Explanation:** Redis sorted sets use skip lists internally, providing O(log n) time complexity for insertions, deletions, and range queries. This logarithmic performance enables efficient leaderboard operations even with millions of users, unlike O(n) operations that would become prohibitively slow.

## 3. [MID_LEVEL · MULTIPLE_CHOICE] Which approach BEST handles millions of high-frequency write operations per second?

```json
{
 "options": [
  "Direct database writes with per-row transactional guarantees",
  "In-memory buffering with batch writes",
  "Synchronous API calls",
  "File-based logging"
 ],
 "correctAnswer": 1
}
```

**Explanation:** In-memory buffering with batch writes handles high-frequency operations by temporarily storing writes in fast memory, then periodically flushing batches to persistent storage. This reduces I/O overhead and database contention while maintaining data integrity.

## 4. [MID_LEVEL · MULTIPLE_CHOICE] For athlete leaderboards updated frequently, which approach balances real-time updates with system efficiency?

```json
{
 "options": [
  "Real-time database aggregation across all user records",
  "Redis sorted sets with incremental updates",
  "Hourly batch recalculation",
  "In-memory computation only"
 ],
 "correctAnswer": 1
}
```

**Explanation:** Redis sorted sets provide O(log n) insertions and range queries, enabling efficient leaderboard updates. Each activity completion can increment a user's score atomically, maintaining real-time rankings without expensive database aggregations over millions of records.

## 5. [MID_LEVEL · MULTIPLE_CHOICE] Which pattern BEST enables friends to track live workout progress with minimal system complexity?

```json
{
 "options": [
  "WebSocket connections maintained to all online friends simultaneously",
  "Polling at predictable intervals",
  "Server-sent events for each GPS point",
  "Real-time database triggers"
 ],
 "correctAnswer": 1
}
```

**Explanation:** For fitness tracking, updates occur predictably every few seconds, making polling efficient. Friends can request updates slightly offset from the athlete's transmission schedule, avoiding the complexity of persistent connections while providing near-real-time experience with acceptable latency.

## 6. [MID_LEVEL · MULTIPLE_CHOICE] Which storage approach optimizes cost while maintaining performance for aging data?

```json
{
 "options": [
  "Keep all data in fast storage regardless of access frequency",
  "Data tiering with hot/warm/cold levels",
  "Delete old data automatically",
  "Compress all data equally"
 ],
 "correctAnswer": 1
}
```

**Explanation:** Data tiering moves less-accessed data to cheaper storage tiers over time. Hot data stays in fast expensive storage, warm data moves to moderate-cost options, and cold data archives to low-cost storage, optimizing the cost-performance balance.

## 7. [MID_LEVEL · TRUE_FALSE] Activity tracking applications can function completely offline by storing GPS coordinates locally until network connectivity returns.

```json
{
 "correctAnswer": true
}
```

**Explanation:** Modern mobile devices have substantial local storage and GPS capabilities independent of network access. Applications can record location data, calculate distances using algorithms like Haversine formula, and sync accumulated data when connectivity is restored, enabling full offline functionality.

## 8. [MID_LEVEL · MULTIPLE_CHOICE] Which data structure efficiently handles 2D geographic proximity searches?

```json
{
 "options": [
  "Hash Table",
  "Quad-tree",
  "Linked List",
  "Stack"
 ],
 "correctAnswer": 1
}
```

**Explanation:** Quad-trees recursively partition 2D space into quadrants, enabling efficient spatial queries for finding nearby locations. Unlike hash tables which provide O(1) lookups for exact matches, quad-trees support range queries essential for proximity searches.

## 9. [MID_LEVEL · MULTIPLE_CHOICE] When updates occur predictably every few seconds, which communication pattern works best?

```json
{
 "options": [
  "WebSockets with constant connections",
  "Polling at update intervals",
  "Server-sent events",
  "Long polling"
 ],
 "correctAnswer": 1
}
```

**Explanation:** For predictable updates, polling at the known interval is simpler and more efficient than maintaining persistent connections. WebSockets add complexity for scenarios where update timing is known, and polling can be precisely timed to match the update frequency.

## 10. [MID_LEVEL · TRUE_FALSE] Time-based database sharding optimizes queries for recent data access patterns.

```json
{
 "correctAnswer": true
}
```

**Explanation:** Time-based sharding places recent data on dedicated shards, enabling faster queries when most access patterns target recent records. This matches user behavior where current activities are accessed more frequently than historical data from years ago.

## 11. [SENIOR · MULTIPLE_CHOICE] An athlete goes offline after starting an activity. The phone records PAUSED at 10:05, RESUMED at 10:12, and COMPLETE at 10:30, but retry behavior causes the backend to receive COMPLETE before the PAUSED/RESUMED events. Which handling best preserves the article’s activity-duration model?

```json
{
 "options": [
  "Use the backend receive time for each state update, because server time is authoritative.",
  "Store timestamped status events and compute duration after ordering/deduplicating the event log.",
  "Reject PAUSED and RESUMED once COMPLETE has already been stored for the activity.",
  "Store only STARTED and COMPLETE, then estimate paused time from missing GPS samples."
 ],
 "correctAnswer": 1
}
```

**Explanation:** The article’s model relies on a log of status/timestamp pairs so active time can be computed by summing STARTED/RESUMED-to-PAUSED/COMPLETE intervals. In an offline system, receive order is not reliable, so the backend should preserve the event log and order it by event time or a client sequence number rather than overwriting state based on arrival order.

## 12. [SENIOR · MULTIPLE_CHOICE] A friends feed returns 40 completed activities per page. Each activity summary is about 250 bytes, but each full route contains 2,000 GPS points at 16 bytes per point before overhead. Which API behavior best matches the article’s design rationale?

```json
{
 "options": [
  "Return full Activity objects in the feed so the client never needs a second request.",
  "Return Partial<Activity> objects in the feed and fetch the full Activity, including route, only when the user opens one.",
  "Store routes only on the client because route payloads are too large for backend storage.",
  "Replace GPS routes with a single bounding box in both the feed and detail views."
 ],
 "correctAnswer": 1
}
```

**Explanation:** The article separates the list view from the detail view: the feed returns only partial activity data to avoid sending large route payloads unnecessarily. With these numbers, route data alone would be roughly 40 × 2,000 × 16 bytes ≈ 1.28 MB per page before overhead, versus about 10 KB for summaries.

## 13. [SENIOR · TRUE_FALSE] If the mobile app waits for backend acknowledgment of each route-point write before updating displayed distance, the design still satisfies the article’s offline and up-to-date-local-stats requirements.

```json
{
 "correctAnswer": false
}
```

**Explanation:** The article requires the app to work in remote areas and show accurate, current stats during the activity. That implies route and distance calculations must continue locally from GPS samples, while backend persistence can lag or happen after connectivity returns.

## 14. [SENIOR · MULTIPLE_CHOICE] An activity has this status log: STARTED at 09:00, PAUSED at 09:12, RESUMED at 09:20, PAUSED at 09:27, RESUMED at 09:30, COMPLETE at 09:45. Using the article’s timestamp-pair approach, what active duration should be stored for the activity?

```json
{
 "options": [
  "45 minutes",
  "34 minutes",
  "26 minutes",
  "27 minutes"
 ],
 "correctAnswer": 1
}
```

**Explanation:** Active time is the sum of intervals where the activity is actually running: 09:00–09:12, 09:20–09:27, and 09:30–09:45. That totals 12 + 7 + 15 = 34 minutes, excluding paused periods from 09:12–09:20 and 09:27–09:30.

## 15. [SENIOR · TRUE_FALSE] For an offline-capable design, active duration should be derived from client-captured status-event timestamps rather than backend receipt timestamps, even if events are synced later, because receipt times may reflect network delay instead of activity state transitions.

```json
{
 "correctAnswer": true
}
```

**Explanation:** The article’s timestamp-pair model depends on when the athlete actually started, paused, resumed, and completed the activity. In an offline or retry-heavy flow, backend receipt time can be delayed or reordered, so using it would distort active duration.
