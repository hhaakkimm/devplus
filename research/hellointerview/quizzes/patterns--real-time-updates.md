# Real-time Updates System Design Quiz

## 1. [JUNIOR · MULTIPLE_CHOICE] Which client update approach has the most expensive initial connection handshake but then offers full-duplex messaging?

```json
{
 "options": [
  "Simple polling",
  "Long polling",
  "WebSockets",
  "Server-Sent Events"
 ],
 "correctAnswer": 2
}
```

**Explanation:** WebSockets require an HTTP upgrade handshake to establish the connection and persistent TCP state, but once connected they enable bidirectional, low-latency messaging. Among these options, only WebSockets are full-duplex.

## 2. [JUNIOR · MULTIPLE_CHOICE] Which technique is the simplest baseline for delivering periodic updates to a client?

```json
{
 "options": [
  "Long polling",
  "Simple polling",
  "WebSockets",
  "Server-Sent Events (SSE)"
 ],
 "correctAnswer": 1
}
```

**Explanation:** Simple polling is the starting point: the client repeatedly asks the server for new data at a fixed interval.

## 3. [MID_LEVEL · TRUE_FALSE] When you add a new WebSocket server to a cluster using consistent hashing, most existing connections stay on their current servers.

```json
{
 "correctAnswer": true
}
```

**Explanation:** With consistent hashing, adding a server only remaps connections that fall into that server's portion of the hash ring (roughly 1/N of total). The other connections stay put, avoiding a thundering herd of reconnections and state rebuilding.

## 4. [MID_LEVEL · MULTIPLE_CHOICE] What is the primary drawback of simple polling compared to other real-time techniques discussed?

```json
{
 "options": [
  "Requires WebSocket support on both client and server",
  "Higher latency and wasted server load",
  "Works only with UDP",
  "Does not work behind firewalls"
 ],
 "correctAnswer": 1
}
```

**Explanation:** Because the client keeps asking even when nothing changed, simple polling adds latency equal to the polling interval and wastes resources.

## 5. [MID_LEVEL · MULTIPLE_CHOICE] You have a chat app where each application server caches 50MB of conversation history per connected user in its own memory. How should you route reconnecting users?

```json
{
 "options": [
  "Round-robin across all servers in the cluster",
  "Consistent hashing to the same server",
  "Random server selection",
  "Least-connections load balancing"
 ],
 "correctAnswer": 1
}
```

**Explanation:** With 50MB of state cached per user on the server, you want reconnecting users to land on the same server that already holds their data. Consistent hashing routes a given user to the same server consistently, avoiding the cost of reloading that state elsewhere.

## 6. [MID_LEVEL · MULTIPLE_CHOICE] You only need to push updates from server to client, with no client-to-server messages over the same channel. Why is SSE a reasonable choice over WebSockets here?

```json
{
 "options": [
  "SSE supports bidirectional binary messaging",
  "SSE runs over plain HTTP and the browser reconnects automatically",
  "SSE guarantees lower latency than WebSockets",
  "SSE bypasses firewalls by switching to UDP"
 ],
 "correctAnswer": 1
}
```

**Explanation:** When you only need server→client streaming, SSE rides plain HTTP and the browser's EventSource reconnects automatically, so you skip the upgrade handshake and connection management that WebSockets require. WebSockets earn their complexity when you also need client→server messaging on the same connection.

## 7. [MID_LEVEL · RANKING] Rank the extra wait these techniques can add before sending an update, shortest first. Assume SSE is connected, long polling has just returned a response, and the next simple poll is several seconds away.

```json
{
 "items": [
  "Simple polling",
  "Long polling",
  "Server-Sent Events (SSE)"
 ],
 "correctOrder": [
  2,
  1,
  0
 ]
}
```

**Explanation:** SSE can send another update on its open response immediately. Long polling must wait for the client’s next request, while simple polling waits for the stated multi-second interval. With a long-poll request already waiting, long polling can deliver an update as promptly as SSE, so this order depends on the stated timing.

## 8. [MID_LEVEL · TRUE_FALSE] Layer 7 HTTP proxies in the request path must understand the WebSocket upgrade handshake, but Layer 4 TCP load balancers can pass through WebSocket traffic without any special WebSocket support.

```json
{
 "correctAnswer": true
}
```

**Explanation:** L7 proxies operate at the HTTP layer and must understand the Upgrade header to properly handle WebSocket connections. L4 load balancers work at the TCP layer and simply pass through the TCP stream without inspecting HTTP headers, so they don't need WebSocket-specific support.

## 9. [MID_LEVEL · TRUE_FALSE] SSE streams can be buffered by misconfigured proxies, delaying updates to clients even though the server flushes chunks immediately.

```json
{
 "correctAnswer": true
}
```

**Explanation:** Proxies that don't support `Transfer-Encoding: chunked` may wait for the full response before forwarding, defeating streaming semantics.

## 10. [MID_LEVEL · TRUE_FALSE] Using a "least connections" strategy at the load balancer helps distribute WebSocket clients more evenly across endpoint servers.

```json
{
 "correctAnswer": true
}
```

**Explanation:** Since each connected client holds resources, balancing by current connection count prevents hotspots better than round-robin.

## 11. [SENIOR · MULTIPLE_CHOICE] A live dashboard has 1.2 million clients using simple polling. If the product accepts up to 10 seconds of update staleness and you set the polling interval to 10 seconds, what steady-state request rate does polling create even when there are no updates?

```json
{
 "options": [
  "12,000 requests/second",
  "60,000 requests/second",
  "120,000 requests/second",
  "1,200,000 requests/second"
 ],
 "correctAnswer": 2
}
```

**Explanation:** Simple polling creates load proportional to clients divided by polling interval: 1,200,000 / 10 = 120,000 requests per second. The key senior tradeoff is that this load exists even when responses are empty, so latency requirements directly translate into infrastructure cost.

## 12. [SENIOR · MULTIPLE_CHOICE] A WebSocket service uses Redis-style pub/sub as the second hop from event producers to WebSocket servers. Which failure mode must you account for if the system needs guaranteed delivery of updates?

```json
{
 "options": [
  "Messages published while a WebSocket server is disconnected may be missed unless there is a durable store or replay mechanism.",
  "The browser will automatically reconnect to Redis and fetch missed messages from the pub/sub channel.",
  "A Layer 4 load balancer will replay missed pub/sub messages to the same WebSocket server after it restarts.",
  "TCP guarantees that messages published during subscriber downtime are buffered indefinitely."
 ],
 "correctAnswer": 0
}
```

**Explanation:** Lightweight pub/sub is good for low-latency fanout, but it is often not durable: subscribers that are offline do not receive messages published during that window. If missed updates are unacceptable, the design needs a durable log, database-backed recovery, or replay path.

## 13. [SENIOR · TRUE_FALSE] With long polling and infrequent updates, the server usually keeps about one request open for each connected client.

```json
{
 "correctAnswer": true
}
```

**Explanation:** The server holds each client's request until an update arrives or the request times out, and the client immediately opens another request after the response. As a result, the number of open requests scales with connected clients even when updates are rare.

## 14. [SENIOR · MULTIPLE_CHOICE] You have 50 WebSocket servers, and each server polls the database once per second for updates relevant to its connected clients. If you double the number of WebSocket servers while the number of clients and event rate stay the same, what is the most important scaling consequence?

```json
{
 "options": [
  "Update latency is cut in half because there are twice as many pollers.",
  "Database polling load stays constant because each event is generated only once.",
  "Each WebSocket connection is automatically migrated to reduce duplicate database reads.",
  "The database sees roughly twice as many polling queries, even though useful work did not double."
 ],
 "correctAnswer": 3
}
```

**Explanation:** Server-side polling is simple, but every polling server contributes recurring read load. Scaling out WebSocket servers can therefore amplify database queries independently of actual event volume, which is why pub/sub or another routing layer is often introduced.

## 15. [SENIOR · TRUE_FALSE] For a WebSocket fleet behind a typical load balancer, adding new servers during a spike mainly helps with new connections; existing open sockets generally remain attached to their current servers unless clients reconnect or the system deliberately drains/rebalances them.

```json
{
 "correctAnswer": true
}
```

**Explanation:** Persistent connections are stateful: once a WebSocket is established, the load balancer has already chosen a backend for that connection. This means autoscaling does not automatically redistribute existing socket load, so overload from already-connected clients may require reconnect strategies, draining, or application-level sharding.
