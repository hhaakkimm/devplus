# Dropbox System Design Quiz

## 1. [JUNIOR · MATCHING_PAIRS] Match each Dropbox system component to its primary responsibility:

```json
{
 "leftItems": [
  "CDN",
  "File Service",
  "S3",
  "File Metadata DB"
 ],
 "rightItems": [
  "Stores file name, size, and ownership info",
  "Caches files at edge locations near users",
  "Generates presigned URLs and manages metadata writes",
  "Stores the actual file bytes"
 ],
 "correctPairs": [
  1,
  2,
  3,
  0
 ]
}
```

**Explanation:** Each component has a distinct role: CDN caches content geographically for fast downloads, File Service handles API logic and presigned URL generation, S3 stores the raw file data, and the Metadata DB tracks file properties and relationships.

## 2. [JUNIOR · MULTIPLE_CHOICE] Why are S3 event notifications more reliable than client-side completion callbacks for updating file metadata?

```json
{
 "options": [
  "S3 events are faster",
  "S3 events work even if the client crashes after uploading",
  "S3 events use less bandwidth",
  "S3 events provide encryption"
 ],
 "correctAnswer": 1
}
```

**Explanation:** If a client crashes or loses network connection right after uploading, it can't send a completion callback. S3 event notifications fire directly from S3 after confirming the upload, ensuring metadata gets updated regardless of client state. Polling is an alternative that also handles this case.

## 3. [MID_LEVEL · MULTIPLE_CHOICE] Why is a NoSQL database like DynamoDB a reasonable choice for storing Dropbox file metadata in the article's design?

```json
{
 "options": [
  "The metadata is loosely structured, has few relations, and is mainly queried by user",
  "The raw file bytes must be stored in the same database as the metadata",
  "NoSQL databases automatically provide perfect cross-region consistency for file sync",
  "Blob storage cannot store files unless their metadata is in DynamoDB"
 ],
 "correctAnswer": 0
}
```

**Explanation:** The article separates raw file contents from metadata: file bytes go to Blob Storage, while metadata like name, size, MIME type, and uploader goes to a database. DynamoDB is reasonable because the metadata access pattern is simple, though the article notes that PostgreSQL could also work.

## 4. [MID_LEVEL · TRUE_FALSE] Last-write-wins strategy ensures strong data consistency in distributed file systems.

```json
{
 "correctAnswer": false
}
```

**Explanation:** Last-write-wins provides eventual consistency, not strong consistency. It resolves conflicts by accepting the most recent update, but doesn't prevent concurrent modifications or guarantee immediate consistency across all nodes.

## 5. [MID_LEVEL · TRUE_FALSE] Web servers and browsers impose payload size limits that prevent large files from being uploaded in a single HTTP request.

```json
{
 "correctAnswer": true
}
```

**Explanation:** Most web servers (Apache, NGINX) default to ~2GB request limits, while services like API Gateway often limit requests to 10MB or less. Browsers also impose their own limits. These hard constraints make chunking necessary for large file uploads, not just beneficial.

## 6. [MID_LEVEL · MULTIPLE_CHOICE] After a network interruption, what does the client need to resume a chunked upload without re-sending the parts it already finished?

```json
{
 "options": [
  "The original file path on the user's local disk",
  "The user's login credentials",
  "The file's fingerprint plus which chunks the server has already stored",
  "Network diagnostics such as latency and packet loss"
 ],
 "correctAnswer": 2
}
```

**Explanation:** Resuming takes two pieces of state: a stable identifier for the upload (a content fingerprint or the multipart uploadId) to find the in-progress transfer, and the per-chunk completion status so only the missing chunks are re-sent. The file path, credentials, and network metrics don't tell the system where the transfer left off.

## 7. [MID_LEVEL · MULTIPLE_CHOICE] In a file storage system like Dropbox, when a network partition occurs, which property should the system prioritize?

```json
{
 "options": [
  "Consistency - block access until all nodes agree",
  "Availability - allow access even with stale data",
  "Neither - shut down the system until the partition heals",
  "Both can be fully maintained during a partition"
 ],
 "correctAnswer": 1
}
```

**Explanation:** File storage systems prioritize availability over consistency during partitions. Users expect to access their files even when some nodes can't communicate. Temporary inconsistency (like a file taking seconds to appear on another device) is acceptable, while blocking access would be a poor user experience.

## 8. [MID_LEVEL · MULTIPLE_CHOICE] A user's laptop was offline for several hours and now needs to sync with the server. Which API design from the article best avoids downloading unnecessary data?

```json
{
 "options": [
  "GET /files to download every file and compare contents locally",
  "POST /files with the user's local files to let the server resolve differences",
  "GET /files/changes?since={timestamp} to fetch only recent change events",
  "GET /files/{fileId} for each known file regardless of whether it changed"
 ],
 "correctAnswer": 2
}
```

**Explanation:** The article proposes a changes endpoint that accepts a `since` timestamp and returns only `ChangeEvent`s that occurred after the client's last sync. This avoids scanning or downloading all files, which would be slow and wasteful as a user's file count grows.

## 9. [MID_LEVEL · TRUE_FALSE] Parallel chunk uploads can maximize available bandwidth utilization.

```json
{
 "correctAnswer": true
}
```

**Explanation:** Parallel uploads utilize multiple connections simultaneously, allowing systems to saturate available bandwidth more effectively than sequential transfers. This is especially beneficial for high-latency or high-bandwidth connections.

## 10. [MID_LEVEL · MULTIPLE_CHOICE] A system needs to upload 50GB files reliably. Which approach works best?

```json
{
 "options": [
  "Single HTTP POST request",
  "Chunked multipart upload",
  "Direct database insertion",
  "Email attachment"
 ],
 "correctAnswer": 1
}
```

**Explanation:** Chunked multipart upload breaks large files into manageable pieces, enabling progress tracking, resumability on failure, and avoiding timeout issues that plague single large requests.

## 11. [SENIOR · RANKING] Rank these file upload approaches from best to worst:

```json
{
 "items": [
  "Upload to backend server, then server uploads to blob storage",
  "Upload directly to blob storage using presigned URLs",
  "Upload to backend server and store on local filesystem"
 ],
 "correctOrder": [
  1,
  0,
  2
 ]
}
```

**Explanation:** Direct upload to blob storage via presigned URLs is optimal because it eliminates the double-upload and reduces load on application servers. Uploading through the backend to blob storage still works but doubles upload time and consumes server bandwidth. Storing on a local filesystem is worst because it doesn't scale and isn't reliable.

## 12. [SENIOR · MULTIPLE_CHOICE] The article's hybrid sync uses WebSocket or SSE notifications plus periodic `GET /files/changes?since={timestamp}` polling. If the live connection drops while files change, how does the design recover without sacrificing low-latency updates when connected?

```json
{
 "options": [
  "Use live notifications when connected and periodic polling to retrieve any changes missed during the gap.",
  "Open one socket per file and discard changes that occurred before each socket reconnected.",
  "Treat local files as the source of truth after a disconnect and upload them over the live connection.",
  "Disable live notifications after the first disconnect and download all file metadata on every sync."
 ],
 "correctAnswer": 0
}
```

**Explanation:** WebSocket or SSE notifications deliver changes quickly while the connection is healthy, but messages can be missed during a disconnect. Periodic polling from the last sync timestamp catches those missed changes and provides eventual consistency without giving up the low-latency push path.

## 13. [SENIOR · TRUE_FALSE] If a Dropbox-style client sets `since` in `GET /files/changes?since={timestamp}` using its own local device clock rather than a server-issued sync timestamp, clock skew can cause the client to miss some `ChangeEvent`s.

```json
{
 "correctAnswer": true
}
```

**Explanation:** The sync API depends on `since` being a reliable boundary for server-side changes. If the client clock is ahead of the server, it may ask for changes after a timestamp that excludes events the server considers earlier, so production systems typically use a server-generated cursor or high-watermark from the last successful sync.

## 14. [SENIOR · MULTIPLE_CHOICE] A backend-mediated upload writes the file bytes to Blob Storage and then writes FileMetadata to the database. The Blob Storage write succeeds, but the metadata write times out and the client retries. Which design response best matches the article’s intended reliability concern?

```json
{
 "options": [
  "Return success because the raw bytes exist; metadata can be reconstructed from Blob Storage later.",
  "Treat the blob and metadata update as a single logical transaction or workflow so the system does not permanently commit one without the other.",
  "Store the file only on the File Service’s local disk until all retries finish.",
  "Use last-write-wins on the metadata row so the retry overwrites any partial state."
 ],
 "correctAnswer": 1
}
```

**Explanation:** The article explicitly calls out the split-brain failure mode where the file is uploaded but metadata is not saved, or metadata is saved but the file is not uploaded. The key design judgment is to make the two writes behave atomically from the product’s perspective, or to have a compensating workflow that cleans up partial state.

## 15. [SENIOR · MULTIPLE_CHOICE] A malicious client calls `POST /files/{fileId}/share` and includes an `uploadedBy` field in the request body claiming to be the file owner. According to the article’s API guidance, what should the server do?

```json
{
 "options": [
  "Trust `uploadedBy` only if it matches the `fileId` prefix.",
  "Accept the request because sharing requires the target user list to be in the body.",
  "Ignore caller identity fields in the body; derive the requester from the session token or JWT headers and authorize against stored metadata.",
  "Require the client to also send the owner’s email address to reduce ambiguity."
 ],
 "correctAnswer": 2
}
```

**Explanation:** The article says user information should come from authenticated headers, such as a session token or JWT, not from the request body. Body fields are client-controlled and can be manipulated, so authorization must be based on trusted identity plus server-side file metadata.
