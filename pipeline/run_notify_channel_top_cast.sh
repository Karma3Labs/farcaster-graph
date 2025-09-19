#!/bin/bash

while getopts "w:v:rd" flag
do
    case "${flag}" in
        w) WORK_DIR=${OPTARG};;
        v) VENV=${OPTARG};;
        r) RUN_FLAG="--run";;
        d) DRYRUN_FLAG="--dry-run";;
    esac
done

if [ -z "$WORK_DIR" ] || [ -z "$VENV" ] || [ -z "$RUN_FLAG" ]; then
  echo "Usage:   $0 -w [work_dir] -v [venv] -r -d"
  echo ""
  echo "Example: $0 -w . -v /home/ubuntu/venvs/fc-graph-env3/ -r"
  echo "Example: $0 -w . -v /home/ubuntu/venvs/fc-graph-env3/ -r -d"
  echo ""
  echo "Params:"
  echo "  [work_dir] The working directory to read .env file and execute scripts from."
  echo "  [venv] The path where a python3 virtualenv has been created."
  echo "  [run] Flag to run the script."
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
python3 -m channels.main_notify_channel_top_cast $RUN_FLAG $DRYRUN_FLAG
deactivate