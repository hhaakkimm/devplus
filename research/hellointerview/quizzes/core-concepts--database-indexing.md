# Database Indexing System Design Quiz

## 1. [JUNIOR · MATCHING_PAIRS] Match each index type to the access pattern it is described as specializing in.

```json
{
 "leftItems": [
  "Hash index",
  "Inverted index",
  "Geospatial index",
  "LSM tree"
 ],
 "rightItems": [
  "Searching for words within text content (full-text search)",
  "Efficiently searching for nearby points by latitude and longitude",
  "Exact-match lookups with O(1) average performance",
  "Write-heavy workloads with high write throughput"
 ],
 "correctPairs": [
  2,
  0,
  1,
  3
 ]
}
```

**Explanation:** The article describes hash indexes as excelling at exact-match queries with O(1) lookups, inverted indexes as the structure for searching words within text content, geospatial indexes as what you reach for when searching for nearby points by latitude and longitude, and LSM trees as built for write-heavy workloads with high write throughput.

## 2. [JUNIOR · MULTIPLE_CHOICE] What is the main trade-off when adding indexes to a database table?

```json
{
 "options": [
  "Slower reads but faster writes",
  "Faster reads but slower writes",
  "Higher CPU usage but lower memory",
  "Better compression but worse security"
 ],
 "correctAnswer": 1
}
```

**Explanation:** Indexes speed up read queries by providing efficient lookup paths, but they slow down writes because every insert, update, or delete must also update all relevant indexes. Each index requires additional storage and maintenance overhead.

## 3. [MID_LEVEL · MULTIPLE_CHOICE] In an LSM-tree-based database, why are primary-key lookups usually more efficient than lookups on a non-primary-key field?

```json
{
 "options": [
  "Because LSM trees keep a separate B-tree index for every column by default",
  "Because non-primary-key fields are always stored only in the write-ahead log",
  "Because the table is stored sorted by primary key, while secondary lookups need extra index structures",
  "Because LSM trees can only answer equality queries, not range queries"
 ],
 "correctAnswer": 2
}
```

**Explanation:** An LSM tree is typically the storage format for the whole table, organized by the primary key, so primary-key access follows the natural layout of the data. Queries on other fields require secondary indexes or additional structures, which can have different and often less direct performance characteristics.

## 4. [MID_LEVEL · TRUE_FALSE] Cassandra and RocksDB use LSM trees because they handle write-heavy workloads better than B-trees.

```json
{
 "correctAnswer": true
}
```

**Explanation:** Systems like Cassandra (Netflix's viewing events) and RocksDB (Facebook's social interactions) process millions of writes per second. LSM trees excel at this by batching writes in memory and flushing them sequentially, converting many random writes into fewer large sequential writes.

## 5. [MID_LEVEL · TRUE_FALSE] R-trees are more flexible than quadtrees because they use overlapping rectangles instead of fixed grid divisions.

```json
{
 "correctAnswer": true
}
```

**Explanation:** R-trees adapt their bounding rectangles to actual data distribution and can overlap, while quadtrees rigidly divide space into equal quadrants. This flexibility allows R-trees to efficiently index both points and complex shapes in the same structure.

## 6. [MID_LEVEL · MULTIPLE_CHOICE] When would you use an inverted index instead of a B-tree?

```json
{
 "options": [
  "For exact string matches against a known column value",
  "For full-text search within documents",
  "For sorting text alphabetically",
  "For storing user passwords"
 ],
 "correctAnswer": 1
}
```

**Explanation:** Inverted indexes map words to documents that contain them, making them perfect for full-text search. B-trees can't efficiently handle queries like 'find documents containing the word database' because they can't do middle-of-string pattern matching.

## 7. [MID_LEVEL · MULTIPLE_CHOICE] Why don't traditional B-tree indexes work well for geospatial queries?

```json
{
 "options": [
  "They use too much memory for multi-column geospatial data",
  "They index each dimension separately, missing proximity",
  "They're too slow for any spatial data",
  "They can't store decimal numbers accurately enough for coordinates"
 ],
 "correctAnswer": 1
}
```

**Explanation:** B-trees on latitude and longitude create two separate 1D indexes, but proximity searches need to understand 2D relationships. A query for 'nearby restaurants' becomes inefficient because you can't easily combine separate latitude and longitude ranges to find points within a circular radius.

## 8. [MID_LEVEL · MULTIPLE_CHOICE] Why are B-trees the most common type of database index?

```json
{
 "options": [
  "They use the least disk space of any index type",
  "They handle both equality and range queries efficiently",
  "They're fastest for exact matches only but can't do range scans",
  "They work only with numeric data"
 ],
 "correctAnswer": 1
}
```

**Explanation:** B-trees maintain sorted order and balanced structure, making them efficient for both exact matches (WHERE id = 123) and range queries (WHERE age BETWEEN 25 AND 35). They also support ORDER BY operations naturally since data is already sorted.

## 9. [MID_LEVEL · MULTIPLE_CHOICE] How does geohash enable efficient spatial queries using standard database indexes?

```json
{
 "options": [
  "By compressing location data to reduce storage",
  "By converting 2D coordinates into sortable strings where nearby points share prefixes",
  "By using special hardware acceleration",
  "By caching frequently queried locations"
 ],
 "correctAnswer": 1
}
```

**Explanation:** Geohash converts latitude/longitude into strings where nearby locations share similar prefixes (like 'dr5ru' for the same city block). This allows using regular B-tree indexes on the geohash strings for efficient proximity searches using simple prefix queries.

## 10. [MID_LEVEL · MULTIPLE_CHOICE] In a composite index on (user_id, created_at), which query CANNOT use the index efficiently?

```json
{
 "options": [
  "WHERE created_at > '2024-01-01'",
  "WHERE user_id = 123",
  "WHERE user_id = 123 AND created_at > '2024-01-01'",
  "WHERE user_id = 123 ORDER BY created_at"
 ],
 "correctAnswer": 0
}
```

**Explanation:** Composite indexes can only be used efficiently when filtering starts with the leftmost column(s). Since user_id comes first in the index, queries filtering only on created_at (skipping user_id) cannot use this index efficiently and must do a full table scan. All other options start with user_id, so they can use the index.

## 11. [SENIOR · MULTIPLE_CHOICE] A metrics table in an LSM-tree store is sorted by its primary key `(device_id, timestamp)`. Queries now need to filter by a `region` column that is not part of the key. What does indexing `region` require?

```json
{
 "options": [
  "Nothing extra, because SSTables are sorted by every column.",
  "Only a larger memtable, so rows can be scanned in memory.",
  "A separate structure that must also be updated on writes.",
  "Only write-ahead log changes, since the log records every column."
 ],
 "correctAnswer": 2
}
```

**Explanation:** An LSM tree is the storage format for the whole table, and its SSTables are sorted only by the primary key. Indexing `region` means maintaining an additional structure, like a Cassandra secondary index or a DynamoDB GSI, which adds write work and has different read costs than primary-key access. The memtable and write-ahead log only buffer and protect recent writes, so neither gives a sorted path by another column.

## 12. [SENIOR · TRUE_FALSE] In an LSM-tree store, a write that has landed in the in-memory memtable will survive a crash even if the write-ahead log has not yet been flushed to disk.

```json
{
 "correctAnswer": false
}
```

**Explanation:** The memtable is fast because it lives in RAM, but RAM is volatile, so a crash wipes anything that exists only there. The write-ahead log is what lets the system recover the write after a crash, so a write is only truly safe once the WAL is durable on disk.

## 13. [SENIOR · MULTIPLE_CHOICE] Why are database B-tree nodes sized to fit in one disk page?

```json
{
 "options": [
  "So each tree level can usually be traversed with one page read",
  "So each index can store only one row pointer per page",
  "So leaf nodes can appear at different depths",
  "So index updates never require disk writes"
 ],
 "correctAnswer": 0
}
```

**Explanation:** A page-sized node lets the database load a whole node with one disk read. Because each node has many children, a lookup reaches a leaf in only a few page reads.

## 14. [SENIOR · TRUE_FALSE] In DynamoDB, the sort key orders items across the whole table, so one sort-key range query can efficiently return matching items from many different partition keys.

```json
{
 "correctAnswer": false
}
```

**Explanation:** DynamoDB keeps items in sort-key order only within a single partition key, so a range query is efficient when it targets one partition key. There is no table-wide sort-key order, so finding a range across many partition keys means querying each partition key separately, scanning the table, or modeling another access path such as a global secondary index.

## 15. [SENIOR · MULTIPLE_CHOICE] A table has a B-tree index on `status`, but 95% of rows have `status = 'active'`. For `SELECT * FROM users WHERE status = 'active'`, why might the database still choose a sequential table scan?

```json
{
 "options": [
  "B-tree indexes only help when the indexed column is unique.",
  "Following the index may identify the rows, but fetching most heap pages through it can cause more random I/O than scanning the table sequentially.",
  "B-tree indexes support range queries but not equality predicates.",
  "On SSDs, random and sequential access have identical cost, so the optimizer ignores indexes."
 ],
 "correctAnswer": 1
}
```

**Explanation:** An index is most valuable when it lets the database avoid reading most of the table. If a predicate matches almost every row, the index traversal plus many heap page fetches can be worse than a sequential scan, especially because random access is still more expensive than sequential access even on SSDs.
