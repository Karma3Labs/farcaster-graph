#!/bin/bash

# Function to validate date format
function validate_date() {
    date_to_check=$1
    date_format='%Y-%m-%d'

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

while getopts dv:f:t: flag
do
    case "${flag}" in
        d) DAEMON_FLAG="--daemon";;
        v) VENV=${OPTARG};;
        f) FILL_TYPE=${OPTARG};;
        t) TARGET_DATE=${OPTARG};;
    esac
done

if [ -z "$VENV" ]; then
  echo "Usage:   $0 -v [venv] -d -t [fill_type]"
  echo ""
  echo "Example: $0 -v /home/ubuntu/venvs/fc-graph-env3/"
  echo "Example: $0 -v /home/ubuntu/venvs/fc-graph-env3/ -d -t backfill"
  echo ""
  echo "Params:"
  echo "  [venv] The path where a python3 virtualenv has been created."
  echo "  [daemon] Run in daemon mode."
  echo "  [fill_type] Run in 'default' or 'backfill' or 'gapfill' mode."
  echo ""
  exit
fi

FILL_TYPE=${FILL_TYPE:-default}
OPT_DATE_SUFFIX=""
TARGET_DATE_SUFFIX=""
if [ ! -z "$TARGET_DATE" ]; then
  validate_date $TARGET_DATE
  if [[ $(uname) == "Darwin" ]]; then
    FORMATTED_TARGET_DATE=$(date -j -f %Y-%m-%d $TARGET_DATE +"%Y%m%d" )
  else
    FORMATTED_TARGET_DATE=$(date -d $TARGET_DATE +"%Y%m%d")
  fi
  OPT_DATE_SUFFIX="_$FORMATTED_TARGET_DATE"
  TARGET_DATE_SUFFIX="_$TARGET_DATE"
  DATE_OPTION="--target-date $TARGET_DATE"
fi

# set -x
set -e
set -o pipefail

function log() {
  echo "`date` - $1"
}

source $VENV/bin/activate
# pip install -r requirements.txt
python3 -m casts.main $DAEMON_FLAG -f $FILL_TYPE $DATE_OPTION
deactivate
