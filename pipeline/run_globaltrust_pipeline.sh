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

while getopts w:v:o:d: flag
do
    case "${flag}" in
        w) WORK_DIR=${OPTARG};;
        v) VENV=${OPTARG};;
        o) OUT_DIR=${OPTARG};;
        d) TARGET_DATE=${OPTARG};;
    esac
done

if [ -z "$WORK_DIR" ] || [ -z "$VENV" ]  || [ -z "$OUT_DIR" ]; then
  echo "Usage:   $0 -w [work_dir] -v [venv] -o [out_dir]"
  echo "Usage:   $0 -w [work_dir] -v [venv] -o [out_dir] -d [date]"
  echo ""
  echo "Example: $0 -w . -v /home/ubuntu/farcaster-graph/pipeline/.venv -o /tmp"
  echo "         $0 -w . -v /home/ubuntu/farcaster-graph/pipeline/.venv -o /tmp -d 2024-06-01"
  echo ""
  echo "Params:"
  echo "  [work_dir]  The working directory to read .env file and execute scripts from."
  echo "  [venv]      The path where a python3 virtualenv has been created."
  echo "  [date]      (optional) Target date to run the globaltrust and localtrust generation."
  echo ""
  exit
fi

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
  DATE_OPTION="--date $TARGET_DATE"
fi

source $WORK_DIR/.env

REMOTE_DB_HOST=${REMOTE_DB_HOST:-127.0.0.1}
REMOTE_DB_PORT=${REMOTE_DB_PORT:-5432}
REMOTE_DB_USER=${REMOTE_DB_USER:-replicator}
REMOTE_DB_NAME=${REMOTE_DB_NAME:-replicator}
REMOTE_DB_PASSWORD=${REMOTE_DB_PASSWORD:-password} # psql requires PGPASSWORD to be set

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

log $OPT_DATE_SUFFIX
log $TARGET_DATE_SUFFIX

# source $VENV/bin/activate
# pip install -r requirements.txt
# python3 -m globaltrust.gen_globaltrust -o $OUT_DIR $DATE_OPTION
# deactivate

log "Inserting localtrust_stats"
PGPASSWORD=$REMOTE_DB_PASSWORD \
$PSQL -e -h $REMOTE_DB_HOST -p $REMOTE_DB_PORT -U $REMOTE_DB_USER -d $REMOTE_DB_NAME \
  -c  "COPY localtrust_stats
  (date,strategy_id_3_row_count,strategy_id_3_mean,strategy_id_3_stddev,strategy_id_3_range) 
  FROM STDIN WITH (FORMAT CSV, HEADER);" < /tmp/localtrust_stats.engagement${TARGET_DATE_SUFFIX}.csv

PGPASSWORD=$REMOTE_DB_PASSWORD \
$PSQL -e -h $REMOTE_DB_HOST -p $REMOTE_DB_PORT -U $REMOTE_DB_USER -d $REMOTE_DB_NAME \
  -c  "COPY localtrust_stats
  (date,strategy_id_1_row_count,strategy_id_1_mean,strategy_id_1_stddev,strategy_id_1_range) 
  FROM STDIN WITH (FORMAT CSV, HEADER);" < /tmp/localtrust_stats.follows${TARGET_DATE_SUFFIX}.csv

log "Inserting globaltrust"
PGPASSWORD=$REMOTE_DB_PASSWORD \
$PSQL -e -h $REMOTE_DB_HOST -p $REMOTE_DB_PORT -U $REMOTE_DB_USER -d $REMOTE_DB_NAME \
  -c "DROP TABLE IF EXISTS tmp_globaltrust${OPT_DATE_SUFFIX}; 
  CREATE UNLOGGED TABLE tmp_globaltrust${OPT_DATE_SUFFIX} AS SELECT * FROM globaltrust LIMIT 0;"

PGPASSWORD=$REMOTE_DB_PASSWORD \
$PSQL -e -h $REMOTE_DB_HOST -p $REMOTE_DB_PORT -U $REMOTE_DB_USER -d $REMOTE_DB_NAME \
  -c  "COPY tmp_globaltrust${OPT_DATE_SUFFIX}
  (i,v,date,strategy_id) 
  FROM STDIN WITH (FORMAT CSV, HEADER);" < /tmp/globaltrust.engagement${TARGET_DATE_SUFFIX}.csv

PGPASSWORD=$REMOTE_DB_PASSWORD \
$PSQL -e -h $REMOTE_DB_HOST -p $REMOTE_DB_PORT -U $REMOTE_DB_USER -d $REMOTE_DB_NAME \
  -c  "COPY tmp_globaltrust${OPT_DATE_SUFFIX}
  (i,v,date,strategy_id) 
  FROM STDIN WITH (FORMAT CSV, HEADER);" < /tmp/globaltrust.follows${TARGET_DATE_SUFFIX}.csv

PGPASSWORD=$REMOTE_DB_PASSWORD \
$PSQL -e -h $REMOTE_DB_HOST -p $REMOTE_DB_PORT -U $REMOTE_DB_USER -d $REMOTE_DB_NAME \
  -c "DELETE FROM globaltrust WHERE date = (SELECT min(date) FROM tmp_globaltrust${OPT_DATE_SUFFIX});
INSERT INTO globaltrust SELECT * FROM tmp_globaltrust${OPT_DATE_SUFFIX};"

wait $!

this_name=`basename "$0"`
log "$this_name done!"
