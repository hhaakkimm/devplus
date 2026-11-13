# Data Modeling System Design Quiz

## 1. [JUNIOR · MULTIPLE_CHOICE] In a system design interview, which schema-design scope best matches the article?

```json
{
 "options": [
  "Normalize every table and eliminate all redundancy before discussing the rest of the system",
  "Sketch core entities, fields, keys, relationships, and indexes for the main access patterns, then move on",
  "Specify every column type, constraint, and secondary index before drawing the high-level design",
  "Benchmark every important query and choose its final storage engine before outlining the high-level design"
 ],
 "correctAnswer": 1
}
```

**Explanation:** The article says to identify core entities early, then sketch the fields, keys, relationships, and indexes needed to support the main access patterns. Data modeling is not the focus of a system design interview, so once the schema is clear and supports the requirements, move on.

## 2. [JUNIOR · TRUE_FALSE] Key-value stores are typically used as a replacement for SQL databases rather than alongside them.

```json
{
 "correctAnswer": false
}
```

**Explanation:** In practice, you'll often use both together. SQL as your source of truth with a key-value cache (like Redis) in front for hot data. This gives you fast access without sacrificing durability or complex queries.

## 3. [MID_LEVEL · TRUE_FALSE] Graph databases are commonly used and recommended for social network features in system design interviews.

```json
{
 "correctAnswer": false
}
```

**Explanation:** This is a common misconception. Even though social networks have graph-like data (friends, followers), companies like Facebook, LinkedIn, and Twitter use relational databases for their core relationship data. A simple SQL 'friendships' table with user_id pairs handles most cases efficiently. Graph databases are rarely the right choice in interviews unless you have a specific, complex graph traversal requirement.

## 4. [MID_LEVEL · MULTIPLE_CHOICE] How should you choose your shard key for database partitioning?

```json
{
 "options": [
  "Always use user_id",
  "Choose randomly to distribute load evenly",
  "Shard by the primary access pattern",
  "Use timestamp-based sharding"
 ],
 "correctAnswer": 2
}
```

**Explanation:** Shard by the primary access pattern. If you mostly query 'posts by user,' shard by user_id. This keeps related data together and avoids expensive cross-shard queries.

## 5. [MID_LEVEL · MULTIPLE_CHOICE] You are designing a checkout flow where creating a payment record and decrementing inventory must succeed or fail together. Why is a relational database a strong fit for this requirement?

```json
{
 "options": [
  "It avoids the need to define a schema upfront.",
  "It automatically caches hot checkout data in memory.",
  "It provides ACID transactions for strong consistency.",
  "It stores each order as a single nested JSON document."
 ],
 "correctAnswer": 2
}
```

**Explanation:** Relational databases are a good fit when correctness depends on strong consistency, such as avoiding double charges or overselling inventory. ACID transactions let related changes commit together or roll back together.

## 6. [MID_LEVEL · MULTIPLE_CHOICE] In a document database, you embed a user's posts directly inside the user document instead of storing posts separately. What trade-off does this introduce?

```json
{
 "options": [
  "Reads can avoid joins, but updating an individual post may require modifying the larger user document.",
  "Writes become impossible unless every post has the same fixed schema.",
  "Foreign key validation becomes faster, but storage usage always decreases.",
  "The system gains complex SQL joins, but loses flexible schemas."
 ],
 "correctAnswer": 0
}
```

**Explanation:** Embedding related data in a document can make common reads faster because the application fetches one document instead of joining across tables. The cost is update complexity and potential denormalization issues when nested data changes.

## 7. [MID_LEVEL · MULTIPLE_CHOICE] When should you consider document databases over SQL?

```json
{
 "options": [
  "Always, for better performance",
  "When schema changes frequently or data is deeply nested",
  "When you need ACID guarantees for transactional integrity",
  "Never, SQL is always better"
 ],
 "correctAnswer": 1
}
```

**Explanation:** Consider document databases when your schema changes frequently, when you have deeply nested data that would require many joins in SQL, or when different records have vastly different structures.

## 8. [MID_LEVEL · MULTIPLE_CHOICE] Which database type should you default to in system design interviews?

```json
{
 "options": [
  "Document databases with flexible schemas",
  "Key-value stores",
  "Relational databases (SQL), which handle most use cases well",
  "Graph databases"
 ],
 "correctAnswer": 2
}
```

**Explanation:** Relational databases (SQL) should be your default choice unless your requirements clearly signal a specialized model. PostgreSQL is recommended as it's well-understood and works for most use cases.

## 9. [MID_LEVEL · TRUE_FALSE] Cross-shard queries are expensive and should be avoided whenever possible.

```json
{
 "correctAnswer": true
}
```

**Explanation:** Cross-shard queries require querying multiple databases and merging results, which is expensive and complex. Good shard key selection keeps related data together to minimize these queries.

## 10. [MID_LEVEL · MULTIPLE_CHOICE] In an e-commerce schema, each option below duplicates a value from its source table into another table. Which duplicated value should stay frozen when the source value later changes, rather than being updated to match?

```json
{
 "options": [
  "A seller's display name, stored on each of their product listings",
  "A user's email, stored on every row that references the user",
  "A product's price, stored on an order line at checkout",
  "A product's current stock count, stored on each cart item"
 ],
 "correctAnswer": 2
}
```

**Explanation:** The order line's price records what the customer paid at checkout, so it is a point-in-time snapshot: if the product's price changes next week, the old order must still show the old price. Because it is never supposed to match the current price, there is no update to miss. The other three are meant to show the current value, so every change has to reach every copy, and one missed update leaves stale, inconsistent data. That is why you start normalized and duplicate data mainly for snapshots like this, analytics, or read-heavy paths.

## 11. [SENIOR · TRUE_FALSE] Expected growth to millions of users is, by itself, a clear signal to switch away from PostgreSQL because the article treats relational databases as unable to scale effectively without changing database models.

```json
{
 "correctAnswer": false
}
```

**Explanation:** The article explicitly says the scalability criticism of relational databases is often exaggerated. It points to read replicas, sharding, connection pooling, and caching as ways to scale a relational foundation, so volume alone does not justify choosing a specialized database.

## 12. [SENIOR · MULTIPLE_CHOICE] A team models a blogging product in a document database by embedding every post inside its author's user document. Later requirements include editing individual posts by id, showing a global feed ordered by post recency, and supporting authors with very large post histories. What is the strongest critique of this model?

```json
{
 "options": [
  "It is invalid because document databases cannot store nested arrays of objects.",
  "It optimizes away joins, but creates large mutable user documents and makes global post queries awkward; posts should likely be modeled separately.",
  "It should be converted to a graph database because authors and posts form relationships.",
  "It is strictly better than SQL because flexible schemas avoid the need for indexes."
 ],
 "correctAnswer": 1
}
```

**Explanation:** Embedding related data can improve read performance for access patterns that naturally fetch the whole document. But when nested data is large, frequently updated independently, or queried globally, the model causes update complexity and poor query fit.

## 13. [SENIOR · MULTIPLE_CHOICE] You are designing checkout for an e-commerce system. The system must prevent double-charging customers and overselling inventory, but a teammate proposes using only a key-value store because most operations are simple lookups and writes. What is the best response?

```json
{
 "options": [
  "Use a relational database as the source of truth for the transactional path, optionally with a key-value cache for hot reads.",
  "Use only the key-value store because exact-key access implies strong consistency for payments and inventory.",
  "Use a document database because flexible schemas are the main requirement in checkout systems.",
  "Use a graph database because orders, payments, and inventory are connected entities."
 ],
 "correctAnswer": 0
}
```

**Explanation:** The decisive requirement is strong consistency, not just lookup speed. SQL databases provide ACID transactions that fit payment and inventory correctness, while a key-value store can still be useful as a cache around the source of truth.

## 14. [SENIOR · TRUE_FALSE] A relational schema can be the right starting point for a feed query like “posts from followed users ordered by recency,” but if that join becomes a hot online path at scale, the article suggests considering denormalized views, caching, or precomputed results rather than assuming the normalized join is sufficient.

```json
{
 "correctAnswer": true
}
```

**Explanation:** The article says SQL makes complex relationship queries straightforward to express, but multi-table joins can become performance traps at scale. A senior design answer distinguishes logical correctness from production performance and introduces derived read models or caches when the query becomes too expensive.

## 15. [SENIOR · MULTIPLE_CHOICE] A key-value store serves hot reads by copying a user's display name into three keys: profile:{user_id}, post_author:{post_id}, and comment_author:{comment_id}. When the user renames themselves, the application overwrites only profile:{user_id}. What happens on later reads?

```json
{
 "options": [
  "Reads of the post_author and comment_author keys fail until those keys are rebuilt.",
  "Reads of the post_author and comment_author keys keep returning the old name.",
  "The store rejects the write because other keys still hold the old name.",
  "The store copies the new name into every key holding the same value."
 ],
 "correctAnswer": 1
}
```

**Explanation:** A key-value store treats each key as an independent value with no references, constraints or joins between keys, so it neither blocks the write nor propagates it. The post_author and comment_author keys still exist and still hold the old name, so they serve stale data. When you denormalize across keys, the application must update or invalidate every copy itself.
