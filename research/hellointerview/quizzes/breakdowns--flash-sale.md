# Flash Sale System Design Quiz

## 1. [JUNIOR · TRUE_FALSE] In the payment flow, the Sale Service updates the Purchase and Reservation after Stripe sends the payment-result webhook.

```json
{
 "correctAnswer": true
}
```

**Explanation:** Stripe handles the payment details and reports the final result through a webhook. A successful webhook marks the Purchase as COMPLETE and the Reservation as PURCHASED.

## 2. [JUNIOR · TRUE_FALSE] A reservation is a temporary claim on inventory that gives a user time to complete payment.

```json
{
 "correctAnswer": true
}
```

**Explanation:** A reservation removes a unit from general availability for a limited window without treating it as purchased. This lets the user complete a multi-second payment flow without holding an open database transaction.

## 3. [MID_LEVEL · MULTIPLE_CHOICE] How does the signed admission token stop a client from bypassing the waiting room?

```json
{
 "options": [
  "It stores the client's payment details until inventory is available",
  "It proves the waiting room admitted that user for that product before the gateway forwards the reservation request",
  "It locks a ReservationUnit row for the entire time the user waits",
  "It replaces authentication with a public queue position"
 ],
 "correctAnswer": 1
}
```

**Explanation:** The waiting room issues a short-lived token containing claims such as user, product, and expiration. The gateway verifies its signature locally, so a caller cannot invent a valid admission or jump directly to the Sale Service.

## 4. [MID_LEVEL · TRUE_FALSE] Rejecting excess reservation traffic with 429 responses can cause a thundering herd when many clients retry together.

```json
{
 "correctAnswer": true
}
```

**Explanation:** A gateway rate limit protects the database, but rejected clients tend to retry around the same time. Their synchronized retries create another spike and repeat the overload pattern.

## 5. [MID_LEVEL · MULTIPLE_CHOICE] Why is polling GET /purchases/:purchaseId a reasonable way to wait for the Stripe webhook in this design?

```json
{
 "options": [
  "Polling makes the payment processor send its webhook sooner",
  "Every visitor to the sale page polls the endpoint at the same time",
  "Polling keeps the inventory transaction open until payment settles",
  "The polling group is limited to reservation holders and the wait lasts a few seconds"
 ],
 "correctAnswer": 3
}
```

**Explanation:** The polling population is a few thousand reservation holders rather than the millions viewing the sale. For a short wait, a simple request every second is cheap enough and avoids the complexity of a pushed connection.

## 6. [MID_LEVEL · TRUE_FALSE] Adding more Sale Service instances removes the contention caused by every reservation updating the same Product row.

```json
{
 "correctAnswer": false
}
```

**Explanation:** More application instances still converge on the same database row. The database has to serialize dependent decrements, so the hot row remains the throughput bottleneck.

## 7. [MID_LEVEL · RANKING] Order the ReservationUnit claim steps from first to last:

```json
{
 "items": [
  "Delete the claimed unit and insert its Reservation with an expiresAt timestamp",
  "Commit the transaction",
  "Select a unit with FOR UPDATE SKIP LOCKED",
  "Return sold out if no row came back; otherwise continue"
 ],
 "correctOrder": [
  2,
  3,
  0,
  1
 ]
}
```

**Explanation:** The transaction first locks an available unit, and an empty result means the product is sold out. With a unit in hand, it deletes the unit and inserts the Reservation (their relative order doesn't matter inside the transaction), then commits so the claim and reservation become visible atomically.

## 8. [MID_LEVEL · MULTIPLE_CHOICE] Before a delayed expiration worker returns a unit to inventory, what should it verify?

```json
{
 "options": [
  "The waiting room has no queued users",
  "The Purchase has been retried at least once",
  "The Reservation is ACTIVE and its expiresAt time has passed",
  "The Product inventory count is already above zero"
 ],
 "correctAnswer": 2
}
```

**Explanation:** A delayed message may arrive after a purchase completed or may be delivered more than once. Checking both status and expiration makes the transaction safe when jobs are late, retried, or duplicated.

## 9. [MID_LEVEL · MULTIPLE_CHOICE] Why should the request that reclaims a batch of expired reservations keep one reclaimed unit for itself?

```json
{
 "options": [
  "It avoids releasing every unit and then racing other buyers to claim one",
  "It guarantees that every expired reservation becomes a completed purchase",
  "It lets the request bypass the transaction-scoped reclamation lock",
  "It prevents the remaining units from returning to the ReservationUnit pool"
 ],
 "correctAnswer": 0
}
```

**Explanation:** The buyer triggered reclamation because the available pool was empty. Keeping one unit lets that request make progress, while the rest of the reclaimed batch replenishes the normal pool for waiting buyers.

## 10. [MID_LEVEL · MULTIPLE_CHOICE] Which operation grouping preserves the inventory invariant when creating a reservation?

```json
{
 "options": [
  "Decrement inventory, commit, and insert the Reservation in a later request",
  "Claim inventory and insert the Reservation in the same database transaction",
  "Insert the Reservation in Postgres and decrement inventory asynchronously in Redis",
  "Read the inventory count on the client before submitting a Reservation"
 ],
 "correctAnswer": 1
}
```

**Explanation:** The inventory claim and Reservation insert represent one logical state change. Committing them together prevents a crash from consuming a unit without recording its owner or creating a reservation without consuming inventory.

## 11. [SENIOR · MULTIPLE_CHOICE] Which ordering policy gives on-time users a fair chance without letting late arrivals cut ahead?

```json
{
 "options": [
  "Use FIFO from the moment the waiting room opens before the sale",
  "Randomize users present at the sale start, then append later arrivals in FIFO order",
  "Randomize the entire queue again whenever a new user arrives",
  "Order users by the latency of their reservation request"
 ],
 "correctAnswer": 1
}
```

**Explanation:** Randomizing the pre-sale group removes the advantage of joining a few milliseconds earlier or having a faster network. After the sale begins, FIFO prevents later arrivals from displacing users already waiting.

## 12. [SENIOR · MULTIPLE_CHOICE] A commerce platform has millions of products, so materializing one ReservationUnit row per physical item would be wasteful. Which adaptation keeps the contention benefit with less storage?

```json
{
 "options": [
  "Maintain a bounded pool of reservable rows and replenish it as the pool gets low",
  "Return to one inventoryCount row and add more Sale Service instances",
  "Create ReservationUnit rows after a buyer completes payment",
  "Let each client choose a unit ID without a database lock"
 ],
 "correctAnswer": 0
}
```

**Explanation:** A bounded pool preserves multiple independently lockable claims without representing the entire catalog's inventory as rows at once. Replenishing the pool as it drains trades some management work for much lower storage.

## 13. [SENIOR · MULTIPLE_CHOICE] Why does the final design prefer ReservationUnit rows over the Redis counter option for coordinating inventory?

```json
{
 "options": [
  "ReservationUnit rows make admission control unnecessary",
  "Redis cannot execute a check and decrement atomically",
  "ReservationUnit rows spread claims across independent locks while keeping inventory and reservations in one transactional source of truth",
  "ReservationUnit rows use less storage than a single integer counter"
 ],
 "correctAnswer": 2
}
```

**Explanation:** Redis speeds up the serialization point, but a single counter remains hot and critical state is split across Redis and Postgres. ReservationUnit rows permit parallel claims and keep the inventory invariant inside one database transaction.

## 14. [SENIOR · MULTIPLE_CHOICE] Load tests show the reservation system sustains 10,000 transactions per second. Which admission policy best matches the article's design?

```json
{
 "options": [
  "Admit all waiting users because SKIP LOCKED eliminates the database's capacity limit",
  "Admit exactly 10,000 users once, then stop the controller",
  "Admit more than 10,000 users per second so unused retries fill any spare capacity",
  "Start below the measured ceiling, such as 8,000 users per second, and tune while preserving headroom"
 ],
 "correctAnswer": 3
}
```

**Explanation:** Admission control should keep arrivals below the backend's sustainable rate rather than operate at the failure boundary. Leaving headroom absorbs variance and other work, and the rate can be adjusted as observed capacity changes.

## 15. [SENIOR · MULTIPLE_CHOICE] The waiting room is sharded across several Redis instances. What is required to preserve the article's fairness policy across shards?

```json
{
 "options": [
  "Each shard should admit its own users whenever its local queue is shortest",
  "Users should choose the shard that reports the fastest polling latency",
  "Each entry needs a globally comparable ordering value that the admission controller respects",
  "All post-sale arrivals should be mixed into the randomized pre-sale group"
 ],
 "correctAnswer": 2
}
```

**Explanation:** Independent shard-local ordering can let a later user on one shard jump ahead of an earlier user on another. A globally comparable ordering value lets the admission controller preserve the randomized pre-sale cohort followed by post-sale FIFO.
