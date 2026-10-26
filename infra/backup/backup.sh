#!/bin/sh
# Dump the database and upload it to S3-compatible storage. Runs from crond (crontab) or by hand:
# docker compose exec backup /backup.sh
# busybox crond hands its own (container) environment to jobs, so POSTGRES_PASSWORD and BACKUP_S3_* arrive from env_file
# shortcut: a failed run is only a line in the container log, no alert; add one when the data is worth it
set -euo pipefail

file=/tmp/devplus-$(date -u +%Y%m%dT%H%M%SZ).sql.gz
# the local file goes away on success and on failure, a failed run leaves one line in the container log
trap 'rc=$?; rm -f "$file"; if [ "$rc" -ne 0 ]; then echo "backup FAILED (exit $rc): nothing uploaded" >&2; fi' EXIT

: "${POSTGRES_PASSWORD:?is not set}" "${BACKUP_S3_ENDPOINT:?is not set}" "${BACKUP_S3_BUCKET:?is not set}"
: "${BACKUP_S3_ACCESS_KEY:?is not set}" "${BACKUP_S3_SECRET_KEY:?is not set}"
export PGPASSWORD=$POSTGRES_PASSWORD AWS_ACCESS_KEY_ID=$BACKUP_S3_ACCESS_KEY AWS_SECRET_ACCESS_KEY=$BACKUP_S3_SECRET_KEY

# with pipefail a pg_dump error stops the script here, before the upload
pg_dump --clean --if-exists -h postgres -U devplus devplus | gzip > "$file"
aws s3 cp "$file" "s3://$BACKUP_S3_BUCKET/" --endpoint-url "$BACKUP_S3_ENDPOINT" --no-progress
echo "backup OK: $(basename "$file")"
