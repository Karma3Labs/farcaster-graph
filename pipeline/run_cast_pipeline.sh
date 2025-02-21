#!/bin/bash

while getopts dv:b flag
do
    case "${flag}" in
        d) DAEMON_FLAG="--daemon";;
        v) VENV=${OPTARG};;
        b) BACKFILL_FLAG="--backfill";;
    esac
done

if [ -z "$VENV" ]; then
  echo "Usage:   $0 -v [venv] -d -b"
  echo ""
  echo "Example: $0 -v /home/ubuntu/venvs/fc-graph-env3/"
  echo "Example: $0 -v /home/ubuntu/venvs/fc-graph-env3/ -d -b"
  echo ""
  echo "Params:"
  echo "  [venv] The path where a python3 virtualenv has been created."
  echo "  [daemon] Run in daemon mode."
  echo "  [backfill] Run in backfill mode."
  echo ""
  exit
fi

# set -x
set -e
set -o pipefail

function log() {
  echo "`date` - $1"
}

source $VENV/bin/activate
# pip install -r requirements.txt
python3 -m casts.main $DAEMON_FLAG $BACKFILL_FLAG
deactivate
