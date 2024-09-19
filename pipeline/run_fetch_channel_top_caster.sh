#!/bin/bash

while getopts w:i:v:c: flag
do
    case "${flag}" in
        w) WORK_DIR=${OPTARG};;
        v) VENV=${OPTARG};;
        c) CSV_PATH=${OPTARG};;
    esac
done

shift $((OPTIND-1))
CHANNEL_IDS="$1"

if [ -z "$VENV" ] || [ -z "$CSV_PATH" ]; then
  echo "Usage:   $0 -w [work_dir] -v [venv] -c [csv_path] [channel_ids]"
  echo ""
  echo "Example: $0 -w . -v /home/ubuntu/venvs/fc-graph-env3/ -c channels/Top_Channels.csv"
  echo ""
  echo "Params:"
  echo "  [work_dir]  The working directory to read .env file and execute scripts from."
  echo "  [venv] The path where a python3 virtualenv has been created."
  echo "  [csv_path] The path to the CSV file."
  echo ""
  exit 1
fi

log() {
  echo "`date` - $1"
}

log "Starting script with parameters: WORK_DIR=${WORK_DIR}, VENV=${VENV}, CSV_PATH=${CSV_PATH}"

source $WORK_DIR/.env

set -e
set -o pipefail

function log() {
  echo "`date` - $1"
}

log "Activating virtual environment"
source $VENV/bin/activate
pip install -r requirements.txt
log "Executing task"
python3 -m channels.main_fetch_channel_top_casters -c "$CSV_PATH"
deactivate

