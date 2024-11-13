#!/bin/bash

while getopts w:i:v:t:c:n:d:o: flag
do
    case "${flag}" in
        w) WORK_DIR=${OPTARG};;
        v) VENV=${OPTARG};;
        t) TASK=${OPTARG};;
        c) CSV_PATH=${OPTARG};;
        d) DOMAIN_CSV=${OPTARG};;
        o) OUT_DIR=${OPTARG};;
    esac
done

shift $((OPTIND-1))
CHANNEL_IDS="$1"

if [ -z "$WORK_DIR" ] || [ -z "$VENV" ] || [ -z "$TASK" ] || [ -z "$CSV_PATH" ] || [ -z "$DOMAIN_CSV" ] ; then
  echo "Usage:   $0 -w [work_dir] -v [venv] -t [task] -c [csv_path] -d [domain_csv] -o [out_dir] [channel_ids] "
  echo ""
  echo "Example: $0 -w . -v /home/ubuntu/venvs/fc-graph-env3/ -t fetch_domains -c channels/Top_Channels.csv -d channels/Channel_Domain.csv"
  echo "         $0 -w . -v /home/ubuntu/venvs/fc-graph-env3/ -t gen_domain_files -c channels/Top_Channels.csv -d channels/Channel_Domain.csv -o /tmp/ openrank,lp"
  echo ""
  echo "Params:"
  echo "  [work_dir] The working directory to read .env file and execute scripts from."
  echo "  [venv] The path where a python3 virtualenv has been created."
  echo "  [task] The task to perform: fetch or process."
  echo "  [csv_path] The path to the CSV file."
  echo "  [channel_ids] Required parameter for process task indicating the channel IDs to process."
  echo "  [domain_csv] The path to the CSV file with channel domain mapping."
  echo "  [out_dir] The directory to write localtrust, pretrust and openrank configs to."
  echo ""
  exit 1
fi

if [ "$TASK" = "gen_domain_files" ]; then
  if [ -z "$OUT_DIR" ] || [ -z "$CHANNEL_IDS" ]; then
    echo "Please specify -o (outdir) and (channel_ids) for the gen_domain_files task."
    exit 1
  fi
fi

log() {
  echo "`date` - $1"
}

log "Starting script with parameters: WORK_DIR=${WORK_DIR},\
  VENV=${VENV}, TASK=${TASK}, CSV_PATH=${CSV_PATH},\
  CHANNEL_IDS=${CHANNEL_IDS}, DOMAIN_CSV=${DOMAIN_CSV},\
  OUT_DIR=${OUT_DIR}"

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
if [ "$TASK" = "fetch_domains" ]; then
  python3 -m channels.main_openrank -c "$CSV_PATH" --domain_mapping "$DOMAIN_CSV" -t fetch_domains
  deactivate
elif [ "$TASK" = "gen_domain_files" ]; then
  log "Received channel_ids: $CHANNEL_IDS"
  python3 -m channels.main_openrank -c "$CSV_PATH" -t gen_domain_files \
    --domain_mapping "$DOMAIN_CSV" --outdir "$OUT_DIR" --channel_ids "$CHANNEL_IDS"
  deactivate
else
  echo "Invalid task specified. Use 'fetch' or 'process' or 'cleanup'."
  exit 1
fi
