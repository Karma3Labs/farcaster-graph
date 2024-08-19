#!/bin/bash
while getopts w: flag
do
    case "${flag}" in
        w) WORK_DIR=${OPTARG};;
    esac
done

shift $((OPTIND-1))
SQL_STATEMENT="$1"

if [ -z "$WORK_DIR" ]; then
  echo "Usage:   $0 -w [work_dir] [sql_statement]"
  echo ""
  echo "Example: $0 -w .  -c 'REFRESH MATERIALIZED VIEW CONCURRENTLY k3l_rank;'"
  echo ""
  echo "Params:"
  echo "  [work_dir]  The working directory to read .env file and execute scripts from."
  echo "  [sql_statement] Optional sql statement to execute."
  echo ""
  exit 1
fi

source $WORK_DIR/.env

DB_HOST=${DB_HOST:-127.0.0.1}
DB_PORT=${DB_PORT:-5432}
DB_USER=${DB_USER:-replicator}
DB_NAME=${DB_NAME:-replicator}
DB_PASSWORD=${DB_PASSWORD:-password} # psql requires PGPASSWORD to be set

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

PGPASSWORD=$DB_PASSWORD $PSQL -e -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME \
  -c "$SQL_STATEMENT"