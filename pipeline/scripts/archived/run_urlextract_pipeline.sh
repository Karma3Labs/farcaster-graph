#!/bin/bash

while getopts w: flag
do
    case "${flag}" in
        w) WORK_DIR=${OPTARG};;
    esac
done

if [ -z "$WORK_DIR" ]; then
  echo "Usage:   $0 -w [work_dir]"
  echo ""
  echo "Example: $0 -w ."
  echo ""
  echo "Params:"
  echo "  [work_dir]  The working directory to read .env file and execute scripts from."
  echo ""
  exit
fi

source $WORK_DIR/.env

DB_HOST=${DB_HOST:-127.0.0.1}
DB_PORT=${DB_PORT:-5432}
DB_USER=${DB_USER:-replicator}
DB_NAME=${DB_NAME:-replicator}
DB_PASSWORD=${DB_PASSWORD:-password} # psql requires PGPASSWORD to be set

# set -x
set -e
set -o pipefail

if hash psql 2>/dev/null; then
  echo "OK, you have psql in the path. We’ll use that."
  PSQL=psql
else
  echo "You don't have psql is the path. Let's try /usr/bin"
  hash /usr/bin/psql
  PSQL=/usr/bin/psql
fi

function log() {
  echo "`date` - $1"
}

log "Inserting into k3l_url_labels"
PGPASSWORD=$DB_PASSWORD \
$PSQL -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME \
  -f $WORK_DIR/frames/incremental_load_labels.sql 

wait $!

log "Inserting into k3l_cast_embed_url_mapping"
PGPASSWORD=$DB_PASSWORD \
$PSQL -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME \
  -f $WORK_DIR/frames/incremental_load_cast_mapping.sql

wait $!

this_name=`basename "$0"`
log "$this_name done!"