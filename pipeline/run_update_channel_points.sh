#!/bin/bash

while getopts w:v:t:p:g: flag
do
    case "${flag}" in
        w) WORK_DIR=${OPTARG};;
        v) VENV=${OPTARG};;
        t) TASK=${OPTARG};;
        p) POSTGRES=${OPTARG};;
        g) GAPFILL_DATE=${OPTARG};;
    esac
done

if [ -z "$WORK_DIR" ] || [ -z "$VENV" ] || [ -z "$TASK" ]; then
  echo "Usage:   $0 -w [work_dir] -v [venv] -t [task]"
  echo "Usage:   $0 -w [work_dir] -v [venv] -t [task] -p [postgres]"
  echo "Usage:   $0 -w [work_dir] -v [venv] -t gapfill -p [postgres] -g [gapfill_date] "
  echo ""
  echo "Example: $0 -w . -v /home/ubuntu/venvs/fc-graph-env3/ -t genesis"
  echo "Example: $0 -w . -v /home/ubuntu/venvs/fc-graph-env3/ -t compute"
  echo "Example: $0 -w . -v /home/ubuntu/venvs/fc-graph-env3/ -t update"
  echo "Example: $0 -w . -v /home/ubuntu/venvs/fc-graph-env3/ -t update -p eigen8 -g 2025-04-01"
  echo ""
  echo "Params:"
  echo "  [work_dir] The working directory to read .env file and execute scripts from."
  echo "  [venv] The path where a python3 virtualenv has been created."
  echo "  [task] The task to perform: daily or distrib."
  echo "  [postgres] The name of the postgres database to connect to."
  echo "  [gapfill_date] The date to use for gapfilling in YYYY-MM-DD format."
  echo ""
  exit
fi

if [ ! -z "$POSTGRES" ]; then
  PG_OPTION="--postgres $POSTGRES"
fi

if [ "$TASK" = "gapfill" ]; then
  if [ -z "$GAPFILL_DATE" ]; then
    echo "Please specify -g (gapfill_date) for the gapfill task."
    exit 1
  fi
fi

# validating TARGET_MONTH in bash is a bit of a pain
# ... let the python script validate it
if [ ! -z "$GAPFILL_DATE" ]; then
  GAPFILL_OPTION="--gapfill-date $GAPFILL_DATE"
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
python3 -m channels.main_points -t "$TASK" $PG_OPTION $GAPFILL_OPTION
deactivate
