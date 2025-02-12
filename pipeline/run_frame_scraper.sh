#!/bin/bash

while getopts d:v: flag
do
    case "${flag}" in
        d) DAEMON=${OPTARG};;
        v) VENV=${OPTARG};;
    esac
done

if [ -z "$VENV" ]; then
  echo "Usage:   $0 -v [venv]"
  echo ""
  echo "Example: $0 -v /home/ubuntu/venvs/fc-graph-env3/"
  echo ""
  echo "Params:"
  echo "  [venv] The path where a python3 virtualenv has been created."
  echo ""
  exit
fi

# set -x
set -e
set -o pipefail

function log() {
  echo "`date` - $1"
}

DAEMON=${DAEMON:-false}

source $VENV/bin/activate
# pip install -r requirements.txt
tldextract --update
python3 -m frames.main -d $DAEMON
deactivate
