# Code Execution Platform System Design Quiz

## 1. [JUNIOR · TRUE_FALSE] Timestamps that need to be trusted should be generated on the server not the client.

```json
{
 "correctAnswer": true
}
```

**Explanation:** Client-provided timestamps can be easily manipulated or incorrect due to clock skew. Security best practices require servers to generate their own timestamps to ensure data integrity and prevent timestamp-based attacks or inconsistencies.

## 2. [JUNIOR · TRUE_FALSE] Systems can prioritize availability over consistency for non-critical features like leaderboards.

```json
{
 "correctAnswer": true
}
```

**Explanation:** According to the CAP theorem, distributed systems must choose between consistency and availability during network partitions. For non-critical features like leaderboards, temporary inconsistency is acceptable if it maintains system availability.

## 3. [MID_LEVEL · TRUE_FALSE] When building the high-level design, walking through each API endpoint is a practical way to verify that the design satisfies the functional requirements.

```json
{
 "correctAnswer": true
}
```

**Explanation:** The article recommends going one-by-one through the functional requirements and mapping them to APIs and components. This keeps the design focused and makes it easier to explain where data flows and where state is stored or updated.

## 4. [MID_LEVEL · TRUE_FALSE] In the Redis sorted set leaderboard design, a client paging through a 100,000-user competition can fetch any single page with one `ZRANGE ... REV` call using start and stop offsets, instead of downloading the full ranked list.

```json
{
 "correctAnswer": true
}
```

**Explanation:** A sorted set keeps users ordered by score, so `ZRANGE competition:leaderboard:{competitionId} start stop REV WITHSCORES` returns just the ranks between the two offsets. The server sends the first page or two, and the client requests later pages as the user scrolls. Each 5-second poll stays small, which a 100,000-entry response would not.

## 5. [MID_LEVEL · MULTIPLE_CHOICE] Why does the article suggest returning `Partial<Problem>[]` from `GET /problems` instead of full `Problem` objects?

```json
{
 "options": [
  "Because list pages only need summary fields, so omitting full statements, code stubs, and test cases reduces unnecessary payload.",
  "Because clients cannot parse nested JSON fields like code stubs or test cases.",
  "Because returning full problem objects would prevent server-side authentication from working.",
  "Because NoSQL databases cannot retrieve complete documents by ID."
 ],
 "correctAnswer": 0
}
```

**Explanation:** The problem list view only needs fields like title, id, difficulty, and maybe tags. Returning the full problem statement, code stubs, and test cases would waste bandwidth and make the page heavier without helping the UI.

## 6. [MID_LEVEL · MULTIPLE_CHOICE] In the article’s LeetCode design, why might a simple client-server or monolithic architecture be preferred over microservices?

```json
{
 "options": [
  "Because monoliths are always more scalable than microservices.",
  "Because the system is relatively small, so the operational overhead of many services may not be worth it.",
  "Because microservices cannot communicate with databases directly.",
  "Because competitions require all features to share one database transaction."
 ],
 "correctAnswer": 1
}
```

**Explanation:** The article notes that this LeetCode-like system has a modest scale compared with many system design problems. For a smaller system, a single codebase can be easier to manage, while microservices may add unnecessary deployment and operational complexity.

## 7. [MID_LEVEL · MULTIPLE_CHOICE] Which approach works BEST for CPU-intensive code execution at scale?

```json
{
 "options": [
  "Synchronous processing",
  "Asynchronous processing",
  "Single-threaded execution",
  "Direct database calls"
 ],
 "correctAnswer": 1
}
```

**Explanation:** Asynchronous processing allows systems to handle CPU-intensive tasks without blocking other operations. It enables better resource utilization, load distribution, and system responsiveness under high demand.

## 8. [MID_LEVEL · MULTIPLE_CHOICE] For `GET /problems?page=1&limit=100`, why does the article mention indexing the database properly?

```json
{
 "options": [
  "To encrypt problem statements before returning them",
  "To fetch paginated problem lists efficiently without scanning unnecessary records",
  "To guarantee that leaderboard rankings are strongly consistent",
  "To prevent users from submitting duplicate solutions"
 ],
 "correctAnswer": 1
}
```

**Explanation:** The problem list endpoint returns pages of results, so the database should be able to locate and return the requested slice efficiently. Proper indexing helps avoid expensive full-table scans as the number of problems grows.

## 9. [MID_LEVEL · MULTIPLE_CHOICE] Why does the article consider a NoSQL database like DynamoDB reasonable for storing `Problem` entities?

```json
{
 "options": [
  "Because leaderboards must always be stored in the same table as problems.",
  "Because NoSQL databases guarantee stronger consistency than SQL databases by default.",
  "Because the design does not require complex queries and can store related fields like test cases as nested subdocuments.",
  "Because SQL databases cannot support pagination."
 ],
 "correctAnswer": 2
}
```

**Explanation:** The article chooses NoSQL because the access patterns are simple: fetch lists of problems and fetch a problem by ID. It also fits the document-style schema where code stubs and test cases can be nested inside the problem entity.

## 10. [MID_LEVEL · MULTIPLE_CHOICE] Why does `GET /problems/:id` include an optional `language` query parameter in the article’s API design?

```json
{
 "options": [
  "To return the code stub for the user’s selected language",
  "To decide which database engine should store the problem",
  "To verify that the submitted code passes all test cases",
  "To hide the problem statement from unsupported browsers"
 ],
 "correctAnswer": 0
}
```

**Explanation:** A problem can have different starter code for Python, JavaScript, TypeScript, and other languages. The language parameter lets the server return the full problem along with the appropriate code stub, defaulting to a language like Python if none is provided.

## 11. [SENIOR · MULTIPLE_CHOICE] During the initial design, a candidate proposes separate microservices for Problems, Submissions, Leaderboards, Users, Profiles, and Payments. Based on the article’s constraints, what is the strongest critique?

```json
{
 "options": [
  "It is invalid because LeetCode-style systems cannot be implemented with microservices.",
  "It should be replaced with a single database table containing every entity to avoid joins.",
  "It adds operational overhead for a relatively small, scoped system, and several proposed services are explicitly out of scope.",
  "It violates the requirement to prioritize availability over consistency because microservices are always strongly consistent."
 ],
 "correctAnswer": 2
}
```

**Explanation:** The article argues that this is a comparatively small system and that a simple client-server or monolithic approach may be more appropriate than defaulting to microservices. Adding services for auth, profiles, and payments also distracts from the stated scope and increases complexity without satisfying core requirements.

## 12. [SENIOR · TRUE_FALSE] Adding a message queue between the API server and code-execution workers improves burst handling, but it does not by itself satisfy the 5-second feedback requirement if worker capacity is too low.

```json
{
 "correctAnswer": true
}
```

**Explanation:** A queue smooths traffic spikes and decouples request intake from CPU-heavy execution, but queued work still waits behind earlier submissions. To meet a latency target, the system must size or autoscale workers based on arrival rate, execution time, and acceptable queue depth.

## 13. [SENIOR · TRUE_FALSE] For a competition with 100,000 users, recomputing and sending the full leaderboard after every submission is a reasonable live-leaderboard strategy if the leaderboard is stored in Redis.

```json
{
 "correctAnswer": false
}
```

**Explanation:** Redis can make rank updates and range queries efficient, but it does not remove the network and fanout cost of repeatedly sending 100,000 entries. The article’s paginated leaderboard design implies clients should fetch limited ranked ranges, with availability favored over perfectly consistent global updates.

## 14. [SENIOR · MULTIPLE_CHOICE] In the article's Redis sorted-set leaderboard design, what should happen when a processed submission changes a user's score?

```json
{
 "options": [
  "Persist the submission result in the main database and update the user's score in Redis.",
  "Update Redis only and rebuild the submission history from leaderboard entries later.",
  "Persist the submission result only and recompute the entire leaderboard for each poll.",
  "Send the score from the execution worker directly to every client over WebSockets."
 ],
 "correctAnswer": 0
}
```

**Explanation:** The article stores submission results in the main database while using a Redis sorted set to serve the current leaderboard. Processing a submission updates both stores, and clients poll the Redis-backed leaderboard endpoint for ranked results. Redis provides fast ranking, while the database keeps the submission record.

## 15. [SENIOR · MULTIPLE_CHOICE] The article chooses a NoSQL database and nests test cases inside the Problem document because it assumes no complex queries are needed. Which new requirement would most directly weaken that data-model choice?

```json
{
 "options": [
  "Users need to fetch a single problem by id before coding a solution.",
  "The client needs a language-specific code stub when opening a problem.",
  "The system needs to store problem tags such as arrays, dynamic programming, and graphs.",
  "Admins need cross-problem analytics and updates over individual test cases, such as finding the most frequently failed test case globally."
 ],
 "correctAnswer": 3
}
```

**Explanation:** Nesting test cases is convenient when the main access pattern is fetching an entire problem document. If the system must query or update individual test cases across many problems, a more normalized model or separate test-case store becomes easier to index, scan, and maintain.
