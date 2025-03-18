#!/bin/bash

while getopts w:v:t:r:n:c:s:b:i: flag
do
    case "${flag}" in
        w) WORK_DIR=${OPTARG};;
        v) VENV=${OPTARG};;
        t) TASK=${OPTARG};;
        r) RUN_ID=${OPTARG};;
        n) NUM_DAYS=${OPTARG};;
        c) NUM_BATCHES=${OPTARG};;
        s) SEED_CSV=${OPTARG};;
        b) BOTS_CSV=${OPTARG};;
        i) BATCH_ID=${OPTARG};;
    esac
done

shift $((OPTIND-1))
CHANNEL_IDS="$1"

if [ -z "$WORK_DIR" ] || [ -z "$VENV" ] || [ -z "$TASK" ] || [ -z "$RUN_ID" ] || [ -z "$NUM_DAYS" ] ; then
  echo "Usage:   $0 -w [work_dir] -v [venv] -t [task] -r [run_id] -n [num_days] -c [num_batches]"
  echo "Usage:   $0 -w [work_dir] -v [venv] -t [task] -r [run_id] -n [num_days] -s [seed_csv] -b [bots_csv] -i [batch_id]"
  echo ""
  echo "Example: $0 -w . -v /home/ubuntu/venvs/fc-graph-env3/ -t prep -r manual__2025-03-17T12:00:01.671847+00:00 -n 60 -c 100"
  echo "         $0 -w . -v /home/ubuntu/venvs/fc-graph-env3/ -t process -r manual__2025-03-17T12:00:01.671847+00:00 -n 60 -s channels/Seed_Fids.csv -b channels/Bot_Fids.csv -i 12"
  echo ""
  echo "Params:"
  echo "  [work_dir]  The working directory to read .env file and execute scripts from."
  echo "  [venv] The path where a python3 virtualenv has been created."
  echo "  [task] The task to perform: prep or process."
  echo "  [run_id] Any aribtrary unique string usually the Airflow run_id to use for the run."
  echo "  [num_days] The number of days of channel interactions to process."
  echo "  [num_batches] The number of batches of channels to process relates to number of Airflow mapped tasks."
  echo "  [seed_csv] The path to the Seed CSV file."
  echo "  [bots_csv] The path to the Bots CSV file."
  echo "  [batch_id] The batch ID to process."
  echo ""
  exit 1
fi

if [ "$TASK" = "prep" ]; then
  if [ -z "$NUM_BATCHES" ] ; then
    echo "Please specify -c (num_batches) for the prep task."
    exit 1
  fi
fi

if [ "$TASK" = "process" ]; then
  if [ -z "$SEED_CSV" ] || [ -z "$BOTS_CSV" ] || [ -z "$BATCH_ID" ]; then
    echo "Please specify -s (seed_csv), -b (bots_csv), and -i (batch_id) for the process task."
    exit 1
  fi
fi

log() {
  echo "`date` - $1"
}

log "Starting script with parameters: WORK_DIR=${WORK_DIR},\
  VENV=${VENV}, TASK=${TASK}, CSV_PATH=${RUN_ID},\
  NUM_DAYS=${NUM_DAYS}, NUM_BATCHES=${NUM_BATCHES}, \
  SEED_CSV=${SEED_CSV}, BOTS_CSV=${BOTS_CSV}, BATCH_ID=${BATCH_ID}"

source $WORK_DIR/.env


set -e
set -o pipefail

log "Activating virtual environment"
source $VENV/bin/activate
# pip install -r requirements.txt

log "Executing task: $TASK"
if [ "$TASK" = "prep" ]; then
  python3 -m channels.main_channel_rank -t prep -r "$RUN_ID" -n "$NUM_DAYS" -c "$NUM_BATCHES"
  deactivate
elif [ "$TASK" = "process" ]; then
  python3 -m channels.main_channel_rank -t process -r "$RUN_ID" -n "$NUM_DAYS" \
    -s "$SEED_CSV" -b "$BOTS_CSV" -i "$BATCH_ID"
  deactivate
else
  echo "Invalid task specified. Use 'prep' or 'process'."
  exit 1
fi
