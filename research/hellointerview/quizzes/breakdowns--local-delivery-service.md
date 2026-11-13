# Gopuff System Design Quiz

## 1. [JUNIOR · MULTIPLE_CHOICE] All of the following improve database read performance EXCEPT:

```json
{
 "options": [
  "Read replicas distributed across availability zones",
  "Query caching",
  "Write-ahead logging",
  "Index optimization"
 ],
 "correctAnswer": 2
}
```

**Explanation:** Write-ahead logging improves write durability and recovery but doesn't enhance read performance. Read replicas, caching, and indexes all directly improve read operations.

## 2. [JUNIOR · TRUE_FALSE] According to CAP theorem, a distributed system can simultaneously guarantee consistency, availability, and partition tolerance.

```json
{
 "correctAnswer": false
}
```

**Explanation:** CAP theorem states you can achieve at most two of these three properties. During network partitions, systems must choose between consistency (CP systems) or availability (AP systems). Partition tolerance is mandatory in distributed systems since network failures are inevitable.

## 3. [MID_LEVEL · MULTIPLE_CHOICE] A Gopuff-like system sells “Cheetos” from many distribution centers. Why should it model Item separately from Inventory?

```json
{
 "options": [
  "Because Item records should store the customer’s delivery address, while Inventory records store product descriptions.",
  "Because Item is the catalog product type, while Inventory represents stock of that item at a specific distribution center.",
  "Because Item should be stored only in a cache, while Inventory must be stored only in an external travel-time service.",
  "Because Item is used only after checkout, while Inventory is used only for search ranking."
 ],
 "correctAnswer": 1
}
```

**Explanation:** Customers care about item types like “Cheetos,” but the system must track where physical stock exists. Separating Item from Inventory lets the availability service sum inventory across nearby distribution centers for the same catalog item.

## 4. [MID_LEVEL · TRUE_FALSE] In the Gopuff design, the Nearby Service can skip calling the travel time service for any DC outside a fixed radius (such as 60 miles), because no DC beyond that distance could be reached within 1 hour.

```json
{
 "correctAnswer": true
}
```

**Explanation:** The radius is set to the most optimistic distance a driver could cover in 1 hour, so anything outside it can be ruled out with a cheap local distance check. Only the remaining nearby DCs are sent to the external travel time service, which avoids wasting expensive calls on DCs that could never meet the 1-hour delivery requirement.

## 5. [MID_LEVEL · TRUE_FALSE] Separating the product catalog from inventory storage can be a good design choice because catalog/search traffic and inventory update traffic often have different workloads.

```json
{
 "correctAnswer": true
}
```

**Explanation:** The article notes that many e-commerce systems store catalog data separately from inventory because they serve different consumers and access patterns. Catalog data is often optimized for browsing/search, while inventory must reflect location-specific stock changes and ordering consistency.

## 6. [MID_LEVEL · MULTIPLE_CHOICE] When determining if a location is within delivery range, which approach minimizes expensive external API calls (like travel time estimation)?

```json
{
 "options": [
  "Filter by distance first, then call travel time API",
  "Call travel time API for every location in the coverage area",
  "Sort locations in the database",
  "Scan through all locations without filtering"
 ],
 "correctAnswer": 0
}
```

**Explanation:** Two-phase filtering first applies a cheap local check (simple distance calculation) to eliminate obviously distant candidates, then calls the expensive travel time API only for locations that pass the first filter. This drastically reduces API costs.

## 7. [MID_LEVEL · MULTIPLE_CHOICE] The availability API already returned items near a user. Why should the order API still include the user’s location?

```json
{
 "options": [
  "So the order service can choose a different product catalog schema for each city.",
  "So the client can skip sending item IDs during checkout.",
  "So payments can be processed by the nearest distribution center.",
  "So the backend can re-confirm the ordered inventory is deliverable within 1 hour before accepting the order."
 ],
 "correctAnswer": 3
}
```

**Explanation:** The article notes that location is passed to both APIs because the backend must verify availability close enough to the user before processing an order. This avoids trusting a prior read or client-side state when the user’s location or serviceable distribution centers may need to be checked again.

## 8. [MID_LEVEL · MULTIPLE_CHOICE] A system serves location-based queries across continents. Which partitioning strategy works best?

```json
{
 "options": [
  "Geographic sharding",
  "Hash partitioning",
  "Round-robin distribution",
  "Timestamp-based splitting"
 ],
 "correctAnswer": 0
}
```

**Explanation:** Geographic sharding colocates related data by region, ensuring location-based queries typically access only local partitions rather than scanning globally distributed data.

## 9. [MID_LEVEL · TRUE_FALSE] Travel time estimation services provide more accurate delivery zones than simple distance calculations.

```json
{
 "correctAnswer": true
}
```

**Explanation:** Travel time services account for real-world factors like traffic, road conditions, and geographic barriers, providing more accurate delivery feasibility than straight-line distance calculations that ignore these constraints.

## 10. [MID_LEVEL · MULTIPLE_CHOICE] Which technique is MOST effective for preventing concurrent resource allocation conflicts?

```json
{
 "options": [
  "Atomic transactions",
  "Load balancing across multiple regions",
  "Horizontal scaling",
  "Cache warming"
 ],
 "correctAnswer": 0
}
```

**Explanation:** Atomic transactions ensure that resource checks and allocations happen as an indivisible unit, preventing race conditions where multiple processes might allocate the same resource simultaneously.

## 11. [SENIOR · MULTIPLE_CHOICE] In the Gopuff design, why doesn't stale cached inventory data lead to overselling during concurrent orders?

```json
{
 "options": [
  "Orders are validated through a SERIALIZABLE transaction on the primary database",
  "The cache is updated synchronously before every order",
  "Read replicas always have the latest data",
  "Distributed locks prevent concurrent access to inventory"
 ],
 "correctAnswer": 0
}
```

**Explanation:** The design separates read and write consistency. Cached data may show slightly stale quantities, but order processing uses a SERIALIZABLE transaction on the Postgres leader that atomically checks inventory and records the order. If inventory is already claimed, the transaction fails rather than overselling.

## 12. [SENIOR · MULTIPLE_CHOICE] Given the stated scale of 10k distribution centers and 100k catalog items, which storage/query pattern is the best fit for the availability API’s <100ms target?

```json
{
 "options": [
  "Store one row per catalog item per distribution center and scan all 1B combinations on each availability request.",
  "First find serviceable DCs, then query indexed inventory rows for only those DCs and aggregate quantities by item.",
  "Call the travel-time service once per catalog item and return items whose nearest DC is reachable in under 1 hour.",
  "Replicate the full orders table into the availability service and infer current inventory by replaying all historical orders."
 ],
 "correctAnswer": 1
}
```

**Explanation:** At 10k × 100k, a full DC-item matrix would be around one billion combinations before considering quantity changes, which is not compatible with a sub-100ms read path. The article’s design narrows the problem first by nearby DCs, then aggregates inventory for that much smaller candidate set.

## 13. [SENIOR · MULTIPLE_CHOICE] Two users concurrently place multi-item orders: User 1 needs items A and B, while User 2 needs items B and A. In a locking-based inventory design, which implementation choice best reduces the deadlock risk described in the article?

```json
{
 "options": [
  "Acquire all inventory locks in a deterministic global order, such as sorting by inventory ID before locking.",
  "Use read replicas for the inventory checks so both users see the same availability snapshot.",
  "Lock the order row first, then lock inventory rows in the order requested by the client.",
  "Increase the availability cache TTL so fewer inventory rows are queried during checkout."
 ],
 "correctAnswer": 0
}
```

**Explanation:** Deadlock can occur when concurrent transactions acquire overlapping locks in different orders. A deterministic lock ordering prevents circular wait, which is one of the necessary conditions for deadlock.

## 14. [SENIOR · MULTIPLE_CHOICE] The design mentions a two-datastore approach where the order service locks inventory records, creates an order, decrements inventory, then releases the lock. If the service crashes after creating the order but before decrementing inventory, what is the core correctness problem?

```json
{
 "options": [
  "The availability API may become slower because the order table has an extra unindexed row.",
  "The system has recorded a successful order without reserving the corresponding physical inventory, allowing a later order to sell the same item.",
  "The distributed lock will necessarily remain held forever, making all future orders impossible.",
  "The item catalog becomes inconsistent because item metadata and inventory are stored in different schemas."
 ],
 "correctAnswer": 1
}
```

**Explanation:** The dangerous failure is not just latency or schema inconsistency; it is a broken atomicity boundary across order creation and inventory mutation. Because the order and inventory updates are not committed together, the system can promise inventory to one user while still showing it as available to another.

## 15. [SENIOR · TRUE_FALSE] An order request can rely on the availability result previously shown to the client; recomputing the serviceable distribution centers during checkout mainly adds latency rather than correctness value.

```json
{
 "correctAnswer": false
}
```

**Explanation:** The article explicitly passes location to both availability and ordering because the backend must confirm that inventory is still close enough to deliver within 1 hour. Availability is a read-side hint that may become stale or may have been computed before conditions changed, while the order path is the consistency boundary that must revalidate deliverability and reserve inventory.
