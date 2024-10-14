#!/bin/bash

source .env

set -x
set -e  # Exit immediately if a command exits with a non-zero status
set -o pipefail  # Ensure pipeline failures are propagated


# TODO: move this to cli args
BACKUP_DIR="/tmp"
BACKUP_FILE="sandbox-backup.tar.gz"
S3_BUCKET='k3l-openrank-farcaster'
S3_PREFIX='pg_dump/'  

# Create backup directory from clean state
rm -rf "$BACKUP_DIR"
mkdir -p "$BACKUP_DIR"

set -e  # Re-enable error exit after this block

# Perform the backup
echo "Starting backup..."
set +x  # Disable command echoing
export PGPASSWORD="$SANDBOX_DB_PASSWORD"
set -x  # Re-enable command echoing
pg_dump -h $SSH_LISTEN_HOST -p $SSH_LISTEN_PORT -U $SANDBOX_DB_USER -d $SANDBOX_DB_NAME \
  -j 1 \
  -Fd \
  -f "$BACKUP_DIR/backup"
unset PGPASSWORD

# Check if backup was successful
if [ $? -eq 0 ]; then
    echo "Backup completed successfully"

    # Compress the backup
    tar czf "$BACKUP_DIR/$BACKUP_FILE" -C "$BACKUP_DIR" backup
    echo "Backup compressed"

    # Upload to S3
    echo "Uploading backup to S3..."
    aws s3 cp "$BACKUP_DIR/$BACKUP_FILE" "s3://$S3_BUCKET/$S3_PREFIX$BACKUP_FILE"

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
