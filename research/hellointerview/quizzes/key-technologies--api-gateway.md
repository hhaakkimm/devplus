# API Gateway

## 1. [JUNIOR · MULTIPLE_CHOICE] Which of these is NOT typically considered a middleware function of an API Gateway?

```json
{
 "options": [
  "Authentication using JWT tokens",
  "Rate limiting to prevent abuse",
  "Database transaction management",
  "SSL termination"
 ],
 "correctAnswer": 2
}
```

**Explanation:** Database transaction management is not a middleware function of an API Gateway. API Gateways handle cross-cutting concerns like authentication, rate limiting, SSL termination, logging, and caching, but not database-specific operations.

## 2. [JUNIOR · MULTIPLE_CHOICE] What is the primary function of an API Gateway?

```json
{
 "options": [
  "Data storage and persistence",
  "Routing requests to backend services",
  "User interface rendering and client-side hydration",
  "Database query optimization"
 ],
 "correctAnswer": 1
}
```

**Explanation:** The API Gateway's primary function is request routing – determining which backend service should handle each incoming request. While it also handles middleware, routing is the core reason you need an API Gateway.

## 3. [MID_LEVEL · MULTIPLE_CHOICE] When might an API Gateway handle protocol translation?

```json
{
 "options": [
  "When all services use the same HTTP protocol",
  "When backends use different protocols like gRPC",
  "When clients only send GET requests",
  "When responses are always in JSON format and need no transformation"
 ],
 "correctAnswer": 1
}
```

**Explanation:** API Gateways can handle protocol translation when backend services use different protocols like gRPC for internal communication while clients communicate via HTTP. This allows services to use the most efficient protocol internally.

## 4. [MID_LEVEL · MULTIPLE_CHOICE] A mobile client sends a malformed JSON body to an endpoint behind an API Gateway. Why is it useful for the gateway to reject this request during validation instead of forwarding it to a backend service?

```json
{
 "options": [
  "It guarantees the client will retry with exponential backoff.",
  "It avoids wasting backend resources on requests that are obviously invalid.",
  "It allows the gateway to permanently cache the failed request.",
  "It lets the backend service skip authentication for future requests."
 ],
 "correctAnswer": 1
}
```

**Explanation:** The article describes request validation as an early step where the gateway checks URLs, headers, and body format. Rejecting malformed requests at the gateway saves backend services from spending time on work that cannot succeed and lets the system return a clear error quickly.

## 5. [MID_LEVEL · TRUE_FALSE] Global distribution of API Gateways works similarly to CDN deployment strategies.

```json
{
 "correctAnswer": true
}
```

**Explanation:** True. Global distribution involves deploying API Gateway instances in multiple geographic regions closer to users, using DNS-based routing to direct users to the nearest gateway, similar to CDN strategies.

## 6. [MID_LEVEL · MULTIPLE_CHOICE] A company runs services on-premises and wants more control over its API Gateway rather than using the easiest cloud-provider-managed option. Which category of gateway from the article is the better fit?

```json
{
 "options": [
  "Open source solutions such as Kong, Tyk, or Express Gateway",
  "Fully managed cloud services such as AWS API Gateway only",
  "A CDN with no gateway functionality",
  "A single backend service exposed directly to all clients"
 ],
 "correctAnswer": 0
}
```

**Explanation:** The article says managed API Gateway services are easiest but also the most expensive and tied to cloud ecosystems. Open source gateways are presented as a better fit for teams that want more control or are running on-premises.

## 7. [MID_LEVEL · TRUE_FALSE] In a globally distributed API Gateway setup, using GeoDNS to route users to nearby gateways should be paired with keeping routing rules and policies synchronized across regions.

```json
{
 "correctAnswer": true
}
```

**Explanation:** GeoDNS can help send users to the closest regional gateway, reducing latency for globally distributed applications. But each region still needs consistent gateway configuration so requests are routed and handled the same way regardless of where they enter the system.

## 8. [MID_LEVEL · MULTIPLE_CHOICE] A user service returns data from an internal gRPC call, but public clients expect JSON over HTTP. Which API Gateway capability best fits this scenario?

```json
{
 "options": [
  "IP blacklisting",
  "Client-to-gateway load balancing",
  "Response transformation",
  "GeoDNS routing"
 ],
 "correctAnswer": 2
}
```

**Explanation:** Response transformation lets the gateway convert backend responses into the format requested by clients. This keeps the external API consistent while allowing internal services to use protocols or formats that are efficient for them.

## 9. [MID_LEVEL · TRUE_FALSE] A gateway builds a response from a product-description service and a live-inventory service. It can cache the stable description while fetching current inventory for each request.

```json
{
 "correctAnswer": true
}
```

**Explanation:** Caching the description avoids repeated calls to the description service until that entry expires or is invalidated. Inventory is still fetched separately, so the composed response can include fresh stock data.

## 10. [MID_LEVEL · TRUE_FALSE] API Gateways evolved primarily due to the rise of microservices architecture.

```json
{
 "correctAnswer": true
}
```

**Explanation:** True. The evolution of API Gateways parallels the rise of microservices architecture. As monolithic applications were broken down into smaller, specialized services, the need for a centralized point of control became evident.

## 11. [SENIOR · MULTIPLE_CHOICE] A company deploys API Gateways in us-east and eu-west and uses GeoDNS to send users to the nearest region. A new `/payments/*` route and an IP blacklist rule are deployed only to us-east. What is the primary failure mode this creates?

```json
{
 "options": [
  "All users will automatically fail over to us-east because GeoDNS detects the newer configuration.",
  "The backend payment service will receive duplicate requests from both regions.",
  "Users in different regions can see different routing and security behavior, so configuration and policies must be synchronized across gateway deployments.",
  "The gateway-to-service load balancer will stop working because it requires a single global gateway instance."
 ],
 "correctAnswer": 2
}
```

**Explanation:** For globally distributed gateways, the article explicitly calls out configuration synchronization as a requirement. If routes or policies differ by region, users can get inconsistent API behavior, and security controls such as blacklists may be applied unevenly.

## 12. [SENIOR · MULTIPLE_CHOICE] Your API Gateway layer is horizontally scaled to 10 stateless instances behind a load balancer. You enable full-response caching for public product catalog endpoints. Compared with using a distributed cache like Redis, what is the main tradeoff of keeping the cache in each gateway instance’s memory?

```json
{
 "options": [
  "It makes the gateway unable to scale horizontally because cached responses must be routed to a single instance.",
  "It can reduce lookup latency, but entries are duplicated across instances and cache hit rate/invalidation behavior depends on which gateway receives the request.",
  "It makes user-specific responses safe to cache because each gateway instance has a private cache.",
  "It removes the need for TTL or event-based invalidation because process restarts will eventually clear stale data."
 ],
 "correctAnswer": 1
}
```

**Explanation:** The article notes that gateway caches can be in memory or in a distributed cache. In-memory caching is fast, but with many gateway instances, each instance has its own cache, so hit rates and invalidation are harder to coordinate than with a shared cache like Redis.

## 13. [SENIOR · TRUE_FALSE] Eight API Gateway instances sit behind a load balancer. If each independently applies a 100 requests/second per-client limit using an in-memory counter, one client can exceed 100 requests/second overall when its traffic is spread across instances.

```json
{
 "correctAnswer": true
}
```

**Explanation:** Each instance sees only its own counter, so the client can consume part of the limit on several gateways and exceed 100 requests/second in aggregate. A global limit needs coordination through shared state or routing that consistently sends the client to one instance.

## 14. [SENIOR · MULTIPLE_CHOICE] Four gateway instances each handle up to 5,000 requests/second. All four route `/users/*` requests to the same shared pool of six user-service instances, each handling up to 2,000 requests/second. With one backend request per incoming request, even load distribution, and no caching or other traffic, what is the maximum sustainable rate?

```json
{
 "options": [
  "5,000 requests/second, because a single gateway instance is the limiting unit.",
  "20,000 requests/second, because the gateway tier is the only tier that matters for ingress capacity.",
  "24,000 requests/second, because gateway and service capacities are additive.",
  "12,000 requests/second, because the user-service tier saturates before the gateway tier."
 ],
 "correctAnswer": 3
}
```

**Explanation:** The gateway tier can handle 4 × 5,000 = 20,000 requests/second. The user-service tier can handle only 6 × 2,000 = 12,000 requests/second, so the backend service pool becomes the bottleneck first.

## 15. [SENIOR · TRUE_FALSE] If an API Gateway caches full responses for a route whose behavior depends on request headers or query parameters, using only the URL path as the cache key can return incorrect responses to some clients.

```json
{
 "correctAnswer": true
}
```

**Explanation:** The article notes that routing can depend on URL paths, HTTP methods, query parameters, and request headers, and that caching is appropriate when the same request input should produce the same result. If headers or query parameters affect routing or response content, they are part of the effective input. Omitting them from the cache key can cause one client's response variant to be served to another client.
