# Temporal Quiz

## 1. [JUNIOR · MULTIPLE_CHOICE] What is a Temporal Signal used for?

```json
{
 "options": [
  "Caching reconstructed Workflow state on a Worker",
  "Sending external information to a running Workflow",
  "Partitioning Workflow Executions across History Service instances",
  "Selecting the database used by a self-hosted cluster"
 ],
 "correctAnswer": 1
}
```

**Explanation:** A Signal appends external input to a Workflow's history and wakes the Workflow so it can react. For example, a delivery webhook can Signal an order Workflow that its package arrived.

## 2. [JUNIOR · MULTIPLE_CHOICE] What does Temporal's Event History provide?

```json
{
 "options": [
  "A durable record used to reconstruct Workflow execution",
  "A registry of the machines allowed to poll each Task Queue",
  "An in-memory cache shared by every Workflow Worker",
  "A continuous event stream intended to replace Kafka"
 ],
 "correctAnswer": 0
}
```

**Explanation:** The Event History is the durable record of what happened during a Workflow Execution. Temporal can replay that history to recover state after a Worker fails or loses its cache.

## 3. [MID_LEVEL · TRUE_FALSE] Adding more application Workers is the appropriate fix when Workflow state updates are bottlenecked in the History Service or its persistence database.

```json
{
 "correctAnswer": false
}
```

**Explanation:** Workers add capacity for application code that is ready to execute. A bottleneck in Workflow state updates needs more History Service or persistence capacity instead.

## 4. [MID_LEVEL · MULTIPLE_CHOICE] Why might an application use separate Task Queues for payment, shipping, and email Activities?

```json
{
 "options": [
  "To make Event History unnecessary for those Activities",
  "To route each kind of work to a Worker fleet with suitable resources or isolation",
  "To guarantee each external side effect executes exactly once",
  "To force every Activity and Workflow Task onto the same machine"
 ],
 "correctAnswer": 1
}
```

**Explanation:** Task Queue names route work to the Workers configured to poll them. Separate queues can isolate sensitive payment work or send CPU-heavy and GPU-heavy Activities to different fleets.

## 5. [MID_LEVEL · MULTIPLE_CHOICE] Which workload most strongly suggests using Temporal instead of a basic task queue?

```json
{
 "options": [
  "One independent thumbnail resize that can be retried as a single job",
  "A continuously processed stream of click events",
  "A cached database read performed during an HTTP request",
  "A multi-step order process that waits for delivery, retries failed work, and resumes after crashes"
 ],
 "correctAnswer": 3
}
```

**Explanation:** A task queue is often sufficient for one independent asynchronous job. Temporal becomes useful when the application must coordinate several dependent steps, long waits, retries, and recovery as one durable process.

## 6. [MID_LEVEL · MATCHING_PAIRS] Match each Temporal component to its primary responsibility:

```json
{
 "leftItems": [
  "Frontend Service",
  "History Service",
  "Matching Service",
  "Worker"
 ],
 "rightItems": [
  "Runs application Workflow and Activity code",
  "Owns durable Workflow state and processes state transitions",
  "Routes client and Worker requests into the cluster",
  "Manages Task Queues and delivers tasks to pollers"
 ],
 "correctPairs": [
  2,
  1,
  3,
  0
 ]
}
```

**Explanation:** Frontend is the stateless entry point, History owns Workflow state, and Matching connects queued tasks to pollers. Workers are application processes outside the Temporal Service that execute the user's code.

## 7. [MID_LEVEL · TRUE_FALSE] Calls made by Activities still need idempotency because Temporal may retry an Activity after an ambiguous failure.

```json
{
 "correctAnswer": true
}
```

**Explanation:** An external system may complete a side effect before the Worker reports success to Temporal. If Temporal cannot see the completion, it may retry the Activity, so the external operation must tolerate duplicate attempts.

## 8. [MID_LEVEL · MULTIPLE_CHOICE] An order Workflow branches on whether the current time is before 5 PM. How should it read time so replay follows the original branch?

```json
{
 "options": [
  "Read the new Worker's wall clock and store the result after the branch finishes",
  "Query the Temporal persistence database from the Workflow",
  "Use the SDK's Workflow-safe time operation, which reproduces logical time during replay",
  "Move the whole Workflow into the Frontend Service"
 ],
 "correctAnswer": 2
}
```

**Explanation:** Reading a machine clock directly could produce a different value after a crash and send replay down another branch. Temporal's Workflow-safe time operation reproduces the logical value used by the original execution.

## 9. [MID_LEVEL · TRUE_FALSE] Sticky Execution is the source of correctness for Workflow recovery, so losing a Worker's cache also loses the Workflow's recoverable state.

```json
{
 "correctAnswer": false
}
```

**Explanation:** Sticky Execution and the Workflow Cache reduce how often Temporal must replay a full history. Correctness comes from the durable Event History, which another Worker can use when the cache disappears.

## 10. [MID_LEVEL · TRUE_FALSE] Temporal's Task Queues serve a different purpose from a platform built for continuously processing a high-volume event stream.

```json
{
 "correctAnswer": true
}
```

**Explanation:** Temporal Task Queues dispatch Workflow and Activity Tasks to application Workers. The article recommends Kafka or another streaming platform when the core problem is continuous, high-volume event-stream processing.

## 11. [SENIOR · TRUE_FALSE] Persisting a Workflow state update and its Transfer Task together prevents a crash from forgetting that follow-up work must be dispatched, but it does not make an Activity's external side effect exactly once.

```json
{
 "correctAnswer": true
}
```

**Explanation:** The transactional-outbox-style write keeps Temporal's state transition and internal dispatch request coupled across a crash. An Activity can still complete externally before its result is recorded, so idempotency remains necessary at the side-effect boundary.

## 12. [SENIOR · TRUE_FALSE] Evicting a Workflow from a Worker's sticky cache may increase replay work without changing the Workflow's result, provided its durable history and deterministic code remain available.

```json
{
 "correctAnswer": true
}
```

**Explanation:** The cache is a performance shortcut that avoids reconstructing state for every Workflow Task. If it is lost, another Worker can replay the durable history and reach the same state as long as the Workflow remains deterministic.

## 13. [SENIOR · MULTIPLE_CHOICE] A cluster has millions of Workflows sleeping on durable timers, but most Activity queues are empty. After a burst of Signals, Workflow state updates become the bottleneck while Workers remain underused. Where should capacity be added first?

```json
{
 "options": [
  "The History Service and its persistence layer",
  "Every Activity Worker fleet",
  "The clients that originally started the Workflows",
  "The Workflow Cache on idle Activity Workers"
 ],
 "correctAnswer": 0
}
```

**Explanation:** Sleeping Workflows consume durable storage but do not occupy a Worker, and empty Activity queues show that application compute is not the constraint. The burst is stressing state transitions, so History Service and database capacity address the actual bottleneck.

## 14. [SENIOR · MULTIPLE_CHOICE] A payment Activity charges Stripe, but its Worker crashes before Temporal records the completion. What behavior should the system be designed to handle?

```json
{
 "options": [
  "Temporal may retry the Activity, so the Stripe operation needs an idempotency mechanism",
  "Replay will infer the missing Stripe result by scanning Mutable State",
  "Matching will keep the crashed Worker alive until it returns the payment ID",
  "The Workflow will skip every later Activity because the Event History is incomplete"
 ],
 "correctAnswer": 0
}
```

**Explanation:** From Temporal's perspective, the Activity has no recorded completion, so retrying it is a valid recovery action. The application must make the Stripe request idempotent because the first attempt may already have produced the external side effect.

## 15. [SENIOR · TRUE_FALSE] Reading a durable database directly from Workflow code is replay-safe because the database persists its values across Worker crashes.

```json
{
 "correctAnswer": false
}
```

**Explanation:** Durability does not guarantee that a query returns the same value later; the database can change between the original execution and replay. External queries belong in Activities whose returned results can be recorded and reproduced.
