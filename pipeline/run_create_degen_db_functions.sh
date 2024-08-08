#!/bin/bash

set -x
set -e

while getopts v:t: flag
do
    case "${flag}" in
        v) VENV=${OPTARG};;
        t) TASK=${OPTARG};;
    esac
done

if [ -z "$VENV" ]; then
  echo "Usage:   $0 -v [venv]"
  echo ""
  echo "Example: $0 -v /home/ubuntu/venvs/fc-graph-env3/"
  echo ""
  echo "Params:"
  echo "  [venv] The path where a python3 virtualenv has been created."
  echo "  [task] The task to perform: 'extract' or 'insert_scores'."
  echo ""
  exit
fi

# set -x
set -e
set -o pipefail

source $VENV/bin/activate
pip install -r requirements.txt

echo "Executing task: $TASK"
if [ "$TASK" = "extract" ]; then
  python3 -m degen.create_degen_sql_functions
elif [ "$TASK" = "insert_scores" ]; then
  python3 -m degen.calculate_rank
else
  echo "Invalid task specified. Use 'extract' or 'insert_scores'."
  exit 1
fi
  deactivate
