# CamelCamelCamel System Design Quiz

## 1. [JUNIOR · TRUE_FALSE] Consensus-based validation requires multiple independent sources to confirm data accuracy.

```json
{
 "correctAnswer": true
}
```

**Explanation:** Consensus validation works by requiring multiple independent parties to agree on data before accepting it as valid. This approach filters out errors and malicious input while maintaining system reliability even with some unreliable sources.

## 2. [JUNIOR · MULTIPLE_CHOICE] Which is NOT a reason to separate time-series data from operational data?

```json
{
 "options": [
  "Different scaling requirements",
  "Distinct access patterns",
  "Specialized optimization needs",
  "Reduced system complexity"
 ],
 "correctAnswer": 3
}
```

**Explanation:** Database separation actually increases system complexity, not reduces it. The valid reasons for separation are different scaling needs (time-series data grows much faster), access patterns (analytical vs transactional), and optimization requirements (time-series vs CRUD operations).

## 3. [MID_LEVEL · MULTIPLE_CHOICE] For serving historical price charts with sub-500ms latency on billions of records, which database type is specifically designed for this use case?

```json
{
 "options": [
  "Pre-aggregated summary tables in PostgreSQL with materialized views",
  "Time-series database with real-time aggregation",
  "Cached individual data points in Redis",
  "Distributed query processing across shards"
 ],
 "correctAnswer": 1
}
```

**Explanation:** Time-series databases like TimescaleDB can perform real-time aggregations in milliseconds even with billions of records through specialized indexing and compression. This eliminates the complexity and staleness of pre-aggregation while meeting strict latency requirements.

## 4. [MID_LEVEL · MULTIPLE_CHOICE] Which approach balances fast notifications with data accuracy?

```json
{
 "options": [
  "Trust-but-verify with quick validation",
  "Always wait for full consensus before notifying",
  "Accept all data immediately",
  "Block suspicious data permanently"
 ],
 "correctAnswer": 0
}
```

**Explanation:** Trust-but-verify accepts data immediately for fast response times but quickly validates suspicious changes. This approach provides low latency for legitimate data while maintaining accuracy by catching and correcting errors rapidly.

## 5. [MID_LEVEL · TRUE_FALSE] For long-range price history charts, using a coarser granularity such as daily averages can help meet latency targets compared with returning every raw price sample.

```json
{
 "correctAnswer": true
}
```

**Explanation:** The article includes a granularity parameter so the API can return daily averages for longer periods and more detailed data for recent timeframes. Coarser data reduces the number of points that must be read, transferred, and rendered, which helps keep price history queries under the <500ms target.

## 6. [MID_LEVEL · MULTIPLE_CHOICE] Why does the article place product_id in the URL path for the price history endpoint instead of in the request body?

```json
{
 "options": [
  "It prevents users from requesting price history for untracked products",
  "It guarantees strongly consistent reads from the price database",
  "It improves cacheability and aligns better with REST conventions",
  "It allows the crawler to scrape Amazon pages faster"
 ],
 "correctAnswer": 2
}
```

**Explanation:** A GET endpoint like `/products/{product_id}/price` is easier for HTTP caches and intermediaries to key by URL. Putting the resource identifier in the path also makes the API more RESTful because the URL directly identifies the product price-history resource being retrieved.

## 7. [MID_LEVEL · MULTIPLE_CHOICE] When crawling resources are limited, which strategy maximizes user value?

```json
{
 "options": [
  "Crawl all products equally across every category",
  "Prioritize by user interest signals",
  "Focus on cheapest products",
  "Random selection approach"
 ],
 "correctAnswer": 1
}
```

**Explanation:** Prioritizing by user interest signals follows the Pareto principle - focusing limited resources on items that provide the most value to users. This approach maximizes system effectiveness when resources are constrained.

## 8. [MID_LEVEL · MULTIPLE_CHOICE] When external APIs impose strict rate limits, which strategy helps systems scale effectively?

```json
{
 "options": [
  "Add more servers to distribute requests across regions",
  "Implement intelligent request prioritization",
  "Cache all responses indefinitely",
  "Use synchronous request processing"
 ],
 "correctAnswer": 1
}
```

**Explanation:** When external APIs have rate limits (like 1 request per second), adding more servers doesn't help since each server faces the same constraint. Systems must instead prioritize which requests are most valuable, potentially using techniques like user interest signals or crowdsourced data collection to work within the limits.

## 9. [MID_LEVEL · TRUE_FALSE] Event-driven notification systems eliminate expensive database scans for change detection.

```json
{
 "correctAnswer": true
}
```

**Explanation:** Event-driven systems publish notifications immediately when changes occur, eliminating the need to periodically scan large databases looking for changes. This approach scales much better as data volume grows because processing load is proportional to actual changes, not total data size.

## 10. [MID_LEVEL · MULTIPLE_CHOICE] Why does the design separate the Price History Service from the Web Crawler Service?

```json
{
 "options": [
  "They have different scaling patterns: user-facing reads are highly concurrent, while crawling is scheduled with steady writes",
  "The crawler must use a relational database, while the price history service must use a document database",
  "It ensures price drop notifications are delivered in real time",
  "It eliminates the need to validate scraped price data before storage"
 ],
 "correctAnswer": 0
}
```

**Explanation:** The Price History Service serves many user requests for charts, so it must scale for read concurrency and low latency. The Web Crawler Service operates on a schedule and writes collected prices, so separating them lets each be optimized and scaled independently.

## 11. [SENIOR · MULTIPLE_CHOICE] The API Gateway rate-limits incoming website and Chrome extension traffic, but Amazon still blocks the crawler. What design mistake does this reveal?

```json
{
 "options": [
  "The Price History Service should synchronously call Amazon on every chart request.",
  "The Primary Database should store price history so crawler writes are transactional.",
  "Inbound client rate limiting was confused with outbound crawler politeness controls.",
  "The Chrome extension should be disabled because browser clients cannot be authenticated."
 ],
 "correctAnswer": 2
}
```

**Explanation:** The API Gateway protects your own system from client traffic, but it does not automatically enforce Amazon's 1 request/second/IP scraping constraint. The crawler needs its own scheduling, throttling, and decoupling from read traffic so user chart views do not translate into uncontrolled Amazon requests.

## 12. [SENIOR · TRUE_FALSE] Merging the web crawler and Price History Service into one deployable service could simplify the architecture, but it creates a failure-mode where user chart traffic and scheduled crawl writes contend for the same compute and scaling knobs.

```json
{
 "correctAnswer": true
}
```

**Explanation:** The article separates these services because they have different scaling characteristics: the Price History Service handles high-concurrency reads, while the crawler performs scheduled writes. Combining them is not inherently impossible, but it weakens isolation and makes it harder to scale or protect one workload when the other spikes.

## 13. [SENIOR · MULTIPLE_CHOICE] Assume one Amazon product page requires one request, and Amazon allows 1 request/second/IP. Approximately how many IPs would be required to recrawl all 500 million products within the 1-hour notification window?

```json
{
 "options": [
  "139 IPs",
  "1,389 IPs",
  "13,889 IPs",
  "138,889 IPs"
 ],
 "correctAnswer": 3
}
```

**Explanation:** One IP can make 3,600 requests per hour, so 500,000,000 / 3,600 is about 138,889 IPs. This quantifies why a naive full-catalog hourly crawl is infeasible and why the design must prioritize high-value products and decouple collection from notification processing.

## 14. [SENIOR · RANKING] Rank these data collection strategies from least to most scalable for tracking 500 million products:

```json
{
 "items": [
  "Prioritized crawling based on user interest",
  "Naive web crawling of all products",
  "Chrome extension crowdsourcing with selective crawling"
 ],
 "correctOrder": [
  1,
  0,
  2
 ]
}
```

**Explanation:** Naive crawling cannot scale due to rate limits (15+ years to crawl 500M products). Prioritized crawling improves efficiency by focusing on high-value products but still faces rate limit constraints. Chrome extension crowdsourcing leverages 1 million users as a distributed data collection network, naturally scaling with user adoption while using crawlers only for verification.

## 15. [SENIOR · MULTIPLE_CHOICE] A user requests a multi-year price chart for a popular product, and the API exposes both `period` and `granularity`. Which implementation best preserves the article's sub-500ms price-history requirement at very large scale?

```json
{
 "options": [
  "Always return every raw price sample so the client can aggregate accurately.",
  "Bound the query with coarse granularity, such as daily aggregates for long periods and finer data only for recent windows.",
  "Move price history into the Primary Database so it can join directly with Products and Subscriptions.",
  "Trigger a fresh Amazon crawl before serving the chart to ensure the latest price is included."
 ],
 "correctAnswer": 1
}
```

**Explanation:** The article explicitly uses `granularity` so long-range requests can return daily averages while recent requests can use finer data. This avoids scanning and transferring excessive time-series rows, which would threaten the <500ms latency target.
