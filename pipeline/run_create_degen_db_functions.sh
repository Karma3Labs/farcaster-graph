#!/bin/bash

set -x
set -e

while getopts v: flag
do
    case "${flag}" in
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


source $VENV/bin/activate
pip install -r requirements.txt
python3 -m degen.create_degen_sql_functions
deactivate
