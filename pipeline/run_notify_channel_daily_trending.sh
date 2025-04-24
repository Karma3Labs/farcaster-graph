#!/bin/bash

while getopts "w:v:c:d" flag
do
    case "${flag}" in
        w) WORK_DIR=${OPTARG};;
        v) VENV=${OPTARG};;
        c) CSV_PATH=${OPTARG};;
        d) DRYRUN_FLAG="--dry-run";;
    esac
done

if [ -z "$WORK_DIR" ] || [ -z "$VENV" ] || [ -z "$CSV_PATH" ]; then
  echo "Usage:   $0 -w [work_dir] -v [venv] -c [csv_path]  -d"
  echo ""
  echo "Example: $0 -w . -v /home/ubuntu/venvs/fc-graph-env3/ -c channels/Trending_Channels.csv"
  echo "Example: $0 -w . -v /home/ubuntu/venvs/fc-graph-env3/ -c channels/Trending_Channels.csv -d"
  echo ""
  echo "Params:"
  echo "  [work_dir] The working directory to read .env file and execute scripts from."
  echo "  [venv] The path where a python3 virtualenv has been created."
  echo "  [csv_path] Path to CSV file."
  echo "  [dryrun] Flag to run the script in dry-run mode."
  echo ""
  exit
fi

source $WORK_DIR/.env

# set -x
set -e
set -o pipefail

function log() {
  echo "`date` - $1"
}

source $VENV/bin/activate
#pip install -r requirements.txt
python3 -m channels.main_notify_daily_trending -c "$CSV_PATH" $DRYRUN_FLAG
deactivate
