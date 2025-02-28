#!/bin/bash

DT_FORMAT='%Y-%m-%d %H:%M:%S'

# Function to validate date format
function validate_date() {
    date_to_check="$1"
    date_format="$2"

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

while getopts dv:f:t:p:m: flag
do
    case "${flag}" in
        d) DAEMON_FLAG="--daemon";;
        v) VENV=${OPTARG};;
        f) FILL_TYPE=${OPTARG};;
        t) TARGET_DATE=${OPTARG};;
        m) TARGET_MONTH=${OPTARG};;
        p) POSTGRES=${OPTARG};;
    esac
done

if [ -z "$VENV" ]; then
  echo "Usage:   $0 -v [venv]  -p [postgres] -d -t [fill_type]"
  echo ""
  echo "Example: $0 -v /home/ubuntu/venvs/fc-graph-env3/"
  echo "Example: $0 -v /home/ubuntu/venvs/fc-graph-env3/  -p eigen8 -d -t backfill"
  echo ""
  echo "Params:"
  echo "  [venv] The path where a python3 virtualenv has been created."
  echo "  [postgres] 'eigen2' or 'eigen8'"
  echo "  [daemon] Run in daemon mode."
  echo "  [fill_type] Run in 'default' or 'backfill' or 'gapfill' mode."
  echo ""
  exit
fi

if [ ! -z "$POSTGRES" ]; then
  PG_OPTION="--postgres $POSTGRES"
fi

FILL_TYPE=${FILL_TYPE:-default}

if [ ! -z "$TARGET_DATE" ]; then
  validate_date "$TARGET_DATE" "$DT_FORMAT"
  DATE_OPTION=(--target-date "$TARGET_DATE")
fi

# validating TARGET_MONTH in bash is a bit of a pain
# ... let the python script validate it
if [ ! -z "$TARGET_MONTH" ]; then
  MONTH_OPTION="--target-month $TARGET_MONTH"
fi


# set -x
set -e
set -o pipefail

function log() {
  echo "`date` - $1"
}

source $VENV/bin/activate
# pip install -r requirements.txt
python3 -m casts.main $PG_OPTION $DAEMON_FLAG -f $FILL_TYPE "${DATE_OPTION[@]}" $MONTH_OPTION
deactivate

log "Done"