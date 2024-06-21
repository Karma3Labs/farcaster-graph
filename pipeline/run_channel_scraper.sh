#!/bin/bash

while getopts w:i:v: flag
do
    case "${flag}" in
        w) WORK_DIR=${OPTARG};;
        v) VENV=${OPTARG};;
    esac
done

if [ -z "$VENV" ]; then
  echo "Usage:   $0 -w [work_dir] -v [venv]"
  echo ""
  echo "Example: $0 -w . -v /home/ubuntu/venvs/fc-graph-env3/"
  echo ""
  echo "Params:"
  echo "  [work_dir]  The working directory to read .env file and execute scripts from."
  echo "  [venv] The path where a python3 virtualenv has been created."
  echo ""
  exit
fi

source $WORK_DIR/.env

DB_HOST=${DB_HOST:-127.0.0.1}
DB_PORT=${DB_PORT:-5432}
DB_USER=${DB_USER:-replicator}
DB_NAME=${DB_NAME:-replicator}
DB_PASSWORD=${DB_PASSWORD:-password} # psql requires PGPASSWORD to be set
DB_CHANNEL_RANK_TABLE=k3l_channel_rank

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

source $VENV/bin/activate
pip install -r requirements.txt
python3 -m channels.main -c "channels/Top_Channels.csv"
deactivate

log "REFRESH MATERIALIZED VIEW CONCURRENTLY $DB_CHANNEL_RANK_TABLE"
PGPASSWORD=$DB_PASSWORD \
$PSQL -e -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME \
  -c "REFRESH MATERIALIZED VIEW CONCURRENTLY $DB_CHANNEL_RANK_TABLE;"

log "VACUUM ANALYZE $DB_CHANNEL_RANK_TABLE"
PGPASSWORD=$DB_PASSWORD \
$PSQL -e -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME \
  -c "VACUUM ANALYZE $DB_CHANNEL_RANK_TABLE;"
