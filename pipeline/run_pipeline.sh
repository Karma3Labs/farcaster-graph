#!/bin/bash

while getopts w:o: flag
do
    case "${flag}" in
        o) OUT_DIR=${OPTARG};;
        w) WORK_DIR=${OPTARG};;
    esac
done

if [ -z "$OUT_DIR" ] || [ -z "$WORK_DIR" ]; then
  echo "Usage:   $0 -w [work_dir] -o [out_dir]"
  echo ""
  echo "Example: $0 -w . -o /tmp"
  echo ""
  echo "Params:"
  echo "  [work_dir]  The working directory to read .env file and execute scripts from."
  echo "  [out_dir] The output directory to write the graph file."
  echo ""
  exit
fi


source $WORK_DIR/.env

DB_HOST=${DB_HOST:-127.0.0.1}
DB_PORT=${DB_PORT:-5432}
DB_USER=${DB_USER:-replicator}
DB_NAME=${DB_NAME:-replicator}
DB_PASSWORD=${DB_PASSWORD:-password} # psql requires PGPASSWORD to be set
VENV=${VENV:-"/home/ubuntu/venvs/fc-graph-env3/"}

# set -x
set -e
set -o pipefail

if hash psql 2>/dev/null; then
  echo "OK, you have psql in the path. We’ll use that."
  PSQL=psql
else
  echo "You don't have psql is the path. Let's try /usr/bin"
  hash /usr/bin/psql
  PSQL=/usr/bin/psql
fi

if [[ $(uname) == "Darwin" ]]; then
    SP=" " # Needed for portability with sed
fi

function log() {
  echo "`date` - $1"
}

# TODO parametrize strategy names in .sql files
log "Exporting localtrust existingConnections from Postgres to tmp folder"
PGPASSWORD=$DB_PASSWORD \
$PSQL -t -A -F',' -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME \
  -f export_existingConnections.sql -o /tmp/lt_existingConnections.csv
# NOTE: the -t option turns off headers and footers in the output. 
# We need to add column headers back.
sed -i${SP}'' '1s/^/i,j,v\n/' /tmp/lt_existingConnections.csv

log "Exporting localtrust l1rep6rec3m12enhancedConnections from Postgres to tmp folder"
PGPASSWORD=$DB_PASSWORD $PSQL -t -A -F',' -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME \
  -f export_l1rep6rec3m12enhancedConnections.sql -o /tmp/lt_l1rep6rec3m12enhancedConnections.csv
# NOTE: the -t option turns off headers and footers in the output. 
# We need to add column headers back
sed -i${SP}'' '1s/^/i,j,v\n/' /tmp/lt_l1rep6rec3m12enhancedConnections.csv

source $VENV/bin/activate
pip install -r requirements.txt
python gen_igraph.py -i /tmp/lt_existingConnections.csv -o /tmp/fc_following.pkl 
python gen_igraph.py -i /tmp/lt_l1rep6rec3m12enhancedConnections.csv -o /tmp/fc_engagement.pkl 
deactivate
