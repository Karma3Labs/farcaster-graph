#!/bin/bash

while getopts w:i:v:t:c:n: flag
do
    case "${flag}" in
        w) WORK_DIR=${OPTARG};;
        v) VENV=${OPTARG};;
        t) TASK=${OPTARG};;
        c) CSV_PATH=${OPTARG};;
        n) INTERVAL=${OPTARG};;
    esac
done

shift $((OPTIND-1))
CHANNEL_IDS="$1"

if [ -z "$WORK_DIR" ] || [ -z "$VENV" ] || [ -z "$TASK" ] || [ -z "$CSV_PATH" ] ; then
  echo "Usage:   $0 -w [work_dir] -v [venv] -t [task] -c [csv_path] -n [interval] [channel_ids]"
  echo ""
  echo "Example: $0 -w . -v /home/ubuntu/venvs/fc-graph-env3/ -t fetch -c channels/Top_Channels.csv "
  echo "         $0 -w . -v /home/ubuntu/venvs/fc-graph-env3/ -t process -c channels/Top_Channels.csv -n 90 openrank,lp"
  echo ""
  echo "Params:"
  echo "  [work_dir]  The working directory to read .env file and execute scripts from."
  echo "  [venv] The path where a python3 virtualenv has been created."
  echo "  [task] The task to perform: fetch or process."
  echo "  [csv_path] The path to the CSV file."
  echo "  [interval] Required parameter for process task indicating the number of days of channel interactions to process. 0 means process lifetime interactions."
  echo "  [channel_ids] Required parameter for process task indicating the channel IDs to process."
  echo ""
  exit 1
fi

if [ "$TASK" = "process" ]; then
  if [ -z "$INTERVAL" ] || [ -z "$CHANNEL_IDS" ]; then
    echo "Please specify both -n (interval) and (channel_ids) for the process task."
    exit 1
  fi
fi

log() {
  echo "`date` - $1"
}

log "Starting script with parameters: WORK_DIR=${WORK_DIR},\
  VENV=${VENV}, TASK=${TASK}, CSV_PATH=${CSV_PATH},\
  INTERVAL=${INTERVAL}, CHANNEL_IDS=${CHANNEL_IDS}"

source $WORK_DIR/.env

DB_HOST=${DB_HOST:-127.0.0.1}
DB_PORT=${DB_PORT:-5432}
DB_USER=${DB_USER:-replicator}
DB_NAME=${DB_NAME:-replicator}
DB_PASSWORD=${DB_PASSWORD:-password} # psql requires PGPASSWORD to be set
DB_CHANNEL_RANK_TABLE=k3l_channel_rank

set -e
set -o pipefail

if hash psql 2>/dev/null; then
  log "OK, you have psql in the path. We’ll use that."
  PSQL=psql
else
  log "You don't have psql in the path. Let's try /usr/bin"
  hash /usr/bin/psql
  PSQL=/usr/bin/psql
fi

log "Activating virtual environment"
source $VENV/bin/activate
pip install -r requirements.txt

log "Executing task: $TASK"
if [ "$TASK" = "fetch" ]; then
  python3 -m channels.main -c "$CSV_PATH" -t fetch
  deactivate
elif [ "$TASK" = "process" ]; then
  log "Received channel_ids: $CHANNEL_IDS"
  python3 -m channels.main -c "$CSV_PATH" -t process --interval "$INTERVAL" --channel_ids "$CHANNEL_IDS"
  deactivate
elif [ "$TASK" = "refresh" ]; then
  log "REFRESH MATERIALIZED VIEW CONCURRENTLY $DB_CHANNEL_RANK_TABLE"
  PGPASSWORD=$DB_PASSWORD \
  $PSQL -e -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME \
    -c "REFRESH MATERIALIZED VIEW CONCURRENTLY $DB_CHANNEL_RANK_TABLE;"

  log "VACUUM ANALYZE $DB_CHANNEL_RANK_TABLE"
  PGPASSWORD=$DB_PASSWORD \
  $PSQL -e -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME \
    -c "VACUUM ANALYZE $DB_CHANNEL_RANK_TABLE;"
else
  echo "Invalid task specified. Use 'fetch' or 'process' or 'cleanup'."
  exit 1
fi
