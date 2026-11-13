# Instagram System Design Quiz

## 1. [MID_LEVEL · RANKING] Rank these storage tiers from hottest (fastest/most expensive) to coldest (slowest/cheapest):

```json
{
 "items": [
  "Redis In-Memory Cache",
  "CDN Edge Cache",
  "SSD Storage",
  "Glacier Archive"
 ],
 "correctOrder": [
  1,
  0,
  2,
  3
 ]
}
```

**Explanation:** Storage tiers follow a cost-performance tradeoff. CDN edge caches provide the fastest access for frequently requested content, followed by in-memory caches like Redis. SSD storage offers good performance for active data, while archival storage like Glacier is cheapest but has retrieval delays. Instagram uses this tiering to optimize costs by moving infrequently accessed content to cheaper storage.

## 2. [MID_LEVEL · MULTIPLE_CHOICE] Which is NOT a characteristic of in-memory data stores?

```json
{
 "options": [
  "Microsecond access latency",
  "Persistence by default",
  "Limited by RAM capacity",
  "Higher cost per GB"
 ],
 "correctAnswer": 1
}
```

**Explanation:** In-memory stores like Redis prioritize speed over durability. While they can be configured for persistence (AOF, snapshots), this isn't their default behavior. They trade durability for microsecond access times, making them ideal for caching but requiring careful consideration of data loss scenarios.

## 3. [MID_LEVEL · TRUE_FALSE] Fan-out on write precomputes results during write operations to improve read performance.

```json
{
 "correctAnswer": true
}
```

**Explanation:** Fan-out on write pushes updates to all relevant destinations when data is created or modified. This front-loads computation during writes, enabling simple, fast reads later. The tradeoff is increased write complexity and potential write amplification for highly connected data.

## 4. [MID_LEVEL · TRUE_FALSE] In a hybrid feed generation approach, posts from users with fewer followers are precomputed while posts from celebrities are fetched in real-time.

```json
{
 "correctAnswer": true
}
```

**Explanation:** This is correct. The hybrid approach combines fan-out on write for regular users (precomputing feeds for users with fewer than a threshold like 100,000 followers) with fan-out on read for celebrities (fetching their posts in real-time during feed requests). This balances write amplification concerns with read performance - we avoid millions of writes when celebrities post, while still maintaining fast feed generation for most users through precomputation.

## 5. [MID_LEVEL · MULTIPLE_CHOICE] Which component caches content at geographic edge locations to reduce latency?

```json
{
 "options": [
  "Content Delivery Network",
  "Load Balancer",
  "Message Queue",
  "Database Replica"
 ],
 "correctAnswer": 0
}
```

**Explanation:** Content Delivery Networks (CDNs) maintain servers at multiple geographic locations worldwide. When users request content, they're automatically routed to the nearest edge location, dramatically reducing latency compared to fetching from a central origin server.

## 6. [STAFF · MULTIPLE_CHOICE] When designing Instagram's media upload system for files up to 4GB, what is the primary architectural decision that enables both upload reliability and direct client-to-storage efficiency?

```json
{
 "options": [
  "Implementing server-side file compression before storing in S3 to reduce storage costs",
  "Using pre-signed URLs with multipart uploads to allow direct client-to-S3 transfers",
  "Creating a dedicated media processing service that handles all file uploads synchronously",
  "Storing all media files in a distributed database instead of object storage for faster access"
 ],
 "correctAnswer": 1
}
```

**Explanation:** Pre-signed URLs with multipart uploads solve multiple critical problems for large media files: they enable direct client-to-S3 transfers (bypassing application servers and reducing bandwidth costs), support files larger than HTTP request limits through chunking, improve upload reliability through retry mechanisms for individual chunks, and maintain security through time-limited, scoped access tokens. This approach is essential at Instagram's scale where routing 4GB video uploads through application servers would create massive bottlenecks and infrastructure costs. The multipart upload API automatically handles chunk reassembly, while pre-signed URLs ensure secure direct access without exposing AWS credentials to clients.

## 7. [SENIOR · MULTIPLE_CHOICE] What happens when a user with millions of followers creates new content in a fan-out on write system?

```json
{
 "options": [
  "The write operation completes instantly",
  "Millions of write operations are triggered",
  "Only one database write occurs",
  "Read operations become slower"
 ],
 "correctAnswer": 1
}
```

**Explanation:** In fan-out on write, creating content triggers updates to every follower's feed. For users with millions of followers, this creates massive write amplification - one logical write becomes millions of physical writes, potentially overwhelming the system and causing significant latency.

## 8. [STAFF · TRUE_FALSE] Eventual consistency allows temporary inconsistencies between replicas to achieve higher availability and partition tolerance.

```json
{
 "correctAnswer": true
}
```

**Explanation:** Eventual consistency relaxes the requirement for immediate synchronization across all replicas. By allowing temporary divergence, systems can continue operating during network partitions and achieve higher availability. The tradeoff is that different replicas may briefly return different values until synchronization completes.

## 9. [STAFF · MULTIPLE_CHOICE] All of the following reduce storage costs for infrequently accessed data EXCEPT:

```json
{
 "options": [
  "Moving data to cold storage",
  "Compressing archived data",
  "Replicating to more regions",
  "Setting shorter retention periods"
 ],
 "correctAnswer": 2
}
```

**Explanation:** Replicating data to more regions increases storage costs by creating additional copies. Cost reduction strategies include moving to cheaper cold storage (like AWS Glacier), compression to reduce size, and retention policies to delete old data. Multi-region replication improves availability but increases costs.

## 10. [SENIOR · MATCHING_PAIRS] Match each Instagram system challenge to its architectural solution:

```json
{
 "leftItems": [
  "Celebrity problem (write amplification)",
  "Large video uploads (up to 4GB)",
  "Global media latency",
  "Feed data durability"
 ],
 "rightItems": [
  "Redis with AOF persistence",
  "CDN edge caching",
  "Hybrid fan-out approach",
  "Pre-signed URLs with chunked uploads"
 ],
 "correctPairs": [
  2,
  3,
  1,
  0
 ]
}
```

**Explanation:** The hybrid approach solves the celebrity problem by avoiding fan-out on write for high-follower accounts. Pre-signed URLs with chunked multipart uploads handle large files that exceed HTTP limits. CDN edge caching reduces global latency by serving content from nearby locations. Redis AOF persistence ensures feed data survives node failures.

## 11. [STAFF · TRUE_FALSE] Using different feed generation strategies based on follower count thresholds balances read and write performance.

```json
{
 "correctAnswer": true
}
```

**Explanation:** Hybrid approaches apply different strategies based on data characteristics. For users below a follower threshold, fan-out on write provides fast reads. For high-follower accounts, fan-out on read avoids write amplification. This selective approach optimizes both read and write performance where needed most.

## 12. [SENIOR · MULTIPLE_CHOICE] Which caching strategy works BEST for data with a 100:1 read to write ratio?

```json
{
 "options": [
  "Write-through cache",
  "Write-back cache",
  "Cache-aside with long TTL",
  "No caching needed"
 ],
 "correctAnswer": 2
}
```

**Explanation:** For read-heavy workloads (100:1), cache-aside with long TTL maximizes cache hit rates while minimizing cache maintenance overhead. The infrequent writes don't justify the complexity of write-through or write-back strategies, and the high read ratio makes caching extremely beneficial.

## 13. [SENIOR · TRUE_FALSE] Chunked multipart uploads enable reliable transfer of files larger than typical HTTP request limits.

```json
{
 "correctAnswer": true
}
```

**Explanation:** HTTP requests typically have size limits (often 2GB or less). Multipart uploads split large files into smaller chunks that can be uploaded independently and reassembled server-side. This enables reliable uploads of multi-gigabyte files while supporting resume capabilities and parallel transfers.

## 14. [SENIOR · MULTIPLE_CHOICE] When generating a social media feed from followed accounts, which approach minimizes read latency for most users?

```json
{
 "options": [
  "Query all followed accounts at read time",
  "Precompute feeds when content is posted",
  "Cache only popular user content",
  "Store all posts in a single table"
 ],
 "correctAnswer": 1
}
```

**Explanation:** Precomputing feeds (fan-out on write) during content creation eliminates the need to aggregate data from multiple sources at read time. While this increases write complexity, it transforms feed retrieval into a simple lookup operation, achieving consistently low read latency.

## 15. [STAFF · MULTIPLE_CHOICE] In social platforms, the 'celebrity problem' refers to which scalability challenge?

```json
{
 "options": [
  "Users with millions of followers creating write amplification",
  "Celebrities posting inappropriate content",
  "Database queries taking too long",
  "Storage costs for celebrity accounts"
 ],
 "correctAnswer": 0
}
```

**Explanation:** The celebrity problem occurs when users with massive follower counts create disproportionate system load. In fan-out on write systems, a single celebrity post triggers millions of feed updates, creating write amplification that can overwhelm infrastructure not designed for such hotspots.
