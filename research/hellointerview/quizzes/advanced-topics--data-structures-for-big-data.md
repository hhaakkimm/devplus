# Data Structures for Big Data System Design Quiz

## 1. [JUNIOR · MULTIPLE_CHOICE] What does Count-Min Sketch provide as output when querying for an element?

```json
{
 "options": [
  "The exact count of occurrences across all hash rows",
  "An upper bound estimate of occurrences",
  "A lower bound estimate of occurrences",
  "Whether the element exists or not"
 ],
 "correctAnswer": 1
}
```

**Explanation:** Count-Min Sketch provides an upper bound on the count by taking the minimum across all hash buckets for an element. Due to collisions, this estimate is never lower than the true count.

## 2. [JUNIOR · MATCHING_PAIRS] Match each probabilistic data structure to its primary use case:

```json
{
 "leftItems": [
  "Bloom Filter",
  "Count-Min Sketch",
  "HyperLogLog",
  "Histogram Buckets"
 ],
 "rightItems": [
  "Estimating unique item count",
  "Tracking frequency counts",
  "Calculating percentiles",
  "Checking set membership"
 ],
 "correctPairs": [
  3,
  1,
  0,
  2
 ]
}
```

**Explanation:** Each data structure serves a distinct purpose: Bloom Filters check if items exist in a set, Count-Min Sketch tracks how often items appear, HyperLogLog counts unique items, and Histogram Buckets calculate percentile distributions.

## 3. [MID_LEVEL · MULTIPLE_CHOICE] When should you NOT use these probabilistic data structures?

```json
{
 "options": [
  "When dealing with billions of items across distributed nodes",
  "When you need exact results and have enough memory",
  "When implementing caching systems",
  "When building analytics systems"
 ],
 "correctAnswer": 1
}
```

**Explanation:** If you require exact results and have sufficient memory for traditional data structures, probabilistic structures add unnecessary complexity. Use them only when space constraints make approximate results worthwhile.

## 4. [MID_LEVEL · TRUE_FALSE] Increasing the number of hash functions in a Bloom Filter can help distinguish elements, but it also sets more bits per insertion, so k should be chosen together with the filter size rather than treated as a free improvement.

```json
{
 "correctAnswer": true
}
```

**Explanation:** The article explains that Bloom Filters hash each inserted element k times and set the corresponding bits. More hashes can improve uniqueness, but they also fill the bit array faster; as the filter becomes saturated, false positives become more likely.

## 5. [MID_LEVEL · MULTIPLE_CHOICE] Which data structure would be most appropriate for implementing a cache that needs to track access frequency for LFU (Least Frequently Used) eviction?

```json
{
 "options": [
  "Bloom Filter",
  "Count-Min Sketch",
  "HyperLogLog",
  "Standard Hash Table"
 ],
 "correctAnswer": 1
}
```

**Explanation:** Count-Min Sketch is ideal for tracking access frequencies when you have many cache keys. It provides upper-bound estimates of access counts while using much less memory than tracking exact counts.

## 6. [MID_LEVEL · MULTIPLE_CHOICE] Why does a Bloom Filter hash each inserted element multiple times instead of using one large, dense bit pattern per element?

```json
{
 "options": [
  "To make deletions safe without extra metadata.",
  "To guarantee there are no false positives.",
  "To store the element value across several positions.",
  "To create limited but distinctive bit patterns that reduce accidental overlap."
 ],
 "correctAnswer": 3
}
```

**Explanation:** The article compares this to using stamps that are unique but not solid. Multiple hash functions set a small number of positions, helping distinguish elements while avoiding a pattern that would quickly saturate the filter.

## 7. [MID_LEVEL · MULTIPLE_CHOICE] In a web crawling system, what would be the best use case for a Bloom Filter?

```json
{
 "options": [
  "Storing the content of crawled pages",
  "Tracking how many times each URL was visited across all workers",
  "Checking if a URL was likely crawled before",
  "Counting unique domains discovered"
 ],
 "correctAnswer": 2
}
```

**Explanation:** Bloom Filters excel at membership testing. In web crawling, you can use them to quickly check if a URL has probably been seen before, avoiding redundant crawling while using minimal memory.

## 8. [MID_LEVEL · MULTIPLE_CHOICE] A web crawler uses a Bloom Filter to track visited URLs. If the filter returns a false positive for a new URL, what is the likely system-level effect?

```json
{
 "options": [
  "The crawler will store the full URL in memory twice.",
  "The crawler will crawl the same page repeatedly.",
  "The crawler may incorrectly skip crawling that URL.",
  "The crawler will know the URL was never visited."
 ],
 "correctAnswer": 2
}
```

**Explanation:** A Bloom Filter false positive means it reports an element as probably present even when it is not. In a crawler, that can cause the system to believe a new URL was already seen, so it may skip crawling that page.

## 9. [MID_LEVEL · MULTIPLE_CHOICE] You are designing a Bloom Filter and want to reduce its false positive rate while keeping the same expected number of inserted items. Which change is most aligned with the article?

```json
{
 "options": [
  "Increase the bit array size and choose an appropriate number of hash functions.",
  "Store the original elements alongside the Bloom Filter.",
  "Use only one hash function so fewer bits are set per insert.",
  "Allow bits to be unset when queries return false positives."
 ],
 "correctAnswer": 0
}
```

**Explanation:** Bloom Filters are sized by choosing parameters like the number of bits and the number of hash functions. More bits can reduce saturation and false positives, but it increases memory usage, which is the main tradeoff the article highlights.

## 10. [MID_LEVEL · MULTIPLE_CHOICE] For tracking Daily Active Users (DAU) across millions of users, which data structure would be most appropriate?

```json
{
 "options": [
  "Bloom Filter",
  "Count-Min Sketch",
  "HyperLogLog",
  "Binary Search Tree"
 ],
 "correctAnswer": 2
}
```

**Explanation:** DAU requires counting unique users, which is a cardinality estimation problem. HyperLogLog is specifically designed for this use case and can efficiently estimate unique user counts with minimal memory.

## 11. [SENIOR · MULTIPLE_CHOICE] You maintain one HyperLogLog sketch per day for unique active users and want the number of unique users across the whole week. Some users are active on multiple days. What should you do?

```json
{
 "options": [
  "Sum the seven daily cardinality estimates, because each sketch already deduplicates its own day.",
  "Average the seven daily estimates and multiply by seven to smooth out HyperLogLog error.",
  "Merge the sketches to estimate the union, rather than adding the daily estimates.",
  "Extract the user IDs from each sketch, deduplicate them exactly, and then count them."
 ],
 "correctAnswer": 2
}
```

**Explanation:** Adding daily unique counts double-counts users who appear on multiple days. HyperLogLog is useful in distributed or time-windowed systems because sketches can be merged to estimate the cardinality of the union without storing the original user IDs.

## 12. [SENIOR · TRUE_FALSE] For a fixed Bloom Filter size and expected item count, increasing the number of hash functions can eventually make the filter worse by setting too many bits and increasing saturation.

```json
{
 "correctAnswer": true
}
```

**Explanation:** More hash functions make each item’s signature more distinctive up to a point, but each inserted item also sets more bits. If too many bits become set, unrelated queries are more likely to find all required bits set, raising the false-positive rate.

## 13. [SENIOR · MULTIPLE_CHOICE] A Count-Min Sketch is used to approximate request frequencies for LFU cache eviction. A rarely requested key collides in the sketch with several very hot keys. What is the expected failure mode?

```json
{
 "options": [
  "The rare key’s frequency may be underestimated, causing it to be evicted too aggressively.",
  "The rare key’s frequency may be overestimated, making it look hotter than it really is.",
  "The sketch will detect the collision and return an exact count for the rare key.",
  "The sketch will return whether the rare key is present, but not any frequency estimate."
 ],
 "correctAnswer": 1
}
```

**Explanation:** Count-Min Sketch counters only increase, so collisions add extra counts from other keys. Taking the minimum across hash rows reduces the error, but the estimate can still be higher than the true frequency, which can falsely protect cold items from eviction.

## 14. [SENIOR · TRUE_FALSE] When using a Bloom Filter as a lightweight guard before a remote cache, a “maybe present” result is sufficient to return the cached value without querying the cache.

```json
{
 "correctAnswer": false
}
```

**Explanation:** A Bloom Filter stores only membership evidence, not the cached object, and it can return false positives. A positive result should only route the request to the cache; a negative result can safely skip the cache lookup because the item is definitely not present.

## 15. [SENIOR · MULTIPLE_CHOICE] You need to track membership for 1B 4-byte IDs with about a 1% Bloom Filter false-positive rate. Based on the article’s sizing guidance, which conclusion is most appropriate?

```json
{
 "options": [
  "A Bloom Filter is roughly 1GB versus about 5GB for a well-optimized hash table, so it is a meaningful but not orders-of-magnitude memory win.",
  "A Bloom Filter will fit in a few kilobytes because it stores only hash-derived bits, so it is effectively free at this scale.",
  "A Bloom Filter and hash table require about the same memory because both must retain every original 4-byte ID.",
  "A Bloom Filter can always be made smaller by increasing the number of hash functions without affecting accuracy."
 ],
 "correctAnswer": 0
}
```

**Explanation:** The article explicitly warns that Bloom Filters are larger than many people expect: around 1GB for 1B 4-byte elements at a 1% false-positive rate. That is still a large savings over an estimated 5GB hash table, but it is not a tiny or free structure.
