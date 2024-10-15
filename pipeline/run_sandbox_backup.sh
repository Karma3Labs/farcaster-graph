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

# Pick an available port
# read lower_port upper_port < /proc/sys/net/ipv4/ip_local_port_range
lower_port=32768
upper_port=60999

for (( port = lower_port ; port <= upper_port ; port++ )); do
    if ! nc -z 127.0.0.1 "$port"; then
        LOCAL_PORT=$port
        break
    fi
done

# SSH details
SSH_KEY=$SSH_KEY_PATH
SSH_USER=$SANDBOX_REMOTE_USER # Unix user on the remote server.
SSH_HOST=$SANDBOX_REMOTE_HOST # The hostname of the remote server.
REMOTE_HOST=127.0.0.1  # The ip that Postgres binds to on the remote server.
REMOTE_PORT=$SANDBOX_REMOTE_PORT  # The port Postgres listens on the remote server.

#DB details
DB_NAME=$SANDBOX_DB_NAME
DB_USER=$SANDBOX_DB_USER
DB_PASSWORD=$SANDBOX_DB_PASSWORD

# Function to clean up SSH tunnel and temporary files
cleanup() {
    echo "Cleaning up..."
    if [ -n "$SSH_PID" ]; then
        kill $SSH_PID 2>/dev/null || true
        wait $SSH_PID 2>/dev/null || true
    fi
    unset PGPASSWORD
    rm -rf "$BACKUP_DIR/backup"
}

# Trap EXIT, SIGINT, and SIGTERM (SIGKILL cannot be trapped)
trap cleanup EXIT SIGINT SIGTERM

rm -rf "$BACKUP_DIR"
mkdir -p "$BACKUP_DIR"
# Ensure the SSH host key is already known
ssh-keyscan -H "$SSH_HOST" >> ~/.ssh/known_hosts 2>/dev/null || true

# Kill any binding port if there is one.
set +e  # Disable error exit to handle empty lsof result
PID=$(lsof -t -i:$LOCAL_PORT)

if [ -z "$PID" ]; then
  echo "No process found binding to port $LOCAL_PORT."
else
  echo "Found process $PID binding to port $LOCAL_PORT."

  # Kill the process
  kill -9 $PID

  if [ $? -eq 0 ]; then
    echo "Process $PID has been terminated."
  else
    echo "Failed to terminate process $PID."
  fi
fi
set -e  # Re-enable error exit after this block

# Start SSH tunnel
echo "Starting SSH tunnel..."
ssh -i "$SSH_KEY" -N -L $LOCAL_PORT:$REMOTE_HOST:$REMOTE_PORT $SSH_USER@$SSH_HOST &
SSH_PID=$!

# Wait for the tunnel to establish or fail
for i in {1..30}; do
    if nc -z localhost $LOCAL_PORT >/dev/null 2>&1; then
        echo "SSH tunnel established successfully"
        break
    fi
    if ! kill -0 $SSH_PID 2>/dev/null; then
        echo "SSH process terminated unexpectedly"
        exit 1
    fi
    sleep 1
done

# Check if the tunnel is established
if ! nc -z localhost $LOCAL_PORT; then
    echo "Failed to establish SSH tunnel after 30 seconds"
    kill $SSH_PID 2>/dev/null
    exit 1
fi

# Perform the backup
echo "Starting backup..."
set +x  # Disable command echoing
export PGPASSWORD="$DB_PASSWORD"
set -x  # Re-enable command echoing
pg_dump -h localhost -p $LOCAL_PORT -U $DB_USER -d $DB_NAME \
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
