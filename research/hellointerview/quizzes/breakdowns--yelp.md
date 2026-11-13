# Distributed Systems and Search Architecture Quiz

## 1. [MID_LEVEL · TRUE_FALSE] B-tree indexes efficiently handle two-dimensional geographic range queries.

```json
{
 "correctAnswer": false
}
```

**Explanation:** B-trees are optimized for one-dimensional data. Geographic queries need spatial indexes like R-trees or quadtrees that understand two-dimensional relationships.

## 2. [MID_LEVEL · RANKING] Order these steps by when they occur (first to last) as a user search request flows through the high-level design described in the article.

```json
{
 "items": [
  "The Business Service queries the Database based on the search criteria",
  "The client sends a GET request to /businesses with the search parameters",
  "The results are returned to the client via the API Gateway",
  "The API Gateway routes the request to the Business Service"
 ],
 "correctOrder": [
  1,
  3,
  0,
  2
 ]
}
```

**Explanation:** The article lays out the search request flow in order: the client sends the GET request, the API Gateway routes it to the Business Service, the Business Service queries the Database, and the results are returned to the client via the API Gateway. The dimension is strict chronological order through the request path.

## 3. [MID_LEVEL · MULTIPLE_CHOICE] Which data structure enables efficient full-text search?

```json
{
 "options": [
  "B-tree index",
  "Inverted index",
  "Hash table",
  "Binary heap"
 ],
 "correctAnswer": 1
}
```

**Explanation:** Inverted indexes map terms to document locations, enabling O(1) lookup for text searches. This structure powers search engines and full-text databases.

## 4. [MID_LEVEL · MULTIPLE_CHOICE] Why does the article store num_reviews alongside each business's precomputed average_rating?

```json
{
 "options": [
  "It supports the incremental-average formula, avoiding a scan of all prior reviews",
  "It makes concurrent writes safe without optimistic locking",
  "It replaces the need to store individual reviews",
  "It lets a B-tree index ratings geographically"
 ],
 "correctAnswer": 0
}
```

**Explanation:** With the current average and review count, a new rating can be folded in using (old average × num_reviews + new rating) / (num_reviews + 1), without reading every prior review. The count makes that calculation efficient, but concurrent writers still need optimistic locking so one update does not overwrite another.

## 5. [MID_LEVEL · MULTIPLE_CHOICE] A system has a 1000:1 read-to-write ratio and needs to scale read throughput. Which approach addresses this?

```json
{
 "options": [
  "Use a write-optimized database like Cassandra",
  "Add read replicas and caching layers",
  "Optimize write performance with batching",
  "Use synchronous replication for consistency"
 ],
 "correctAnswer": 1
}
```

**Explanation:** For read-heavy workloads (1000:1 ratio), the bottleneck is read capacity. Read replicas distribute read load across multiple database instances, and caching reduces database hits entirely.

## 6. [MID_LEVEL · MATCHING_PAIRS] Match each component of the Yelp high-level design to its responsibility as described in the article.

```json
{
 "leftItems": [
  "Client",
  "API Gateway",
  "Business Service",
  "Database"
 ],
 "rightItems": [
  "Stores information about businesses such as name, description, location, and category",
  "Users interact with the system through a web or mobile application",
  "Processes query parameters and formulates database queries to retrieve business information",
  "Routes incoming requests to the appropriate services"
 ],
 "correctPairs": [
  1,
  3,
  2,
  0
 ]
}
```

**Explanation:** The article defines each component's role: the Client is how users interact via web or mobile, the API Gateway routes incoming requests to the appropriate services, the Business Service processes query parameters and formulates database queries, and the Database stores business information like name, location, and category.

## 7. [MID_LEVEL · TRUE_FALSE] Database constraints provide stronger data integrity than application-level checks.

```json
{
 "correctAnswer": true
}
```

**Explanation:** Database constraints enforce rules at the lowest level, preventing any process from violating them. Application checks can be bypassed by direct database access.

## 8. [MID_LEVEL · MULTIPLE_CHOICE] Which is NOT suitable for geographic proximity searches?

```json
{
 "options": [
  "Quadtree",
  "R-tree",
  "B-tree",
  "Geohash"
 ],
 "correctAnswer": 2
}
```

**Explanation:** B-trees excel at one-dimensional data but cannot efficiently index two-dimensional geographic coordinates. Quadtrees, R-trees, and geohashes are designed for spatial data.

## 9. [MID_LEVEL · MULTIPLE_CHOICE] What occurs when optimistic locking detects concurrent modifications?

```json
{
 "options": [
  "Transaction commits successfully",
  "Transaction rolls back",
  "Database locks permanently",
  "Update merges automatically"
 ],
 "correctAnswer": 1
}
```

**Explanation:** Optimistic locking checks version numbers before committing. When conflicts are detected, the transaction rolls back, requiring the client to retry with fresh data.

## 10. [MID_LEVEL · TRUE_FALSE] Using a cron job to periodically update business average ratings provides real-time accuracy for users viewing search results.

```json
{
 "correctAnswer": false
}
```

**Explanation:** Periodic updates via cron jobs do not provide real-time accuracy. When a user leaves a new review, the average rating won't be updated until the next scheduled cron job runs (which could be hours or days later). This leads to stale data where users see outdated average ratings that don't reflect recent reviews. For real-time accuracy, synchronous updates or near-real-time processing would be required.

## 11. [MID_LEVEL · MULTIPLE_CHOICE] When implementing a constraint that users can only leave one review per business, which approach provides the strongest data integrity guarantee?

```json
{
 "options": [
  "Check for existing reviews in the application layer before inserting",
  "Use a unique database constraint on (user_id, business_id)",
  "Implement a distributed lock across multiple services",
  "Store review counts in a separate cache layer"
 ],
 "correctAnswer": 1
}
```

**Explanation:** Database constraints enforce data integrity at the persistence layer, making it impossible to violate the constraint regardless of which service or process attempts to insert data. This prevents race conditions and ensures consistency even when multiple services interact with the database, unlike application-layer checks which can be bypassed or fail under concurrent access.

## 12. [MID_LEVEL · TRUE_FALSE] Using a message queue to handle review submissions is necessary when the system processes 100,000 review writes per day.

```json
{
 "correctAnswer": false
}
```

**Explanation:** 100,000 writes per day equals approximately 1 write per second, which is a very low write volume that modern databases can easily handle without requiring a message queue. Message queues add complexity and are typically needed for much higher write volumes (thousands of writes per second) or when you need to decouple services for other architectural reasons. For this low volume, a simple synchronous approach with proper database constraints would be more appropriate and demonstrates understanding of when not to over-engineer a solution.

## 13. [MID_LEVEL · TRUE_FALSE] Eventual consistency is acceptable for Yelp's business rating system because users can tolerate slightly outdated average ratings.

```json
{
 "correctAnswer": true
}
```

**Explanation:** True. The article explicitly states that eventual consistency is fine for Yelp's requirements. Users searching for businesses can tolerate average ratings that are slightly behind real-time updates, as the core user experience doesn't require immediate consistency when new reviews are added. This trade-off allows for better system performance and scalability.

## 14. [MID_LEVEL · TRUE_FALSE] PostGIS extension allows PostgreSQL to efficiently handle geospatial queries without requiring a separate search service like Elasticsearch.

```json
{
 "correctAnswer": true
}
```

**Explanation:** PostGIS is a PostgreSQL extension that adds geospatial indexing capabilities, enabling efficient location-based queries directly within PostgreSQL. This eliminates the need for a separate search service and avoids data consistency issues between multiple systems, making it a simpler solution for geospatial search requirements.

## 15. [MID_LEVEL · TRUE_FALSE] Pre-computing business average ratings trades write-time computation for faster read queries.

```json
{
 "correctAnswer": true
}
```

**Explanation:** Pre-computing average ratings calculates and stores the result when reviews are written, rather than computing it on every search query. This moves computation from read time to write time, avoiding expensive aggregate calculations during search and dramatically improving query latency.
