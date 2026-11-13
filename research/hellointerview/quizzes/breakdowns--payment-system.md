# Payment System Design Quiz

## 1. [JUNIOR · TRUE_FALSE] Idempotent operations ensure repeated requests produce the same final state.

```json
{
 "correctAnswer": true
}
```

**Explanation:** An idempotent endpoint returns an identical result no matter how many times a client retries, preventing duplicate side effects such as double charges or duplicate messages.

## 2. [JUNIOR · MATCHING_PAIRS] Match each component in the payment system's high-level design to its primary responsibility.

```json
{
 "leftItems": [
  "API Gateway",
  "Payment Service",
  "Transaction Service",
  "Reconciliation Service"
 ],
 "rightItems": [
  "Creates and manages PaymentIntents and interfaces with the database to store payment information",
  "Serves as the entry point for merchant requests, handling authentication and rate limiting",
  "Consumes timeout events and queries the payment network to determine what actually happened",
  "Receives card details and interfaces directly with external payment networks like Visa and Mastercard"
 ],
 "correctPairs": [
  1,
  0,
  3,
  2
 ]
}
```

**Explanation:** The API Gateway is the entry point handling auth and rate limiting. The Payment Service creates and manages PaymentIntents. The Transaction Service receives card details and talks to external payment networks. The Reconciliation Service consumes timeout events and queries the network to resolve uncertain outcomes.

## 3. [MID_LEVEL · MULTIPLE_CHOICE] A merchant creates a PaymentIntent for an order, but the first charge attempt fails due to insufficient funds. The merchant retries the same checkout with a different card. How should this be represented in the article's data model?

```json
{
 "options": [
  "Create a new PaymentIntent and delete the failed one so only the successful attempt remains.",
  "Keep the same PaymentIntent and create a new Transaction linked to it for the retry.",
  "Update the failed Transaction in place with the new card details and final status.",
  "Store the retry only as a webhook event because PaymentIntents should not track failed attempts."
 ],
 "correctAnswer": 1
}
```

**Explanation:** The article distinguishes PaymentIntent as the merchant-facing lifecycle object from Transaction as the internal money-movement attempt. A single PaymentIntent can have multiple Transactions, such as when a failed charge is retried.

## 4. [MID_LEVEL · MULTIPLE_CHOICE] In an event-driven payment system with reconciliation, what enables correlating internal attempts with external payment network events?

```json
{
 "options": [
  "Recording attempt details before external calls",
  "Using strong consistency with synchronous replication across all databases",
  "Implementing synchronous API calls only",
  "Storing only successful transaction outcomes"
 ],
 "correctAnswer": 0
}
```

**Explanation:** By recording attempt details (network name, reference ID, what we're trying to accomplish) before making external calls, the reconciliation service can later correlate external events from payment networks with our internal attempts to resolve any discrepancies.

## 5. [MID_LEVEL · TRUE_FALSE] Change Data Capture (CDC) operates at the database level, guaranteeing that application bugs cannot skip audit logging.

```json
{
 "correctAnswer": true
}
```

**Explanation:** CDC monitors the database's write-ahead log or oplog, capturing every committed change automatically. Since it operates below the application layer, it cannot be bypassed by buggy code that forgets to write audit records.

## 6. [MID_LEVEL · MULTIPLE_CHOICE] When a payment request to an external network times out, what should a payment system do to ensure transaction safety?

```json
{
 "options": [
  "Immediately mark the payment as failed",
  "Retry the payment request with the same details",
  "Mark the payment as 'pending verification' and reconcile later",
  "Assume the payment succeeded"
 ],
 "correctAnswer": 2
}
```

**Explanation:** Timeouts don't indicate success or failure - they indicate uncertainty. Marking as 'pending verification' acknowledges this uncertainty while a reconciliation service queries the payment network to determine what actually happened, preventing double-charging.

## 7. [MID_LEVEL · MULTIPLE_CHOICE] Which approach prevents sensitive card data from ever touching the merchant's servers, reducing their PCI DSS scope?

```json
{
 "options": [
  "Loading the processor's iframe so card data goes straight to the processor",
  "Having the merchant's server collect the card data and forward it to the processor over HTTPS",
  "Authenticating each transaction with a static API key in the request header",
  "Submitting the card form over plain HTTPS to the merchant's backend"
 ],
 "correctAnswer": 0
}
```

**Explanation:** The processor's SDK loads an iframe from the processor's own domain, so the card details a customer enters go straight to the processor and never reach the merchant's servers. Because the merchant never handles raw card data, their PCI DSS compliance scope is dramatically reduced. Layering client-side encryption on top protects the data before it even leaves the customer's browser.

## 8. [MID_LEVEL · TRUE_FALSE] Payment systems must handle the inherently asynchronous nature of external payment networks like Visa and Mastercard.

```json
{
 "correctAnswer": true
}
```

**Explanation:** External payment networks operate independently with their own retry mechanisms, queue delays, and batch processing. A timeout doesn't mean failure - the payment might still be processing through banking systems.

## 9. [MID_LEVEL · MULTIPLE_CHOICE] Which technique BEST prevents duplicate charges when external service calls may time out?

```json
{
 "options": [
  "Idempotency keys on requests",
  "Increasing HTTP timeouts to avoid premature disconnects",
  "Retrying requests without changes",
  "Round-robin load balancing"
 ],
 "correctAnswer": 0
}
```

**Explanation:** An idempotency key ties each logical request to a unique identifier. Retries with the same key return the stored result rather than performing the action again, eliminating duplicate charges.

## 10. [MID_LEVEL · RANKING] In the event-driven safety with reconciliation approach, order these steps of handling a single charge from earliest to latest in the flow.

```json
{
 "items": [
  "Call the payment network by sending the charge request with the configured timeout",
  "Record the attempt to the database (network name, reference ID, intention) before calling the network",
  "Update the attempt status (succeeded, timeout, or failed) based on the network's response",
  "The reconciliation service consumes timeout events and queries the network using the recorded reference ID"
 ],
 "correctOrder": [
  1,
  0,
  2,
  3
 ]
}
```

**Explanation:** The article's flow is: record the attempt before acting, call the payment network, update the attempt status based on the outcome, then have the reconciliation service consume timeout events and proactively query the network. Tracking intentions before acting is the key insight that makes reconciliation possible.

## 11. [SENIOR · MULTIPLE_CHOICE] A merchant’s webhook endpoint is down when a payment succeeds. Which behavior best matches the design implied by the article’s status API plus webhook approach?

```json
{
 "options": [
  "Persist the authoritative payment status internally, retry or defer webhook delivery, and allow the merchant to fetch status via `GET /payment-intents/{id}`.",
  "Roll back the successful payment because the merchant did not acknowledge the webhook.",
  "Mark the payment as `pending` indefinitely until the merchant webhook returns HTTP 200.",
  "Store the payment status only in the webhook payload, since webhooks are the real-time interface."
 ],
 "correctAnswer": 0
}
```

**Explanation:** Webhooks are a notification mechanism, not the source of truth for payment state. The system should keep durable internal state and expose it through the status API, while webhook delivery can be retried independently when the merchant endpoint recovers.

## 12. [SENIOR · MULTIPLE_CHOICE] A PaymentIntent has already reached `captured` after one Charge transaction succeeded. Minutes later, a delayed failure response arrives for an earlier retry attempt linked to the same PaymentIntent. What should the payment system do?

```json
{
 "options": [
  "Overwrite the PaymentIntent to `failed`, because the delayed response is newer information from the network.",
  "Treat the PaymentIntent state machine as authoritative and ignore or record the stale failure without regressing the intent state.",
  "Create a second PaymentIntent so both the success and failure can be represented independently to the merchant.",
  "Delete the earlier Transaction so delayed responses can no longer affect the PaymentIntent."
 ],
 "correctAnswer": 1
}
```

**Explanation:** Because one PaymentIntent can have multiple Transactions, individual transaction results must not blindly “last-write-wins” the overall payment state. The PaymentIntent owns the lifecycle state machine, so invalid regressions like `captured` → `failed` should be rejected while still preserving the underlying transaction event for auditability.

## 13. [SENIOR · MULTIPLE_CHOICE] The article simplifies money movement as a polymorphic `Transaction`, but notes that a production system would likely add double-entry `LedgerEntry` rows. What problem does that production change primarily solve?

```json
{
 "options": [
  "It avoids the need to store PaymentIntent state because balances can be inferred from merchant API keys.",
  "It reduces PCI scope by replacing card numbers with ledger identifiers.",
  "It records every balance-affecting movement as balanced debit/credit entries, improving financial integrity and auditability.",
  "It lets the API gateway route requests without calling the Payment Service."
 ],
 "correctAnswer": 2
}
```

**Explanation:** A `Transaction` is useful for modeling payment attempts, refunds, disputes, and payouts, but it is not the same as a financial ledger. Double-entry ledger rows make actual balance movement explicit and auditable, which is critical when money must be reconciled exactly.

## 14. [SENIOR · MULTIPLE_CHOICE] Which approach BEST ensures no payment transaction data is ever lost while maintaining audit compliance?

```json
{
 "options": [
  "Update records in place with daily backups",
  "Separate audit tables updated by application code on every write path",
  "CDC feeding an immutable event stream",
  "Storing only current state in memory"
 ],
 "correctAnswer": 2
}
```

**Explanation:** CDC automatically captures all database changes at the database level and feeds them to an immutable event stream (like Kafka), guaranteeing no audit data is lost regardless of application bugs. This satisfies compliance requirements with cryptographically verifiable immutability.

## 15. [SENIOR · TRUE_FALSE] When a charge attempt fails and the merchant retries under the same PaymentIntent, modeling the retry as a new Transaction rather than overwriting the old one better preserves auditability and lets the PaymentIntent expose a single merchant-facing lifecycle.

```json
{
 "correctAnswer": true
}
```

**Explanation:** The article defines a one-to-many relationship where a PaymentIntent can spawn multiple Transactions, such as separate charge attempts after a failure. Keeping each attempt as its own record preserves the history needed for durability and auditability, while the PaymentIntent can still summarize the overall state for the merchant.
