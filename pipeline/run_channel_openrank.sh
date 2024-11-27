#!/bin/bash

PATH=$PATH:tmp/bin

while getopts w:i:v:t:s:n:d:o:p: flag
do
    case "${flag}" in
        w) WORK_DIR=${OPTARG};;
        v) VENV=${OPTARG};;
        t) TASK=${OPTARG};;
        s) SEED_CSV=${OPTARG};;
        d) DOMAIN_CSV=${OPTARG};;
        o) OUT_DIR=${OPTARG};;
        p) PREV_DIR=${OPTARG};;
    esac
done

shift $((OPTIND-1))
CHANNEL_IDS="$1"

if [ -z "$WORK_DIR" ] || [ -z "$VENV" ] || [ -z "$TASK" ]; then
  echo "Usage:   $0 -w [work_dir] -v [venv] -t [task] -s [seed_csv] -d [domain_csv] -o [out_dir] -p [prev_dir] [channel_ids] "
  echo ""
  echo "Example: $0 -w . -v .venv -t fetch_domains -s channels/Top_Channels.csv -d channels/Channel_Domain.csv"
  echo "         $0 -w . -v .venv -t gen_domain_files -s channels/Top_Channels.csv -d channels/Channel_Domain.csv -o /tmp/ -p /tmp/prev_run/ openrank,music"
  echo "         $0 -w . -v .venv -t gen_domain_files -s channels/Top_Channels.csv -d channels/Channel_Domain.csv -o /tmp/ -p /tmp/prev/ openrank,music"
  echo "         $0 -w . -v .venv -t process_domains -d channels/Channel_Domain.csv -o /tmp/ openrank,music"
  echo "         $0 -w . -v .venv -t fetch_results -o /tmp/ "
  echo ""
  echo "Params:"
  echo "  [work_dir] The working directory to read .env file and execute scripts from."
  echo "  [venv] The path where a python3 virtualenv has been created." 
  echo "  [task] The task to perform: fetch_domains or gen_domain_files."
  echo "  [seed_csv] The path to the Seed CSV file."
  echo "  [domain_csv] The path to the CSV file with channel domain mapping."
  echo "  [out_dir] The directory to write localtrust, pretrust and openrank configs to."
  echo "  [prev_dir] The directory to read localtrust and pretrust of the previous run."
  echo "  [channel_ids] Required parameter for gen_domain_files task indicating the channel IDs to process."
  echo ""
  exit 1
fi

if [ "$TASK" = "gen_domain_files" ] || [ "$TASK" = "process_domains" ]; then
  if [ -z "$OUT_DIR" ] || [ -z "$CHANNEL_IDS" ] || [ -z "$DOMAIN_CSV" ]; then
    echo "Please specify -d (domain_csv), -o (outdir) and (channel_ids) for the gen_domain_files and process_domains task."
    exit 1
  fi
fi

if [ "$TASK" = "gen_domain_files" ]; then
  if [ -z "$SEED_CSV" ]; then
    echo "Please specify -s (seed_csv) for the gen_domain_files task."
    exit 1
  fi
fi

if [ ! -z "$PREV_DIR" ]; then
  PREV_DIR_OPTION="--prevdir $PREV_DIR"
fi

log() {
  echo "`date` - $1"
}

log "Starting script with parameters: WORK_DIR=${WORK_DIR},\
  VENV=${VENV}, TASK=${TASK}, SEED_CSV=${SEED_CSV},\
  CHANNEL_IDS=${CHANNEL_IDS}, DOMAIN_CSV=${DOMAIN_CSV},\
  OUT_DIR=${OUT_DIR}, PREV_DIR_OPTION=${PREV_DIR_OPTION}"

source $WORK_DIR/.env

DB_HOST=${DB_HOST:-127.0.0.1}
DB_PORT=${DB_PORT:-5432}
DB_USER=${DB_USER:-replicator}
DB_NAME=${DB_NAME:-replicator}
DB_PASSWORD=${DB_PASSWORD:-password} # psql requires PGPASSWORD to be set

# uncomment for debugging
# set -x
set -e
set -o pipefail

if command -v psql 2>/dev/null; then
  log "OK, you have psql in the path. We’ll use that."
  PSQL=psql
else
  log "You don't have psql in the path. Let's try /usr/bin"
  command -v /usr/bin/psql
  PSQL=/usr/bin/psql
fi

if command -v openrank-sdk 2>/dev/null; then
  log "Found openrank-sdk in the path."
else
  log "You don't have openrank-sdk installed."
  exit 1
fi

ver=$(openrank-sdk --version 2>&1 | sed 's/openrank-sdk 0.\([0-9]\).\([0-9]\)/\1\2/')
if [ "$ver" -lt "14" ]; then
    echo "openrank-sdk version must be 0.1.4 or greater"
    exit 1
fi

log "Activating virtual environment"
source $VENV/bin/activate
# pip install -r requirements.txt

log "Executing task: $TASK"
if [ "$TASK" = "fetch_domains" ]; then
  python3 -m channels.main_openrank -s "$SEED_CSV" --domain_mapping "$DOMAIN_CSV" -t fetch_domains
  deactivate
elif [ "$TASK" = "gen_domain_files" ]; then
  log "Received channel_ids: $CHANNEL_IDS"
  python3 -m channels.main_openrank -s "$SEED_CSV" -t gen_domain_files \
    --domain_mapping "$DOMAIN_CSV" --outdir "$OUT_DIR" $PREV_DIR_OPTION \
    --channel_ids "$CHANNEL_IDS"
  deactivate
elif [ "$TASK" = "process_domains" ]; then
  log "Received channel_ids: $CHANNEL_IDS"
  python3 -m channels.main_openrank -t process_domains \
    --domain_mapping "$DOMAIN_CSV" --outdir "$OUT_DIR" \
    --channel_ids "$CHANNEL_IDS"
  deactivate
elif [ "$TASK" = "fetch_results" ]; then
  python3 -m channels.main_openrank -t fetch_results \
    --outdir "$OUT_DIR" 
  deactivate
else
  echo "Invalid task specified. Use 'fetch' or 'process' or 'cleanup'."
  exit 1
fi
