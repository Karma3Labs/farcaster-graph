#!/bin/bash

source .env

set -x
set -e  # Exit immediately if a command exits with a non-zero status
set -o pipefail  # Ensure pipeline failures are propagated


# TODO: move this to cli args
DATE_SUFFIX=$(date +"%Y%m%d" )
BACKUP_DIR="/tmp/sandbox-backup-$DATE_SUFFIX"
BACKUP_FILE="sandbox_pgdump"
S3_BUCKET='k3l-openrank-farcaster'
S3_PREFIX='pg_dump/'  

rm -rf "$BACKUP_DIR"
mkdir -p "$BACKUP_DIR"

set -e  # Re-enable error exit after this block

# Perform the backup
echo "Starting backup..."
set +x  # Disable command echoing
export PGPASSWORD="$SANDBOX_DB_PASSWORD"
set -x  # Re-enable command echoing
pg_dump -h $SANDBOX_DB_HOST -p $SANDBOX_DB_PORT -U $SANDBOX_DB_USER -d $SANDBOX_DB_NAME \
  -j 1 \
  -Fd \
  -f "$BACKUP_DIR/$BACKUP_FILE"
unset PGPASSWORD

# Check if backup was successful
if [ $? -eq 0 ]; then
    echo "Backup completed successfully"

    # Compress the backup
    tar czf "$BACKUP_DIR/$BACKUP_FILE.tgz" -C "$BACKUP_DIR" $BACKUP_FILE
    echo "Backup compressed"

    # Upload to S3
    echo "Uploading backup to S3..."
    aws s3 cp "$BACKUP_DIR/$BACKUP_FILE.tgz" "s3://$S3_BUCKET/$S3_PREFIX$BACKUP_FILE.tgz"

    if [ $? -eq 0 ]; then
        echo "Backup successfully uploaded to S3"
    else
        echo "Failed to upload backup to S3"
        exit 1
    fi
else
    echo "Backup failed"
    exit 1
fi

cleanup
exit 0
