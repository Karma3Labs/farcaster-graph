#!/bin/bash

while getopts w:v: flag
do
    case "${flag}" in
        w) WORK_DIR=${OPTARG};;
        v) VENV=${OPTARG};;
    esac
done

if [ -z "$WORK_DIR" ] || [ -z "$VENV" ]; then
  echo "Usage:   $0 -w [work_dir] -v [venv]"
  echo ""
  echo "Example: $0 -w . -v /home/ubuntu/venvs/fc-graph-env3/"
  echo ""
  echo "Params:"
  echo "  [work_dir] The working directory to read .env file and execute scripts from."
  echo "  [venv] The path where a python3 virtualenv has been created."
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
python3 -m channels.main_points --run
deactivate
