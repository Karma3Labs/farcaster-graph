#!/bin/bash

while getopts "w:v:b:d" flag
do
    case "${flag}" in
        w) WORK_DIR=${OPTARG};;
        v) VENV=${OPTARG};;
        b) BOTS_CSV=${OPTARG};;
        d) DRYRUN_FLAG="--dry-run";;
    esac
done

if [ -z "$WORK_DIR" ] || [ -z "$VENV" ] || [ -z "$BOTS_CSV" ]; then
  echo "Usage:   $0 -w [work_dir] -v [venv] -b [bots_csv] -d"
  echo ""
  echo "Example: $0 -w . -v /home/ubuntu/venvs/fc-graph-env3/ -b channels/Bot_Fids.csv"
  echo "Example: $0 -w . -v /home/ubuntu/venvs/fc-graph-env3/ -b channels/Bot_Fids.csv -d"
  echo ""
  echo "Params:"
  echo "  [work_dir] The working directory to read .env file and execute scripts from."
  echo "  [venv] The path where a python3 virtualenv has been created."
  echo "  [bots_csv] The path to the CSV file that has list of mod bots."
  echo "  [dryrun] Flag to run the script in dry-run mode."
  echo ""
  exit
fi

source $WORK_DIR/.env

# set -x
set -e
set -o pipefail

function log() {
  echo "`date` - $1"
}

source $VENV/bin/activate
#pip install -r requirements.txt
python3 -m channels.main_notify_weekly_mods -b "$BOTS_CSV" $DRYRUN_FLAG
deactivate
