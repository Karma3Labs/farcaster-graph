#!/bin/bash

PATH=$PATH:tmp/bin

while getopts w:v:t:s:c:o:p:b: flag
do
    case "${flag}" in
        w) WORK_DIR=${OPTARG};;
        v) VENV=${OPTARG};;
        t) TASK=${OPTARG};;
        s) SEED_CSV=${OPTARG};;
        c) CATEGORY=${OPTARG};;
        o) OUT_DIR=${OPTARG};;
        b) BOTS_CSV=${OPTARG};;
    esac
done

shift $((OPTIND-1))

if [ -z "$WORK_DIR" ] || [ -z "$VENV" ] || [ -z "$TASK" ] || [ -z "$CATEGORY" ]; then
  echo "Usage:   $0 -w [work_dir] -v [venv] -t [task] -s [seed_csv] -c [category] -o [out_dir] "
  echo ""
  echo "Example: $0 -w . -v .venv -t fetch_category -s channels/Top_Channels.csv -c test"
  echo "         $0 -w . -v .venv -t gen_category_files -s channels/Top_Channels.csv -c test -o /tmp/"
  echo "         $0 -w . -v .venv -t gen_category_files -s channels/Top_Channels.csv -c test -o /tmp/"
  echo "         $0 -w . -v .venv -t process_category -c test -o /tmp/ openrank,music"
  echo "         $0 -w . -v .venv -t fetch_results -o /tmp/ "
  echo ""
  echo "Params:"
  echo "  [work_dir] The working directory to read .env file and execute scripts from."
  echo "  [venv] The path where a python3 virtualenv has been created."
  echo "  [task] The task to perform: fetch_category or gen_category_files."
  echo "  [seed_csv] The path to the Seed CSV file."
  echo "  [category] Choice of 'test' or 'prod'."
  echo "  [out_dir] The directory to write localtrust, pretrust and openrank configs to."
  echo ""
  exit 1
fi

if [ "$TASK" = "gen_category_files" ] || [ "$TASK" = "process_category" ]; then
  if [ -z "$OUT_DIR" ]; then
    echo "Please specify -o (outdir) for the gen_category_files and process_category task."
    exit 1
  fi
fi

if [ "$TASK" = "gen_category_files" ]; then
  if [ -z "$SEED_CSV" ]; then
    echo "Please specify -s (seed_csv) for the gen_category_files task."
    exit 1
  fi
fi

log() {
  echo "`date` - $1"
}

log "Starting script with parameters: WORK_DIR=${WORK_DIR},\
  VENV=${VENV}, TASK=${TASK}, SEED_CSV=${SEED_CSV},\
  CATEGORY=${CATEGORY},OUT_DIR=${OUT_DIR}"

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
if [ "$ver" -lt "19" ]; then
    echo "openrank-sdk version must be 0.1.9 or greater"
    exit 1
fi

log "Activating virtual environment"
source $VENV/bin/activate
# pip install -r requirements.txt

log "Executing task: $TASK"
if [ "$TASK" = "gen_category_files" ]; then
  python3 -m channels.main_openrank -s "$SEED_CSV" -t gen_category_files \
    --category "$CATEGORY" --outdir "$OUT_DIR" \
    -b "$BOTS_CSV"
  deactivate
elif [ "$TASK" = "process_category" ]; then
  python3 -m channels.main_openrank -t process_category \
    --category "$CATEGORY" --outdir "$OUT_DIR"
  deactivate
elif [ "$TASK" = "fetch_results" ]; then
  python3 -m channels.main_openrank -t fetch_results \
    --category "$CATEGORY" --outdir "$OUT_DIR"
  deactivate
else
  echo "Invalid task specified. Use 'fetch' or 'process' or 'cleanup'."
  exit 1
fi
