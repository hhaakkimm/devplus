# Networking Essentials System Design Quiz

## 1. [JUNIOR · MULTIPLE_CHOICE] Which protocol prioritizes speed over reliability?

```json
{
 "options": [
  "UDP",
  "TCP",
  "HTTP",
  "HTTPS"
 ],
 "correctAnswer": 0
}
```

**Explanation:** UDP provides connectionless, best-effort delivery with minimal overhead, making it faster than TCP but without reliability guarantees. This trade-off suits real-time applications where speed matters more than perfect delivery.

## 2. [JUNIOR · TRUE_FALSE] Server-Sent Events enable bidirectional real-time communication between clients and servers.

```json
{
 "correctAnswer": false
}
```

**Explanation:** Server-Sent Events only support server-to-client communication, not bidirectional. While they enable real-time push notifications, clients must use separate HTTP requests to send data to servers. WebSockets provide true bidirectional communication.

## 3. [MID_LEVEL · TRUE_FALSE] When a service sends its messages over UDP, the transport layer does not put out-of-order datagrams back in sequence or discard duplicate datagrams before handing them to the application.

```json
{
 "correctAnswer": true
}
```

**Explanation:** UDP is connectionless and provides no delivery, ordering, or duplicate-protection guarantees, so datagrams reach the application in whatever order and quantity the network delivers them. A service that needs ordered, duplicate-free processing over UDP has to add its own sequence numbers and deduplication, or it can switch to TCP, which provides those guarantees in the transport layer.

## 4. [MID_LEVEL · MULTIPLE_CHOICE] For a conservative system design interview answer, why might you choose TCP over QUIC for a general web service even though QUIC has modern performance benefits?

```json
{
 "options": [
  "QUIC does not provide end-to-end communication",
  "TCP has broader baseline adoption and is more universally supported",
  "TCP is connectionless, so it avoids handshakes",
  "QUIC only works for DNS traffic"
 ],
 "correctAnswer": 1
}
```

**Explanation:** The article describes QUIC as a newer protocol with TCP-like benefits and performance improvements, but not yet as ubiquitous. For many interview designs, TCP is the safer default because it is widely adopted and well understood.

## 5. [MID_LEVEL · MULTIPLE_CHOICE] A client must keep retrying requests to a service recovering from an outage. Which retry strategy reduces load on the service while still eventually delivering the requests?

```json
{
 "options": [
  "Immediate retry with no delay",
  "Exponential backoff with jitter",
  "Fixed short intervals between every attempt",
  "Abandon the requests without retrying"
 ],
 "correctAnswer": 1
}
```

**Explanation:** Exponential backoff progressively increases the delay between retries, so a recovering service isn't hit with a flood of requests, and jitter randomizes those delays to prevent synchronized clients from creating a thundering herd. Immediate or fixed-interval retries keep hammering the service, and abandoning the requests avoids load but never delivers them, which defeats the purpose of retrying.

## 6. [MID_LEVEL · MULTIPLE_CHOICE] Why can round-robin load balancing produce uneven server load when connections are long-lived and persistent?

```json
{
 "options": [
  "New connections are dispatched evenly, but long-lived ones accumulate unequally across servers",
  "Every request is forced to reuse a single shared server connection",
  "All persistent connections are pinned to the least-loaded server",
  "Latency increases because each server receives identical traffic"
 ],
 "correctAnswer": 0
}
```

**Explanation:** Round-robin assigns each new connection to the next server in turn, so brand-new connections are spread evenly. But because persistent connections stay open for different lengths of time, servers gradually accumulate unequal numbers of active connections, creating imbalanced load. Least-connections balancing avoids this by routing each connection to whichever server currently has the fewest active connections.

## 7. [MID_LEVEL · MULTIPLE_CHOICE] A service sends many short HTTP/1.1 requests, one after another, to a single backend server. Each request currently opens a new TCP connection. Which change removes the TCP handshake from most of these requests?

```json
{
 "options": [
  "Cache the backend's DNS lookup so its IP address resolves without a network call",
  "Increase the TCP receive window so responses arrive in fewer round trips",
  "Enable HTTP keep-alive so later requests reuse the open TCP connection",
  "Route the requests through a Layer 4 load balancer in front of the server"
 ],
 "correctAnswer": 2
}
```

**Explanation:** Every new TCP connection costs a three-way handshake before the HTTP request can be sent. HTTP keep-alive leaves the connection open after a response, so later requests to the same server skip the handshake entirely. DNS caching removes lookup time rather than connection setup, a larger receive window only helps transfers that span many round trips, and a Layer 4 load balancer still needs a connection per request.

## 8. [MID_LEVEL · TRUE_FALSE] Circuit breakers prevent cascading failures by temporarily blocking requests to failing services.

```json
{
 "correctAnswer": true
}
```

**Explanation:** Circuit breakers monitor service health and 'trip' when failures exceed a threshold, blocking requests to give failing services time to recover. This prevents cascading failures and reduces system-wide impact.

## 9. [MID_LEVEL · MULTIPLE_CHOICE] You assign a server the private IP address 10.0.0.5 inside your own network. Why can’t users on the public internet directly route traffic to it?

```json
{
 "options": [
  "TCP only supports public IP addresses",
  "Private IP addresses are not globally routable by internet routing infrastructure",
  "DNS cannot resolve names to private IP addresses",
  "UDP packets cannot cross network boundaries"
 ],
 "correctAnswer": 1
}
```

**Explanation:** Private IPs can be used inside a network, but the public internet is not configured to route traffic to arbitrary private address ranges. Internet-facing services need routable public IPs or an intermediary such as NAT or a load balancer with a public address.

## 10. [MID_LEVEL · TRUE_FALSE] HTTP is a stateless protocol, so the protocol itself keeps no memory of previous requests between a client and server.

```json
{
 "correctAnswer": true
}
```

**Explanation:** HTTP treats each request independently - the protocol carries no built-in memory of earlier requests. Applications often layer session state on top (for example a cookie plus a shared session store), but that state lives in the application, not the protocol. This protocol-level statelessness is what makes it easy to route requests across a pool of servers, as long as any session state the application needs is shared between them.

## 11. [SENIOR · MULTIPLE_CHOICE] A team runs a service on machines in a private network and assigns them arbitrary non-routable IP addresses. They add a public DNS record pointing directly to one of those private IPs; clients inside the network can connect, but internet users cannot. What is the best explanation?

```json
{
 "options": [
  "DNS can only resolve names for public cloud providers, not private networks.",
  "TCP requires a three-way handshake, and private IPs do not support TCP handshakes.",
  "DNS may return the IP, but internet routing infrastructure will not know how to deliver packets to an arbitrary non-routable private address.",
  "HTTP is stateless, so the server must use a load balancer before public clients can connect."
 ],
 "correctAnswer": 2
}
```

**Explanation:** DNS only maps a name to an IP address; it does not make that IP globally reachable. For internet clients to reach a machine, the address must be routable via public internet routing infrastructure, typically using allocated public IPs or an internet-facing proxy/load balancer.

## 12. [SENIOR · MULTIPLE_CHOICE] A realtime mobile app sends frequent position updates where old updates become useless once a newer one arrives. The team considers switching from UDP to TCP to avoid packet loss. On lossy networks, what is the most important failure mode this can introduce?

```json
{
 "options": [
  "TCP may delay newer position updates behind retransmission of an older lost packet because it preserves reliable, in-order delivery.",
  "TCP packets cannot include source and destination ports, making it impossible to route replies to the right application.",
  "TCP will deliver packets faster than the application can process because it has no flow control.",
  "TCP prevents clients from maintaining persistent connections, so every update requires a new DNS lookup."
 ],
 "correctAnswer": 0
}
```

**Explanation:** TCP’s reliability and ordering guarantees are useful for many applications, but they can hurt realtime streams where stale data should be skipped. A lost packet can force later data to wait until retransmission succeeds, while UDP allows the application to accept loss and process newer updates immediately.

## 13. [SENIOR · TRUE_FALSE] For a protocol running over TCP, a timeout can still be necessary at the application level because TCP’s reliability mechanisms do not guarantee that a remote service will respond within a useful deadline.

```json
{
 "correctAnswer": true
}
```

**Explanation:** TCP provides delivery, ordering, and flow-control semantics for bytes between endpoints, but it does not make the server fast or healthy. In system design, treating network calls as bounded by deadlines is important because retries, circuit breakers, and fallbacks depend on distinguishing slow failure from useful work.

## 14. [SENIOR · MULTIPLE_CHOICE] A client must issue 200 sequential tiny HTTP requests to the same host over TCP. Assume establishing a new TCP connection adds one round trip (RTT = 50 ms) of latency before that connection's first request can be sent; server processing is negligible, DNS is already cached, and teardown cost is ignored. Compared with opening a fresh connection for every request, how much total latency does HTTP keep-alive eliminate by reusing a single connection for all 200 requests?

```json
{
 "options": [
  "50 ms",
  "5,000 ms",
  "9,950 ms",
  "19,900 ms"
 ],
 "correctAnswer": 2
}
```

**Explanation:** The handshake adds one round trip before a connection's first request can go out — the client sends its request right after receiving the SYN-ACK, so the final ACK doesn't add to time-to-first-byte. Opening a fresh connection per request pays that 50 ms setup 200 times, while keep-alive pays it only once, so exactly 199 × 50 ms = 9,950 ms is eliminated. The total is not 10,000 ms because the keep-alive connection still pays its one setup, and it is not 19,900 ms because the handshake costs one round trip here, not two.

## 15. [SENIOR · TRUE_FALSE] Choosing UDP for a realtime stream can reduce connection setup and retransmission overhead, but the application may need to tolerate duplicate, missing, or out-of-order updates itself.

```json
{
 "correctAnswer": true
}
```

**Explanation:** UDP is connectionless and adds very little on top of IP, which makes it attractive when speed matters more than reliable delivery. The tradeoff is that delivery, ordering, and duplicate protection are not provided by the transport layer, so the application protocol must either handle those cases or be designed so they are acceptable.
