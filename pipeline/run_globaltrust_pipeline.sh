#!/bin/bash

# Function to validate date format
function validate_date() {
    date_to_check=$1
    date_format='%Y-%m-%d'
    
    # Check if the date matches the format YYYY-mm-dd
    if ! date -d "$date_to_check" +"$date_format" >/dev/null 2>&1; then
        echo "Invalid date format. Use YYYY-mm-dd."
        exit 1
    fi

    # Check if the date is in the past
    today=$(date +%Y-%m-%d)
    if [ "$date_to_check" \> "$today" ] || [ "$date_to_check" == "$today" ]; then
        echo "The date must be in the past and not include today."
        exit 1
    fi
}

while getopts w:v:d: flag
do
    case "${flag}" in
        w) WORK_DIR=${OPTARG};;
        v) VENV=${OPTARG};;
        d) TARGET_DATE=${OPTARG};;
    esac
done

if [ -z "$WORK_DIR" ] || [ -z "$VENV" ]; then
  echo "Usage:   $0 -w [work_dir] -v [venv]"
  echo "Usage:   $0 -w [work_dir] -v [venv] -d [date]"
  echo ""
  echo "Example: $0 -w . -v /home/ubuntu/farcaster-graph/pipeline/.venv"
  echo "         $0 -w . -v /home/ubuntu/farcaster-graph/pipeline/.venv -d 2024-06-01"
  echo ""
  echo "Params:"
  echo "  [work_dir]  The working directory to read .env file and execute scripts from."
  echo "  [venv]      The path where a python3 virtualenv has been created."
  echo "  [date]      (optional) Target date to run the globaltrust and localtrust generation."
  echo ""
  exit
fi

OPT_DATE_SUFFIX=""
if [ ! -z "$TARGET_DATE" ]; then
  validate_date $TARGET_DATE
  FORMATTED_TARGET_DATE=$(date -d $TARGET_DATE +"%Y%m%d")
  OPT_DATE_SUFFIX="_$FORMATTED_TARGET_DATE"
  DATE_OPTION="--date $TARGET_DATE"
fi

source $WORK_DIR/.env

DB_HOST=${DB_HOST:-127.0.0.1}
DB_PORT=${DB_PORT:-5432}
DB_USER=${DB_USER:-replicator}
DB_NAME=${DB_NAME:-replicator}
DB_PASSWORD=${DB_PASSWORD:-password} # psql requires PGPASSWORD to be set
DB_TEMP_LOCALTRUST=${DB_TEMP_LOCALTRUST:-tmp_lt}
DB_LOCALTRUST=${DB_LOCALTRUST:-CHANGEME}
DB_TEMP_GLOBALTRUST=${DB_TEMP_GLOBALTRUST:-tmp_gt}
DB_GLOBALTRUST=${DB_GLOBALTRUST:-CHANGEME}

# set -x
set -e
set -o pipefail

if hash psql 2>/dev/null; then
  echo "OK, you have psql in the path. We’ll use that."
  PSQL=psql
else
  echo "You don't have psql in the path. Let's try /usr/bin"
  hash /usr/bin/psql
  PSQL=/usr/bin/psql
fi

function log() {
  echo "`date` - $1"
}

source $VENV/bin/activate
pip install -r requirements.txt
python3 -m globaltrust.gen_globaltrust $DATE_OPTION
deactivate

# We won't touch the localtrust table if we are running it based on a prior date
if [ -z "$TARGET_DATE" ]; then
  # NOTE: We could have replaced localtrust and upserted into globaltrust in python but ..
  # .. separating out like this helps us run steps in isolation.
  # For example, we can comment out the below code and ..
  # .. experiment with the python code (weights for example) without worrying about affecting prod.
  log "Replacing $DB_LOCALTRUST"
  PGPASSWORD=$DB_PASSWORD \
  $PSQL -e -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME \
    -c "DROP TABLE $DB_LOCALTRUST; ALTER TABLE $DB_TEMP_LOCALTRUST RENAME TO $DB_LOCALTRUST;"

  wait $!

  log "Inserting localtrust stats"
  PGPASSWORD=$DB_PASSWORD \
  $PSQL -t -A -F',' -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME \
    -f globaltrust/export_localtrust_daily_stats.sql

  wait $!
fi

log "Upserting $DB_GLOBALTRUST"
PGPASSWORD=$DB_PASSWORD \
$PSQL -e -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME \
  -c "DELETE FROM $DB_GLOBALTRUST WHERE date = (SELECT min(date) FROM ${DB_TEMP_GLOBALTRUST}${OPT_DATE_SUFFIX});"
INSERT INTO $DB_GLOBALTRUST SELECT * FROM ${DB_TEMP_GLOBALTRUST}${OPT_DATE_SUFFIX};
DROP TABLE IF EXISTS ${DB_TEMP_GLOBALTRUST}${OPT_DATE_SUFFIX};

wait $!

this_name=`basename "$0"`
log "$this_name done!"
