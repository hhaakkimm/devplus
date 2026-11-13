# Elasticsearch System Design Quiz

## 1. [JUNIOR · MATCHING_PAIRS] Match each Elasticsearch node type to its primary responsibility:

```json
{
 "leftItems": [
  "Master Node",
  "Data Node",
  "Coordinating Node",
  "Ingest Node"
 ],
 "rightItems": [
  "Stores documents and Lucene indexes",
  "Receives client requests and distributes queries",
  "Transforms and prepares data for indexing",
  "Manages cluster-level operations"
 ],
 "correctPairs": [
  3,
  0,
  1,
  2
 ]
}
```

**Explanation:** Master nodes handle cluster administration like adding/removing nodes and creating indices. Data nodes store documents and their indexes. Coordinating nodes receive search requests and distribute them across the cluster. Ingest nodes transform data before indexing.

## 2. [JUNIOR · MULTIPLE_CHOICE] In Elasticsearch's data model, what is the relationship between documents, indices, and mappings?

```json
{
 "options": [
  "Documents contain indices which contain mappings",
  "Indices hold documents; mappings define the schema",
  "Mappings contain indices which contain documents",
  "They are all equivalent concepts"
 ],
 "correctAnswer": 1
}
```

**Explanation:** An index is a collection of documents (similar to a database table), while a mapping defines the schema - specifying field types and how they should be processed and indexed for search.

## 3. [MID_LEVEL · MULTIPLE_CHOICE] How does Elasticsearch's query planner optimize search performance?

```json
{
 "options": [
  "By caching all search results in a shared in-memory store",
  "By keeping statistics on fields and keywords to choose efficient execution strategies",
  "By always using the inverted index first",
  "By distributing queries randomly across nodes"
 ],
 "correctAnswer": 1
}
```

**Explanation:** The query planner uses statistics about field types, keyword popularity, and document characteristics to determine the most efficient execution strategy, such as deciding the optimal order for processing query terms or whether to use indexes or direct document searches.

## 4. [MID_LEVEL · MULTIPLE_CHOICE] What is the advantage of using search_after over from/size pagination?

```json
{
 "options": [
  "It allows random access to any page",
  "It fetches only documents after the last result of the previous page",
  "It provides better security",
  "It uses less memory for small result sets"
 ],
 "correctAnswer": 1
}
```

**Explanation:** search_after uses the sort values from the last document of the previous page to skip ahead, so it never has to retrieve and sort all the preceding documents the way from/size does -- making deep pagination far cheaper. (This is search_after on its own; pairing it with a point-in-time snapshot adds the snapshot's overhead in exchange for a consistent view.)

## 5. [MID_LEVEL · MULTIPLE_CHOICE] What is a key limitation to consider when using Elasticsearch for frequently updated data?

```json
{
 "options": [
  "It cannot handle any updates",
  "Updates require soft deletion and re-insertion, creating performance overhead until segment merges occur",
  "It only supports batch updates during off-peak hours",
  "Updates corrupt the inverted index"
 ],
 "correctAnswer": 1
}
```

**Explanation:** Elasticsearch handles updates by soft-deleting the old document and inserting new data, leaving deleted documents in segments until merge operations clean them up. This creates performance penalties for workloads with frequent updates, making it less suitable for rapidly changing data.

## 6. [MID_LEVEL · MULTIPLE_CHOICE] A client reads a book document at version 1, changes the price, and sends a full-document PUT. What should it include to avoid silently overwriting a concurrent update?

```json
{
 "options": [
  "A version condition, such as `?version=1`, so the update fails if the document changed",
  "A larger `number_of_replicas` value so all writes are serialized",
  "A `keyword` mapping for every field in the document",
  "A nested mapping for the fields being updated"
 ],
 "correctAnswer": 0
}
```

**Explanation:** Elasticsearch exposes document versioning so clients can perform optimistic concurrency control. If another process updates the document first, the version check fails, giving the client a chance to handle the conflict instead of overwriting changes.

## 7. [MID_LEVEL · MULTIPLE_CHOICE] Which approach is generally recommended when using Elasticsearch in system design interviews?

```json
{
 "options": [
  "Use Elasticsearch as your primary database for all data",
  "Use Elasticsearch alongside an authoritative data store via Change Data Capture (CDC)",
  "Replace all SQL databases with Elasticsearch",
  "Use Elasticsearch only for write-heavy workloads"
 ],
 "correctAnswer": 1
}
```

**Explanation:** Elasticsearch is best used as a specialized search engine alongside an authoritative data store like Postgres or DynamoDB, with CDC keeping them synchronized. This provides search capabilities while maintaining data durability and consistency guarantees.

## 8. [MID_LEVEL · TRUE_FALSE] If a User document has many fields but searches only use a small subset of them, defining a mapping for just the searchable fields can reduce Elasticsearch memory overhead compared with indexing the entire object.

```json
{
 "correctAnswer": true
}
```

**Explanation:** The article notes that mappings determine which fields are searchable and that indexing unused fields increases memory overhead. In a system design scenario, being selective about mapped fields can improve performance and reduce cost when many fields are stored but not queried.

## 9. [MID_LEVEL · RANKING] Rank these deep-pagination approaches (page 1000+) from LEAST to MOST efficient, ignoring consistency guarantees:

```json
{
 "items": [
  "search_after pagination",
  "from/size pagination",
  "Point-in-time (PIT) snapshot + search_after"
 ],
 "correctOrder": [
  1,
  2,
  0
 ]
}
```

**Explanation:** from/size is the worst -- each request retrieves and sorts every document before the requested page. search_after is the most efficient: it uses the sort values of the last result to skip ahead, never paying for the documents before it. PIT + search_after has search_after's efficiency plus the cost of holding a consistent snapshot open, so on pure performance it sits between the two -- you accept that overhead when you need a stable view of the data during pagination.

## 10. [MID_LEVEL · MULTIPLE_CHOICE] You are modeling books and reviews in Elasticsearch. Reviews are rarely updated, and most searches need to return books together with their reviews. Which modeling choice best matches the article's guidance?

```json
{
 "options": [
  "Store reviews only in a relational database and never index them in Elasticsearch",
  "Nest reviews inside each book document",
  "Create a separate Elasticsearch cluster for reviews",
  "Use dynamic mapping for reviews and avoid defining their fields"
 ],
 "correctAnswer": 1
}
```

**Explanation:** The article says nesting can be efficient when the nested data is infrequently updated and frequently queried with the parent document. If reviews changed often or were queried independently, a separate reviews index would usually be a better normalization-style tradeoff.

## 11. [SENIOR · TRUE_FALSE] When using `search_after`, sorting only by a non-unique field such as `createdAt` is sufficient for reliable pagination because Elasticsearch can infer a stable order among documents with the same sort value.

```json
{
 "correctAnswer": false
}
```

**Explanation:** `search_after` depends on the previous hit’s sort values, so ties need a deterministic tie-breaker such as a unique document ID. Without one, documents sharing the same primary sort value can be skipped or repeated across pages, even though `search_after` avoids the high cost of deep `from/size` pagination.

## 12. [SENIOR · TRUE_FALSE] For a query that may match documents anywhere in an index, increasing the number of primary shards can make latency worse past a point because the request fans out to more shard copies and the coordinating node must merge more shard-local results.

```json
{
 "correctAnswer": true
}
```

**Explanation:** Shards add parallelism and let an index scale across nodes, but they also add per-shard overhead. Broad searches require scatter/gather work across shards, so over-sharding can increase coordination and merge costs rather than improving latency.

## 13. [SENIOR · MULTIPLE_CHOICE] A team enables dynamic mapping for a large `User` object with 80 fields, but product search only ever filters or searches on 6 of them. What is the main Elasticsearch-specific cost called out in the article?

```json
{
 "options": [
  "Queries become impossible because Elasticsearch requires every mapped field to appear in every document.",
  "Replica shards stop improving read throughput because mappings are too sparse.",
  "The index can no longer use keyword fields for exact-match lookups.",
  "The cluster pays memory and performance overhead for indexing fields that are not used for search."
 ],
 "correctAnswer": 3
}
```

**Explanation:** Mappings determine which fields Elasticsearch indexes and how it interprets them. The article specifically notes that mapping many unused fields wastes memory and can increase cost and performance pressure, so explicit mappings are preferable when most fields are not searchable.

## 14. [SENIOR · MULTIPLE_CHOICE] Two services read version 1 of the same document. Service A replaces the full document and changes `price`; Service B later replaces the full document from its stale copy and changes `description`, without using the version parameter. What failure mode is the article warning about?

```json
{
 "options": [
  "Service B can overwrite Service A’s price change because a full-document replacement from stale state is not protected by default.",
  "Elasticsearch will merge both full-document replacements field-by-field because `_version` exists on the document.",
  "Both writes will be rejected because Elasticsearch requires `_version` on every update request.",
  "The document will be split into two Lucene segments, and search will return duplicate versions until refresh."
 ],
 "correctAnswer": 0
}
```

**Explanation:** The article warns that replacing an entire document can overwrite concurrent changes if the client does not guard the write. Supplying the expected `_version` turns this into optimistic concurrency control, causing stale writes to fail so the client can retry safely.

## 15. [SENIOR · MULTIPLE_CHOICE] A bookstore stores each book as an Elasticsearch document and is deciding whether to embed reviews as nested documents inside the book or store reviews in a separate index. Reviews are added and edited frequently, while book metadata changes rarely. Based on the article’s tradeoff, which design is the better default?

```json
{
 "options": [
  "Nest reviews inside book documents so each book search can always retrieve reviews with no extra index.",
  "Use dynamic mapping for reviews but keep them in the same book document to reduce mapping complexity.",
  "Store reviews in a separate reviews index because frequent independent updates make nesting less attractive.",
  "Store each review as a separate Elasticsearch cluster to avoid shard contention with books."
 ],
 "correctAnswer": 2
}
```

**Explanation:** The article frames nested documents as a denormalization tradeoff: nesting is attractive when the nested data is infrequently updated and frequently queried with the parent. If reviews change often, embedding them in book documents increases update coupling, so a separate reviews index is the better default.
