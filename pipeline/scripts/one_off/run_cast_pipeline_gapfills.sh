#!/bin/bash

date_format='%Y-%m-%d'

# Function to validate date format
function validate_date() {
    date_to_check=$1

    # Check if the date matches the format YYYY-mm-dd
    if [[ $(uname) == "Darwin" ]]; then
      if ! date -j -f "$date_format" "$date_to_check" >/dev/null 2>&1; then
        echo "Invalid date format. Use YYYY-mm-dd."
        exit 1
      fi
    else
      if ! date -d "$date_to_check" +"$date_format" >/dev/null 2>&1; then
        echo "Invalid date format. Use YYYY-mm-dd."
        exit 1
      fi
    fi

    # Check if the date is in the past
    today=$(date +"$date_format")
    if [ "$date_to_check" \> "$today" ] || [ "$date_to_check" == "$today" ]; then
      echo "The date must be in the past and not include today."
      exit 1
    fi
}

while getopts v:s:p:e:l: flag
do
    case "${flag}" in
        v) VENV=${OPTARG};;
        s) START_DATE=${OPTARG};;
        e) END_DATE=${OPTARG};;
        p) POSTGRES=${OPTARG};;
        l) SLEEP_TIME=${OPTARG};;
    esac
done

if [ -z "$VENV" ] || [ -z "$START_DATE" ] || [ -z "$END_DATE" ]; then
  echo "Usage:   $0 -v [venv] -s [start_date] -e [end_date]"
  echo "Usage:   $0 -v [venv] -s [start_date] -e [end_date] -p [postgres] -l [sleep_time]"
  echo ""
  echo "Example: $0 -v /home/ubuntu/venvs/fc-graph-env3/ -s 2025-02-01 -e 2025-02-05"
  echo "Example: $0 -v /home/ubuntu/venvs/fc-graph-env3/ -s 2025-02-01 -e 2025-02-05 -p eigen8"
  echo ""
  echo "Params:"
  echo "  [venv] The path where a python3 virtualenv has been created."
  echo "  [start_date] The date to start the gapfilling process."
  echo "  [end_date] The date to end the gapfilling process."
  echo "  [postgres] 'eigen2' or 'eigen8'"
  echo "  [sleep_time] The amount of time to sleep between gapfill runs."
  echo ""
  exit
fi

if [ ! -z "$POSTGRES" ]; then
  PG_OPTION="--postgres $POSTGRES"
fi

validate_date $START_DATE
validate_date $END_DATE

SLEEP_TIME=${SLEEP_TIME:-30s}


# set -x
set -e
set -o pipefail

function log() {
  echo "`date` - $1"
}

source $VENV/bin/activate
# pip install -r requirements.txt
while [[ $START_DATE < $END_DATE ]]; do
  DATE_OPTION=(--target-date "$START_DATE 00:00:00")
  FILL_TYPE="gapfill"
  DAEMON_FLAG=""
  log "Running gapfill for $START_DATE"
  # python3 -m casts.main $PG_OPTION $DAEMON_FLAG -f $FILL_TYPE "${DATE_OPTION[@]}"
  log "Sleeping for $SLEEP_TIME"
  sleep $SLEEP_TIME
  START_DATE=$(date -I -d "$START_DATE + 1 day")
done
deactivate
