# Proximity Search Quiz

## 1. [JUNIOR · TRUE_FALSE] A spatial index typically produces the final answer to a proximity query on its own, with no further distance computation needed.

```json
{
 "correctAnswer": false
}
```

**Explanation:** A spatial index almost never produces the final answer. Its job is to turn "check every row" into "check a small candidate set," and you finish with exact distance or geometry math on those candidates. Every spatial structure is just a different way to generate that candidate set cheaply.

## 2. [JUNIOR · TRUE_FALSE] In a quadtree, the data points live only in the leaf nodes.

```json
{
 "correctAnswer": true
}
```

**Explanation:** Internal quadtree nodes just define how space is divided -- the points themselves live in the leaves. A search walks from the root down to a leaf, then scans that leaf's points (plus neighboring leaves, so you don't miss someone just across a boundary) as the candidate set.

## 3. [MID_LEVEL · MULTIPLE_CHOICE] Why do classic quadtrees and k-d trees perform poorly as on-disk database indexes?

```json
{
 "options": [
  "They can only store integer coordinates, not floating point",
  "They're pointer structures, so traversal risks a random disk read at every hop",
  "They require the entire dataset to be sorted before every query",
  "Their nodes are too large to fit in a database page"
 ],
 "correctAnswer": 1
}
```

**Explanation:** Both are pointers all the way down, with nodes at arbitrary addresses. That's cheap in RAM but painful on disk, where each pointer hop risks a random page read. Disk-friendly structures fix this by packing data into page-sized blocks -- that's exactly what BKD trees and R-trees do.

## 4. [MID_LEVEL · MULTIPLE_CHOICE] What problem does S2 solve that geohash struggles with at planet scale?

```json
{
 "options": [
  "Geohash keys are strings, which most databases can't index efficiently",
  "Geohash treats the earth as a flat rectangle, so cell sizes distort badly with latitude",
  "Geohash cells can't be truncated to get a parent cell",
  "Geohash requires a dedicated spatial extension to query"
 ],
 "correctAnswer": 1
}
```

**Explanation:** A degree of longitude is ~111km at the equator but shrinks toward zero at the poles, so flat-grid geohash cells become thin slivers up north. S2 projects the globe onto a cube's six faces, keeping cells roughly equal-area everywhere, and correctly handles cases a flat grid mangles like polygons crossing the antimeridian.

## 5. [MID_LEVEL · TRUE_FALSE] For constantly moving point data like driver locations, encoded-cell approaches are preferred over R-trees largely because a location update becomes a single integer update.

```json
{
 "correctAnswer": true
}
```

**Explanation:** A moving driver in an encoded-cell system is just an integer changing value on an ordinary index, which scales to millions of writes per second. R-trees pay real rebalancing cost per update, and the BKD variant is essentially write-once. That write-cost difference is the main reason dispatch systems use geohash, S2, or H3.

## 6. [MID_LEVEL · MATCHING_PAIRS] Match each production system to the spatial structure underneath it:

```json
{
 "leftItems": [
  "PostGIS",
  "Elasticsearch geo fields",
  "Redis geo commands",
  "MongoDB 2dsphere"
 ],
 "rightItems": [
  "Geohash stored as a 52-bit integer in a sorted set",
  "S2 cells",
  "R-tree-style bounding boxes via the GiST framework",
  "BKD trees"
 ],
 "correctPairs": [
  2,
  3,
  0,
  1
 ]
}
```

**Explanation:** PostGIS builds R-tree-style spatial indexes on Postgres's GiST framework. Elasticsearch uses BKD trees for geo fields. Redis GEOADD interleaves lat/lng into a 52-bit geohash integer stored as a sorted-set score. MongoDB's 2dsphere index is built on Google's S2 cell system.

## 7. [MID_LEVEL · RANKING] Put the steps of an encoded-key proximity query (like H3 dispatch) in order:

```json
{
 "items": [
  "Compute the ring of neighboring cells around it",
  "Compute the cell ID for the query point",
  "Look up candidates whose cell ID is in that list using an ordinary index",
  "Post-filter the candidates by exact distance"
 ],
 "correctOrder": [
  1,
  0,
  2,
  3
 ]
}
```

**Explanation:** You snap the query point to its cell, expand to the surrounding ring (going wider if you need a bigger net), fetch everything in those cells with a plain WHERE ... IN lookup on an ordinary integer index, then finish with exact distance math. Cheap writes, cheap candidate generation, no spatial extension anywhere.

## 8. [MID_LEVEL · MULTIPLE_CHOICE] A rider stands right at the edge of geohash cell dr5ru, and the nearest driver is ten meters away in neighboring cell dr5rg. How do production systems avoid missing that driver?

```json
{
 "options": [
  "Use longer geohash prefixes so cells are smaller",
  "Store each driver in every cell they're near, not just their own",
  "Query the rider's cell plus the eight neighboring cells, then post-filter by exact distance",
  "Fall back to a full table scan whenever a query point is near a boundary"
 ],
 "correctAnswer": 2
}
```

**Explanation:** This is the 3x3 trick: query the query point's cell plus its eight neighbors as a unit, so nothing within one cell's distance can be missed, then post-filter by exact distance to drop candidates that are technically in the window but too far. Longer prefixes make boundary effects worse, not better -- smaller cells mean more boundaries.

## 9. [MID_LEVEL · TRUE_FALSE] In an R-tree, bounding rectangles at the same level of the tree never overlap.

```json
{
 "correctAnswer": false
}
```

**Explanation:** R-tree rectangles can and do overlap -- that's the structure's key tradeoff. If a query point lands inside two rectangles, you must descend both subtrees. A sloppy insertion strategy creates lots of overlap and drags performance down, which is why production implementations use R*-tree insertion heuristics to keep overlap low.

## 10. [MID_LEVEL · TRUE_FALSE] Elasticsearch's geo fields are built on BKD trees, which are essentially write-once structures built from a batch of data.

```json
{
 "correctAnswer": true
}
```

**Explanation:** A BKD (block k-d) tree packs points into disk-page-sized blocks and is built once from a batch, which makes it disk-friendly but essentially write-once. That's why Elasticsearch geo indexes don't love constantly churning data -- a constraint that matters when you're indexing millions of moving drivers.

## 11. [SENIOR · MULTIPLE_CHOICE] You're designing a food delivery platform that must answer "which delivery zones contain this address?" over polygons that rarely change. Which indexing approach fits best?

```json
{
 "options": [
  "Geohash prefixes on the zone centroids, with a 3x3 neighbor query",
  "H3 cells at fine resolution, storing each zone as its center cell",
  "Redis geo commands with zones stored as points",
  "An R-tree-style spatial index like PostGIS, since the data is geometric and writes are rare"
 ],
 "correctAnswer": 3
}
```

**Explanation:** Containment questions over polygons are exactly what custom spatial trees are for -- an R-tree wraps each zone in a bounding rectangle and handles points, lines, and polygons alike. The encoded-key options all reduce zones to points, which throws away the geometry you need. The R-tree's costlier writes don't matter when zones rarely change.

## 12. [SENIOR · MULTIPLE_CHOICE] An R-tree-backed query for a single point is unexpectedly descending many subtrees before returning. What's the most likely cause, and the standard fix?

```json
{
 "options": [
  "The tree is unbalanced from deletes; fix by rebuilding it nightly",
  "Heavy overlap between bounding rectangles from a poor insertion strategy; fix with R*-tree insertion heuristics",
  "The point matches multiple exact rows; fix by deduplicating the data",
  "Disk pages are too small for the nodes; fix by increasing the page size"
 ],
 "correctAnswer": 1
}
```

**Explanation:** When bounding rectangles overlap, a query point inside several of them forces the search down every matching branch. Sloppy insertion produces lots of overlap and lots of wasted descents. The R*-tree's smarter insertion heuristics keep overlap low, which is why nearly every modern R-tree implementation is built on them. R-trees stay balanced like B-trees, so imbalance isn't the issue.

## 13. [SENIOR · TRUE_FALSE] Like geohash and S2, H3 lays its cells along a space-filling curve, so a numeric range scan over H3 IDs sweeps up a geographic neighborhood.

```json
{
 "correctAnswer": false
}
```

**Explanation:** This is H3's key structural difference: close H3 IDs aren't reliably close on the map, so range scans don't work. Instead H3 provides cheap grid math to compute the exact ring of cells around any cell, and you look those IDs up directly with WHERE h3_cell IN (...). Geohash and S2 are the ones where prefix/range scans sweep up neighborhoods.

## 14. [SENIOR · MULTIPLE_CHOICE] Why doesn't a composite B-tree index on (latitude, longitude) fix the proximity search problem?

```json
{
 "options": [
  "Composite indexes can't include more than one numeric column",
  "The index sorts by latitude and only breaks ties with longitude, so it still effectively sorts on one dimension",
  "Composite indexes only support equality predicates on the second column",
  "The index becomes too large to fit in memory once both columns are included"
 ],
 "correctAnswer": 1
}
```

**Explanation:** A B-tree sorts by the first column and uses the second only to break ties, so a composite (lat, lng) index still pulls back a huge one-dimensional strip with rows unranked by distance. The root problem is unchanged: a single sort order can't preserve two-dimensional closeness. That's what spatial trees and encoded keys exist to recover.

## 15. [SENIOR · MULTIPLE_CHOICE] A quadtree-backed service shows fast proximity queries in rural areas but much slower ones in dense city centers. What's the most likely structural cause?

```json
{
 "options": [
  "Splits land at each cell's geometric midpoint rather than where the data clusters, so dense areas produce much deeper trees",
  "City data contains more polygons, which quadtrees must convert to points",
  "The tree rebalances on every insert, and cities have more inserts",
  "Urban cells contain more empty space, wasting index pages"
 ],
 "correctAnswer": 0
}
```

**Explanation:** Quadtree splits always halve cells at the geometric midpoint, never adapting to where points actually sit, so a dense cluster like Manhattan takes ten or more levels to separate while rural Vermont resolves in two. Query latency ends up depending on where you're looking, with the busiest regions slowest -- a big reason quadtrees are hard to reason about at scale.
