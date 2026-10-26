# 3.21, not 3.20: postgresql17-client first appears in 3.21 (pg_dump must not be older than the server)
FROM alpine:3.21
RUN apk add --no-cache postgresql17-client aws-cli
COPY backup.sh /
COPY crontab /etc/crontabs/root
# -d 8: crond logs job starts to stderr (container log); job output goes there too
CMD ["crond", "-f", "-d", "8"]
