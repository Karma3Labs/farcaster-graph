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

ALT_REMOTE_DB_HOST=${ALT_REMOTE_DB_HOST:-127.0.0.1}
ALT_REMOTE_DB_PORT=${ALT_REMOTE_DB_PORT:-5432}
ALT_REMOTE_DB_USER=${ALT_REMOTE_DB_USER:-k3l_user}
ALT_REMOTE_DB_NAME=${ALT_REMOTE_DB_NAME:-farcaster}
ALT_REMOTE_DB_PASSWORD=${ALT_REMOTE_DB_PASSWORD:-password} # psql requires PGPASSWORD to be set

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

PGPASSWORD=$ALT_REMOTE_DB_PASSWORD $PSQL -e -h $ALT_REMOTE_DB_HOST \
  -p $ALT_REMOTE_DB_PORT -U $ALT_REMOTE_DB_USER -d $ALT_REMOTE_DB_NAME \
  -c "$SQL_STATEMENT"