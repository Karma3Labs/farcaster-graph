#!/bin/bash

while getopts w:o:v: flag
do
    case "${flag}" in
        o) OUT_DIR=${OPTARG};;
        w) WORK_DIR=${OPTARG};;
        v) VENV=${OPTARG};;
    esac
done

if [ -z "$OUT_DIR" ] || [ -z "$WORK_DIR" ] || [ -z "$VENV" ]; then
  echo "Usage:   $0 -w [work_dir] -o [out_dir] -v [venv]"
  echo ""
  echo "Example: $0 -w . -o /tmp -v /home/ubuntu/venvs/fc-graph-env3/"
  echo ""
  echo "Params:"
  echo "  [work_dir]  The working directory to read .env file and execute scripts from."
  echo "  [out_dir] The output directory to write the graph file."
  echo "  [venv] The path where a python3 virtualenv has been created."
  echo ""
  exit
fi

# set -x
set -e
set -o pipefail

source $VENV/bin/activate
pip install -r requirements.txt
python3 -m globaltrust.gen_globaltrust
deactivate