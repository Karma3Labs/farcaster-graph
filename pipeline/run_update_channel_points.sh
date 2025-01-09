#!/bin/bash

while getopts w:v:t: flag
do
    case "${flag}" in
        w) WORK_DIR=${OPTARG};;
        v) VENV=${OPTARG};;
        t) TASK=${OPTARG};;
    esac
done

if [ -z "$WORK_DIR" ] || [ -z "$VENV" ] || [ -z "$TASK" ]; then
  echo "Usage:   $0 -w [work_dir] -v [venv] -t [task]"
  echo ""
  echo "Example: $0 -w . -v /home/ubuntu/venvs/fc-graph-env3/ -t genesis"
  echo "Example: $0 -w . -v /home/ubuntu/venvs/fc-graph-env3/ -t compute"
  echo "Example: $0 -w . -v /home/ubuntu/venvs/fc-graph-env3/ -t update"
  echo ""
  echo "Params:"
  echo "  [work_dir] The working directory to read .env file and execute scripts from."
  echo "  [venv] The path where a python3 virtualenv has been created."
  echo "  [task] The task to perform: daily or distrib."
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
python3 -m channels.main_points -t "$TASK"
deactivate
