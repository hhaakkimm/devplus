# Consistent Hashing System Design Quiz

## 1. [JUNIOR · TRUE_FALSE] Production hash rings typically use a hash space of 0 to 2^32-1 or larger, not 0 to 100.

```json
{
 "correctAnswer": true
}
```

**Explanation:** Real hash rings use large hash spaces (commonly 2^32 or 2^128) to minimize the chance of collisions and ensure even distribution. The 0-100 range you see in diagrams is just for educational illustrations.

## 2. [JUNIOR · MULTIPLE_CHOICE] What is the main problem that consistent hashing solves?

```json
{
 "options": [
  "Slow database queries due to inefficient indexing",
  "Minimizing data movement when nodes change",
  "Reducing memory usage",
  "Improving data compression"
 ],
 "correctAnswer": 1
}
```

**Explanation:** Consistent hashing's primary benefit is minimizing data redistribution when nodes are added or removed from a distributed system. Only a small fraction of data needs to move, unlike simple modulo hashing.

## 3. [MID_LEVEL · TRUE_FALSE] In basic consistent hashing without virtual nodes, adding a new node to the ring takes a slice of keys away from exactly one existing node -- its clockwise successor.

```json
{
 "correctAnswer": true
}
```

**Explanation:** Keys are assigned to the first node found walking clockwise, so a new node lands in the gap between two existing nodes and takes over the keys that fall just before it. Those keys used to walk clockwise past that spot to the next node -- the new node's clockwise successor -- so that single successor hands off a slice while every other node stays untouched. With virtual nodes the new node occupies many ring positions at once, so it pulls small slices from many successors instead of just one.

## 4. [MID_LEVEL · MULTIPLE_CHOICE] In a cluster of 10 nodes using consistent hashing with enough virtual nodes for an even distribution, roughly what fraction of the total data has to move when you add an 11th node?

```json
{
 "options": [
  "About 1/11 of the data (the new node's share)",
  "About 1/10 of the data",
  "Roughly half of the data",
  "Roughly 90% of the data"
 ],
 "correctAnswer": 0
}
```

**Explanation:** With an even distribution, the 11th node ends up owning about 1/11 of the keyspace, so about 1/11 of the data moves to it and the rest stays put. (Without virtual nodes the exact amount depends on where the new node lands on the ring -- one of the reasons virtual nodes are used is to make rebalancing both even and predictable.)

## 5. [MID_LEVEL · TRUE_FALSE] When using consistent hashing, adding a new node to a cluster still requires moving some data, but far less than with modulo hashing.

```json
{
 "correctAnswer": true
}
```

**Explanation:** Consistent hashing minimizes data redistribution but doesn't eliminate it. When a new node joins, it takes over a portion of the keyspace — roughly 1/N of the total data moves to the new node. This is dramatically better than modulo hashing, where changing N causes roughly (N-1)/N of keys to remap.

## 6. [MID_LEVEL · TRUE_FALSE] With modulo hashing, adding one database to a cluster of 10 databases would require moving roughly 90% of the data.

```json
{
 "correctAnswer": true
}
```

**Explanation:** A key stays put only if `hash(key) % 10` equals `hash(key) % 11`, which happens only when `hash(key) % 110` is between 0 and 9 -- that's 10 out of every 110 hash values, or 1/11 of keys. The other 10/11 (about 91%, i.e. roughly 90%) land on a different database and must move. Consistent hashing would move only the new node's ~1/11 share; plain modulo reshuffles nearly everything, which is why it's a bad fit for clusters that change size.

## 7. [MID_LEVEL · TRUE_FALSE] After a CDN routes a request to the appropriate edge location, consistent hashing is commonly used to pick which edge server there caches the requested content.

```json
{
 "correctAnswer": true
}
```

**Explanation:** CDNs first route the user to an appropriate edge location based on geography and latency. Within that location, consistent hashing can map a content key to one cache server so repeat requests hit the same place, and when servers are added or removed only a small fraction of keys need to move.

## 8. [MID_LEVEL · MULTIPLE_CHOICE] A physical server occupies 100 virtual-node positions on the hash ring. When it fails, where does its data go, and how does that compare to a server that occupied a single position?

```json
{
 "options": [
  "It all lands on one clockwise neighbor, exactly as it would for a single-position server, since a failed node has one successor",
  "Less total data has to move off the failed server than in the single-position case",
  "The load spreads across many servers, whereas a single-position server would overload one neighbor",
  "Nothing changes; virtual nodes don't affect how a failed server's data is redistributed"
 ],
 "correctAnswer": 2
}
```

**Explanation:** Each of the failed server's 100 positions has its own clockwise successor, so its keys are parceled out to many different servers rather than piling onto one. A server with a single ring position hands its entire range to just one neighbor, which can overload it. The total amount of data moved is about the same in both cases -- virtual nodes change who absorbs the load, not how much moves.

## 9. [MID_LEVEL · TRUE_FALSE] In basic consistent hashing without virtual nodes, when a node is removed, all of its keys move to a single other node (its clockwise successor).

```json
{
 "correctAnswer": true
}
```

**Explanation:** Without virtual nodes, a removed node's entire key range falls to just one node -- the next one clockwise. That's minimal disruption to the rest of the ring, but it can overload that one successor. Virtual nodes fix this: each physical node sits at many ring positions, so a failure's load spreads across many successors instead of one.

## 10. [MID_LEVEL · MULTIPLE_CHOICE] Which scenario would benefit MOST from consistent hashing?

```json
{
 "options": [
  "Single database with high CPU usage that needs vertical scaling",
  "Distributed cache with frequent node changes",
  "Static website hosting",
  "Local file storage"
 ],
 "correctAnswer": 1
}
```

**Explanation:** Distributed caches with frequent node changes (scaling up/down, failures, maintenance) benefit most from consistent hashing because it minimizes cache invalidation and data movement during these common operational events.

## 11. [SENIOR · TRUE_FALSE] In a DynamoDB- or Cassandra-style design that combines replication with consistent hashing, permanently adding capacity or replacing a node can still require copying data, but the copying is limited to affected key ranges rather than a full cluster-wide reshuffle.

```json
{
 "correctAnswer": true
}
```

**Explanation:** Consistent hashing determines the new ownership ranges after membership changes, but it does not eliminate the need to re-replicate data when capacity is added or a failed node is permanently replaced. The benefit is that only a bounded fraction of keys are affected, unlike modulo hashing where changing the node count can remap most keys.

## 12. [SENIOR · MULTIPLE_CHOICE] A cluster uses consistent hashing with many virtual nodes and has an even key distribution. One celebrity event suddenly receives 100x more read traffic than any other event, and the physical node owning that event becomes overloaded. Which change directly addresses the failure mode described in the article?

```json
{
 "options": [
  "Add more virtual nodes per physical server so the hot event is split across more ring positions.",
  "Replicate the hot event to multiple nodes and load-balance reads across those replicas.",
  "Increase the hash ring size from 0..100 to 0..2^32-1 so the hot event hashes more uniformly.",
  "Move from consistent hashing back to modulo hashing so the hot key is recalculated on each request."
 ],
 "correctAnswer": 1
}
```

**Explanation:** Virtual nodes improve structural balance: how many keys or ranges each server owns. They do not split traffic for a single extremely popular key, so hot keys need workload-level techniques such as read replicas or salting.

## 13. [SENIOR · MULTIPLE_CHOICE] In a DynamoDB- or Cassandra-like system that combines consistent hashing with replication across three availability zones, what should happen immediately after one primary node fails?

```json
{
 "options": [
  "All keys owned by the failed node are synchronously moved to its clockwise successor before reads can resume.",
  "The system changes the hash function so affected keys are redistributed evenly across every surviving node.",
  "A surviving replica is promoted or used to serve traffic, avoiding immediate bulk data movement.",
  "The failed node's virtual nodes are deleted and their data is copied from clients' next write requests."
 ],
 "correctAnswer": 2
}
```

**Explanation:** The article emphasizes that consistent hashing defines placement, but it does not magically move terabytes during a failure. Replicated systems usually serve from or promote replicas immediately; bulk movement is more associated with planned capacity changes or permanent replacement to restore replication.

## 14. [SENIOR · TRUE_FALSE] Key-space salting can spread one logical hot key across the hash ring by hashing suffixed physical keys such as `taylor-swift-0` through `taylor-swift-9` instead of repeatedly hashing the unchanged key.

```json
{
 "correctAnswer": true
}
```

**Explanation:** The article's salting technique creates distinct physical keys by appending suffixes before hashing, so the variants can land on different nodes. Hashing the same unchanged key repeatedly would always select the same ring position and would not distribute the hot spot.

## 15. [SENIOR · MULTIPLE_CHOICE] A team is choosing between a hash-ring design and Redis Cluster's fixed hash-slot design. Based on the article, which trade-off is accurate for fixed hash slots?

```json
{
 "options": [
  "They are simpler to reason about, but rebalancing requires more coordination.",
  "They eliminate the need to move data when nodes are added or removed.",
  "They prevent hot spots because each slot automatically tracks request volume.",
  "They are equivalent to modulo hashing over the current number of nodes."
 ],
 "correctAnswer": 0
}
```

**Explanation:** Redis Cluster uses a fixed number of slots, such as 16,384, and assigns slot ranges to nodes. This can be simpler operationally to understand, but moving slots during rebalancing requires coordination; it is not the same as `key % number_of_nodes`.
