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

while getopts s:w:v:t:o:d:r: flag
do
    case "${flag}" in
        s) STEP=${OPTARG};;
        w) WORK_DIR=${OPTARG};;
        v) VENV=${OPTARG};;
        t) TEMP_DIR=${OPTARG};;
        o) OUT_DIR=${OPTARG};;
        d) TARGET_DATE=${OPTARG};;
        r) VERSION=${OPTARG};;
    esac
done

if [ -z "$STEP" ] || [ -z "$WORK_DIR" ] || [ -z "$VENV" ]  || [ -z "$OUT_DIR" ]  || [ -z "$TEMP_DIR" ]; then
  echo "Usage:   $0 -s [step] -w [work_dir] -v [venv] -o [out_dir] -t [temp_dir]"
  echo "Usage:   $0 -s [step] -w [work_dir] -v [venv] -o [out_dir] -t [temp_dir] -d [date]"
  echo "Usage:   $0 -s [step] -w [work_dir] -v [venv] -o [out_dir] -t [temp_dir] -d [date] -r [version]"
  echo ""
  echo "Example: $0 -s prep -w . -v /home/ubuntu/farcaster-graph/pipeline/.venv -o ~/graph_files -t /tmp"
  echo "         $0 -s compute -w . -v /home/ubuntu/farcaster-graph/pipeline/.venv -o ~/graph_files -t /tmp -d 2024-06-01"
  echo "         $0 -s graph -w . -v /home/ubuntu/farcaster-graph/pipeline/.venv -o ~/graph_files -t /tmp -d 2024-06-01 -r 1"
  echo ""
  echo "Params:"
  echo "  [step]  localtrust or compute"
  echo "  [work_dir]  The working directory to read .env file and execute scripts from."
  echo "  [temp_dir]  The temporary directory where csv files are to be written to."
  echo "  [out_dir]  The final destination directory to write localtrust files to."
  echo "  [venv]      The path where a python3 virtualenv has been created."
  echo "  [date]      (optional) Target date to run the globaltrust and localtrust generation."
  echo "  [version]   (optional) Version of the globaltrust computation. Default is 1."
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

# Set default version if not provided
VERSION=${VERSION:-1}
VERSION_OPTION="--version $VERSION"

source $WORK_DIR/.env

ALT_REMOTE_DB_HOST=${ALT_REMOTE_DB_HOST:-127.0.0.1}
ALT_REMOTE_DB_PORT=${ALT_REMOTE_DB_PORT:-5432}
ALT_REMOTE_DB_USER=${ALT_REMOTE_DB_USER:-k3l_user}
ALT_REMOTE_DB_NAME=${ALT_REMOTE_DB_NAME:-farcaster}
ALT_REMOTE_DB_PASSWORD=${ALT_REMOTE_DB_PASSWORD:-password} # psql requires PGPASSWORD to be set

# set -x
set -e
set -o pipefail

function log() {
  echo "`date` - $1"
}

log "DATE_OPTION: $OPT_DATE_SUFFIX"
log "TARGET_DATE: $TARGET_DATE_SUFFIX"
log "VERSION: $VERSION"
log "TEMP_DIR: $TEMP_DIR"
log "OUT_DIR: $OUT_DIR"

log "ALT_REMOTE_DB_HOST: $ALT_REMOTE_DB_HOST"
log "ALT_REMOTE_DB_PORT: $ALT_REMOTE_DB_PORT"
log "ALT_REMOTE_DB_USER: $ALT_REMOTE_DB_USER"
log "ALT_REMOTE_DB_NAME: $ALT_REMOTE_DB_NAME"


echo "Executing step: $STEP"
if [ "$STEP" = "graph" ]; then

  source $VENV/bin/activate
  #pip install -r requirements.txt
  python3 -m globaltrust.gen_globaltrust -s $STEP -o $OUT_DIR $VERSION_OPTION
  deactivate

elif [ "$STEP" = "prep" ]; then

  source $VENV/bin/activate
  #pip install -r requirements.txt
  python3 -m globaltrust.gen_globaltrust -s $STEP -o $TEMP_DIR $DATE_OPTION $VERSION_OPTION
  deactivate

elif [ "$STEP" = "compute_following" ]; then
  source $VENV/bin/activate
  #pip install -r requirements.txt

  #### START Globaltrust for FOLLOWING strategy
  # copy pretrust to go_eigentrust_bind_src so that go-eigentrust can read from filesystem instead of rest api
  cp  ${TEMP_DIR}/pretrust.following${TARGET_DATE_SUFFIX}.csv ${GO_EIGENTRUST_BIND_SRC}/go_pretrust.csv

  # copy localtrust to go_eigentrust_bind_src so that go-eigentrust can read from filesystem instead of rest api
  # localtrust has i,j,v,date,strategy_id for downstream processing but
  # go-eigentrust requires only i,j,v
  cut -d',' -f1,2,3 \
  ${TEMP_DIR}/localtrust.following${TARGET_DATE_SUFFIX}.csv > ${GO_EIGENTRUST_BIND_SRC}/go_localtrust.csv
  # run compute
  python3 -m globaltrust.gen_globaltrust -s compute_following \
    -p ${GO_EIGENTRUST_BIND_TARGET}/go_pretrust.csv \
    -l ${GO_EIGENTRUST_BIND_TARGET}/go_localtrust.csv \
    -o $TEMP_DIR \
    $DATE_OPTION \
    $VERSION_OPTION
  #### END Globaltrust for FOLLOWING strategy

  deactivate

elif [ "$STEP" = "compute_engagement" ]; then
  source $VENV/bin/activate
  #pip install -r requirements.txt

  #### START Globaltrust for ENGAGEMENT strategy
  # copy pretrust to go_eigentrust_bind_src so that go-eigentrust can read from filesystem instead of rest api
  cp  ${TEMP_DIR}/pretrust.engagement${TARGET_DATE_SUFFIX}.csv ${GO_EIGENTRUST_BIND_SRC}/go_pretrust.csv

  # copy localtrust to go_eigentrust_bind_src so that go-eigentrust can read from filesystem instead of rest api
  # localtrust has i,j,v,date,strategy_id for downstream processing but
  # go-eigentrust requires only i,j,v
  cut -d',' -f1,2,3 \
  ${TEMP_DIR}/localtrust.engagement${TARGET_DATE_SUFFIX}.csv > ${GO_EIGENTRUST_BIND_SRC}/go_localtrust.csv
  # run compute
  python3 -m globaltrust.gen_globaltrust -s compute_engagement \
    -p ${GO_EIGENTRUST_BIND_TARGET}/go_pretrust.csv \
    -l ${GO_EIGENTRUST_BIND_TARGET}/go_localtrust.csv \
    -o $TEMP_DIR \
    $DATE_OPTION \
    $VERSION_OPTION
  #### END Globaltrust for ENGAGEMENT strategy

  deactivate

elif [ "$STEP" = "compute_v3engagement" ]; then
  source $VENV/bin/activate
  #pip install -r requirements.txt

  #### START Globaltrust for V3_ENGAGEMENT strategy
  # copy pretrust to go_eigentrust_bind_src so that go-eigentrust can read from filesystem instead of rest api
  cp  ${TEMP_DIR}/pretrust.v3engagement${TARGET_DATE_SUFFIX}.csv ${GO_EIGENTRUST_BIND_SRC}/go_pretrust.csv

  # copy localtrust to go_eigentrust_bind_src so that go-eigentrust can read from filesystem instead of rest api
  # localtrust has i,j,v,date,strategy_id for downstream processing but
  # go-eigentrust requires only i,j,v
  cut -d',' -f1,2,3 \
  ${TEMP_DIR}/localtrust.v3engagement${TARGET_DATE_SUFFIX}.csv > ${GO_EIGENTRUST_BIND_SRC}/go_localtrust.csv
  # run compute
  python3 -m globaltrust.gen_globaltrust -s compute_v3engagement \
    -p ${GO_EIGENTRUST_BIND_TARGET}/go_pretrust.csv \
    -l ${GO_EIGENTRUST_BIND_TARGET}/go_localtrust.csv \
    -o $TEMP_DIR \
    $DATE_OPTION \
    $VERSION_OPTION
  #### END Globaltrust for V3_ENGAGEMENT strategy

  deactivate

elif [ "$STEP" = "insert_db" ]; then

  if hash psql 2>/dev/null; then
    echo "OK, you have psql in the path. We’ll use that."
    PSQL=psql
  else
    echo "You don't have psql in the path. Let's try /usr/bin"
    hash /usr/bin/psql
    PSQL=/usr/bin/psql
  fi

  # Eigen8 create temp table for globaltrust csv import
  log "Inserting tmp_globaltrust_v2${OPT_DATE_SUFFIX}"
  PGPASSWORD=$ALT_REMOTE_DB_PASSWORD \
  $PSQL -e -h $ALT_REMOTE_DB_HOST -p $ALT_REMOTE_DB_PORT -U $ALT_REMOTE_DB_USER -d $ALT_REMOTE_DB_NAME \
    -c "DROP TABLE IF EXISTS tmp_globaltrust_v2${OPT_DATE_SUFFIX};
    CREATE UNLOGGED TABLE tmp_globaltrust_v2${OPT_DATE_SUFFIX} AS SELECT * FROM globaltrust LIMIT 0;"

  if [ -f "${TEMP_DIR}/globaltrust.following${TARGET_DATE_SUFFIX}.csv" ]; then
    # Eigen8 import FOLLOWING globaltrust csv into temp table
    PGPASSWORD=$ALT_REMOTE_DB_PASSWORD \
    $PSQL -e -h $ALT_REMOTE_DB_HOST -p $ALT_REMOTE_DB_PORT -U $ALT_REMOTE_DB_USER -d $ALT_REMOTE_DB_NAME \
      -c  "COPY tmp_globaltrust_v2${OPT_DATE_SUFFIX}
      (i,v,date,strategy_id)
      FROM STDIN WITH (FORMAT CSV, HEADER);" < ${TEMP_DIR}/globaltrust.following${TARGET_DATE_SUFFIX}.csv
  fi

  if [ -f "${TEMP_DIR}/globaltrust.engagement${TARGET_DATE_SUFFIX}.csv" ]; then
    # Eigen8 import ENGAGEMENT globaltrust csv into temp table
    PGPASSWORD=$ALT_REMOTE_DB_PASSWORD \
    $PSQL -e -h $ALT_REMOTE_DB_HOST -p $ALT_REMOTE_DB_PORT -U $ALT_REMOTE_DB_USER -d $ALT_REMOTE_DB_NAME \
      -c  "COPY tmp_globaltrust_v2${OPT_DATE_SUFFIX}
      (i,v,date,strategy_id)
      FROM STDIN WITH (FORMAT CSV, HEADER);" < ${TEMP_DIR}/globaltrust.engagement${TARGET_DATE_SUFFIX}.csv
  fi

  if [ -f "${TEMP_DIR}/globaltrust.v3engagement${TARGET_DATE_SUFFIX}.csv" ]; then
    # Eigen8 import V3_ENGAGEMENT globaltrust csv into temp table
    PGPASSWORD=$ALT_REMOTE_DB_PASSWORD \
    $PSQL -e -h $ALT_REMOTE_DB_HOST -p $ALT_REMOTE_DB_PORT -U $ALT_REMOTE_DB_USER -d $ALT_REMOTE_DB_NAME \
      -c  "COPY tmp_globaltrust_v2${OPT_DATE_SUFFIX}
      (i,v,date,strategy_id)
      FROM STDIN WITH (FORMAT CSV, HEADER);" < ${TEMP_DIR}/globaltrust.v3engagement${TARGET_DATE_SUFFIX}.csv
  fi

  # Eigen8 copy globaltrust from temp table into main table
  log "Inserting globaltrust"
  PGPASSWORD=$ALT_REMOTE_DB_PASSWORD \
  $PSQL -e -h $ALT_REMOTE_DB_HOST -p $ALT_REMOTE_DB_PORT -U $ALT_REMOTE_DB_USER -d $ALT_REMOTE_DB_NAME \
    -c "DELETE FROM globaltrust WHERE date = (SELECT min(date) FROM tmp_globaltrust_v2${OPT_DATE_SUFFIX});
  INSERT INTO globaltrust SELECT * FROM tmp_globaltrust_v2${OPT_DATE_SUFFIX};"

  # Eigen8 vacuum and analyze
  PGPASSWORD=$ALT_REMOTE_DB_PASSWORD \
  $PSQL -e -h $ALT_REMOTE_DB_HOST -p $ALT_REMOTE_DB_PORT -U $ALT_REMOTE_DB_USER -d $ALT_REMOTE_DB_NAME \
    -c "VACUUM ANALYZE globaltrust;"

  if [ -z "$TARGET_DATE" ] && [[ $TEMP_DIR != $OUT_DIR ]]; then
    log "Moving generated files to graph folder"
    mv ${TEMP_DIR}/globaltrust.engagement.csv ${OUT_DIR}/
    mv ${TEMP_DIR}/globaltrust.following.csv ${OUT_DIR}/
    mv ${TEMP_DIR}/globaltrust.v3engagement.csv ${OUT_DIR}/
    mv ${TEMP_DIR}/localtrust.engagement.csv ${OUT_DIR}/
    mv ${TEMP_DIR}/localtrust.v3engagement.csv ${OUT_DIR}/
    mv ${TEMP_DIR}/localtrust.following.csv ${OUT_DIR}/
  fi

  log "Inserting localtrust_stats"

  if [ -f "${TEMP_DIR}/localtrust_stats.engagement${TARGET_DATE_SUFFIX}.csv" ]; then
    # Eigen8 insert localtrust stats for ENGAGEMENT strategy
    PGPASSWORD=$ALT_REMOTE_DB_PASSWORD \
    $PSQL -e -h $ALT_REMOTE_DB_HOST -p $ALT_REMOTE_DB_PORT -U $ALT_REMOTE_DB_USER -d $ALT_REMOTE_DB_NAME \
      -c  "COPY localtrust_stats_v2
      (date,strategy_id_row_count,strategy_id_mean,strategy_id_stddev,strategy_id_range,strategy_id)
      FROM STDIN WITH (FORMAT CSV, HEADER);" < ${TEMP_DIR}/localtrust_stats.engagement${TARGET_DATE_SUFFIX}.csv
  fi

  if [ -f "${TEMP_DIR}/localtrust_stats.following${TARGET_DATE_SUFFIX}.csv" ]; then
    # Eigen8 insert localtrust stats for FOLLOWING strategy
    PGPASSWORD=$ALT_REMOTE_DB_PASSWORD \
    $PSQL -e -h $ALT_REMOTE_DB_HOST -p $ALT_REMOTE_DB_PORT -U $ALT_REMOTE_DB_USER -d $ALT_REMOTE_DB_NAME \
      -c  "COPY localtrust_stats_v2
      (date,strategy_id_row_count,strategy_id_mean,strategy_id_stddev,strategy_id_range,strategy_id)
      FROM STDIN WITH (FORMAT CSV, HEADER);" < ${TEMP_DIR}/localtrust_stats.following${TARGET_DATE_SUFFIX}.csv
  fi

  if [ -f "${TEMP_DIR}/localtrust_stats.v3engagement${TARGET_DATE_SUFFIX}.csv" ]; then
    # Eigen8 insert localtrust stats for V3_ENGAGEMENT strategy
    PGPASSWORD=$ALT_REMOTE_DB_PASSWORD \
    $PSQL -e -h $ALT_REMOTE_DB_HOST -p $ALT_REMOTE_DB_PORT -U $ALT_REMOTE_DB_USER -d $ALT_REMOTE_DB_NAME \
      -c  "COPY localtrust_stats_v2
      (date,strategy_id_row_count,strategy_id_mean,strategy_id_stddev,strategy_id_range,strategy_id)
      FROM STDIN WITH (FORMAT CSV, HEADER);" < ${TEMP_DIR}/localtrust_stats.v3engagement${TARGET_DATE_SUFFIX}.csv
  fi

else
  echo "Invalid step specified."
  exit 1
fi

wait $!

this_name=`basename "$0"`

log "$this_name done!"
