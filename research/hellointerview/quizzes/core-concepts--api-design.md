# API Design System Design Quiz

## 1. [JUNIOR · TRUE_FALSE] According to the HTTP specification, PUT is defined as an idempotent method, meaning sending the same PUT request multiple times produces the same server state as sending it once.

```json
{
 "correctAnswer": true
}
```

**Explanation:** The HTTP spec defines PUT as idempotent - the server state after multiple identical PUT requests should be the same as after a single request. PUT replaces the entire resource, so repeating it just overwrites with the same data. This property makes PUT requests safe to retry on network failures.

## 2. [JUNIOR · TRUE_FALSE] gRPC uses JSON for serialization to ensure compatibility with web browsers.

```json
{
 "correctAnswer": false
}
```

**Explanation:** gRPC uses Protocol Buffers for binary serialization, not JSON. This makes it more efficient but less compatible with browsers, which is why it's typically used for internal service-to-service communication.

## 3. [MID_LEVEL · MULTIPLE_CHOICE] Which pagination approach is more stable when new records are being added?

```json
{
 "options": [
  "Offset-based pagination",
  "Cursor-based pagination",
  "Both are equally stable",
  "Neither handles new records well"
 ],
 "correctAnswer": 1
}
```

**Explanation:** Cursor-based pagination uses a pointer to a specific record instead of counting from the beginning, making it unaffected by new records being added during pagination.

## 4. [MID_LEVEL · MULTIPLE_CHOICE] When should you use API keys vs JWT tokens?

```json
{
 "options": [
  "Always use API keys for better security across all endpoints",
  "Use API keys for user sessions, JWT for services",
  "JWT for user sessions, API keys for service-to-service",
  "They are interchangeable in most production systems"
 ],
 "correctAnswer": 2
}
```

**Explanation:** Use JWT tokens for user sessions in web/mobile applications as they can carry user context and be stateless. Use API keys for internal service communication and external developer access.

## 5. [MID_LEVEL · MULTIPLE_CHOICE] When should you consider GraphQL over REST in system design interviews?

```json
{
 "options": [
  "Always, as GraphQL is more modern and feature-rich than REST",
  "When you need better performance",
  "When you see over-fetching or under-fetching problems",
  "Never, REST is always sufficient"
 ],
 "correctAnswer": 2
}
```

**Explanation:** Consider GraphQL when the interviewer mentions scenarios like different data needs for mobile vs web apps, or when you need to avoid over-fetching and under-fetching problems.

## 6. [MID_LEVEL · TRUE_FALSE] API keys are well-suited for authenticating end users in mobile and web applications.

```json
{
 "correctAnswer": false
}
```

**Explanation:** API keys are designed for service-to-service communication and developer access, not end-user authentication. They lack user context, session management, and expiration handling that user-facing applications need. JWT tokens or session-based auth are appropriate for end users.

## 7. [MID_LEVEL · MULTIPLE_CHOICE] In a booking API, a client sends `POST /events/123/bookings?notify=true` along with ticket selections and payment details. Where should the ticket selections and payment details go?

```json
{
 "options": [
  "In the request body, because they are the core payload used to create the booking",
  "In path parameters, because all booking inputs should be part of the URL structure",
  "In query parameters, because POST requests should not have request bodies",
  "In the HTTP status code, because it tells the server what data to create"
 ],
 "correctAnswer": 0
}
```

**Explanation:** The request body is where complex data for creating or updating a resource belongs, such as ticket quantities, seating choices, and payment information. The event ID belongs in the path because it identifies the parent resource, while `notify=true` is a query parameter because it modifies optional behavior.

## 8. [MID_LEVEL · MULTIPLE_CHOICE] Which API protocol should you default to in system design interviews?

```json
{
 "options": [
  "GraphQL",
  "REST",
  "gRPC",
  "WebSockets"
 ],
 "correctAnswer": 1
}
```

**Explanation:** REST should be your default choice as it's well-understood, has great tooling, and works for 90% of use cases. Only choose alternatives when you have specific requirements that REST can't meet.

## 9. [MID_LEVEL · MULTIPLE_CHOICE] A user service needs to make frequent internal calls to an auth service to quickly check whether a user can access a resource. Which API style best fits this internal, performance-sensitive interaction?

```json
{
 "options": [
  "GraphQL, because clients can choose exactly which fields they need",
  "REST, because all APIs should model actions as resources",
  "gRPC/RPC, because action-like calls with efficient binary communication fit internal service-to-service use",
  "WebSockets, because permission checks require persistent bidirectional connections"
 ],
 "correctAnswer": 2
}
```

**Explanation:** RPC-style APIs are a good fit for internal microservice calls where the operation is naturally an action, such as checkPermission(userId, resource). Protocols like gRPC also use efficient binary serialization and HTTP/2, which helps when performance is important.

## 10. [MID_LEVEL · MULTIPLE_CHOICE] In a REST API, how should path parameters and query parameters be used?

```json
{
 "options": [
  "Path parameters identify a required resource; query parameters apply optional filters",
  "Query parameters identify a required resource; path parameters apply optional filters",
  "Path parameters are for GET requests; query parameters are for POST requests",
  "They are interchangeable, so the choice is purely stylistic"
 ],
 "correctAnswer": 0
}
```

**Explanation:** Path parameters identify a specific resource in the URL structure and are required for the request to make sense (e.g., '/events/{id}/tickets'). Query parameters are optional modifiers used for filtering, sorting, or pagination (e.g., '/events?city=NYC&date=2024-01-01'). The two serve distinct roles and are not interchangeable.

## 11. [SENIOR · MULTIPLE_CHOICE] You are designing a system with public CRUD APIs for a mobile app, a high-volume internal `checkPermission(userId, resource)` call between services, and live chat updates. Which protocol mix best matches the article’s guidance?

```json
{
 "options": [
  "REST for public CRUD, RPC/gRPC for the internal permission check, and WebSockets or Server-Sent Events for live chat.",
  "GraphQL for all three because it avoids over-fetching and uses a single endpoint.",
  "REST for public CRUD, REST for live chat polling, and API keys for the internal permission check.",
  "gRPC for public mobile CRUD, REST for internal permission checks, and GraphQL subscriptions for chat."
 ],
 "correctAnswer": 0
}
```

**Explanation:** The article recommends REST as the default for standard web/mobile CRUD APIs. It suggests RPC/gRPC for high-performance internal service calls and notes that real-time features like chat need persistent protocols such as WebSockets or Server-Sent Events.

## 12. [SENIOR · TRUE_FALSE] For a valid authenticated request that fails because the database is unavailable, a 500-class response better matches the article’s guidance than returning a 400-class response.

```json
{
 "correctAnswer": true
}
```

**Explanation:** The article emphasizes distinguishing client errors from server errors. A database outage is a server-side failure, while 400 indicates the client sent a bad request.

## 13. [SENIOR · MULTIPLE_CHOICE] The server executes the same `PATCH /users/{id}` request repeatedly. Which request body leaves the user in the same state regardless of how many times it runs?

```json
{
 "options": [
  "`{\"add_phone_number\": \"555-0100\"}`, which appends the number to the user's `phone_numbers` list",
  "`{\"email\": \"ana@example.com\"}`, which sets `email` to that value",
  "`{\"login_count_increment\": 1}`, which adds 1 to `login_count`",
  "`{\"toggle_marketing_opt_in\": true}`, which flips `marketing_opt_in` to its opposite value"
 ],
 "correctAnswer": 1
}
```

**Explanation:** An operation is idempotent when repeating it leaves the same final state as running it once. Setting `email` to an exact value does that: every retry writes `ana@example.com` again. Appending adds a duplicate number, incrementing raises the count on each retry, and toggling flips the flag back and forth, so the final state depends on how many retries arrive.

## 14. [SENIOR · TRUE_FALSE] A DELETE endpoint can still be idempotent even if the first successful call returns 204 and a retry returns 404.

```json
{
 "correctAnswer": true
}
```

**Explanation:** The article defines idempotency in terms of final server state, not identical response codes. After the first DELETE, the resource is gone; after a retry, it is still gone, so the server state has not changed further.

## 15. [SENIOR · MULTIPLE_CHOICE] A client sends `POST /events/123/bookings`, the server creates the booking, but the client times out before receiving the response. Based on the article’s HTTP semantics, what is the safest API-design conclusion?

```json
{
 "options": [
  "The client can safely retry the same POST because HTTP guarantees POST requests are idempotent.",
  "A blind retry may create a duplicate booking unless the API adds some deduplication or idempotency mechanism.",
  "The endpoint should be converted to GET because GET requests are safer over unreliable networks.",
  "The second POST will necessarily return 404 because the booking already exists."
 ],
 "correctAnswer": 1
}
```

**Explanation:** The article emphasizes that POST is neither safe nor idempotent: repeated calls can create multiple resources. This matters specifically when networks fail and clients retry, such as duplicate ticket bookings after a timeout.
