#!/bin/bash

while getopts w:v:t:m: flag
do
    case "${flag}" in
        w) WORK_DIR=${OPTARG};;
        v) VENV=${OPTARG};;
        t) TASK=${OPTARG};;
        m) MODE=${OPTARG};;
    esac
done

if [ -z "$WORK_DIR" ] || [ -z "$VENV" ] || [ -z "$TASK" ] || [ -z "$MODE" ]; then
  echo "Usage:   $0 -w [work_dir] -v [venv] -t [task] -m [mode]"
  echo ""
  echo "Example: $0 -w . -v /home/ubuntu/venvs/fc-graph-env3/ -t distrib -m weighted"
  echo ""
  echo "Params:"
  echo "  [work_dir] The working directory to read .env file and execute scripts from."
  echo "  [venv] The path where a python3 virtualenv has been created."
  echo "  [task] The task to perform: prep or distrib."
  echo "  [mode] The mode to use: weighted or log or logeps or sqrt or cbrt or reddit."
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
python3 -m channels.main_points -t "$TASK" -m "$MODE" 
deactivate
