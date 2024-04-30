#!/bin/bash

while getopts w:i:v: flag
do
    case "${flag}" in
        w) WORK_DIR=${OPTARG};;
        i) IN_LT=${OPTARG};;
        v) VENV=${OPTARG};;
    esac
done

if [ -z "$VENV" ]; then
  echo "Usage:   $0 -w [work_dir] -i [in_lt] -v [venv]"
  echo ""
  echo "Example: $0 -w . -i /home/ubuntu/serve_files/fc_engagement_fid_df.pkl -v /home/ubuntu/venvs/fc-graph-env3/"
  echo ""
  echo "Params:"
  echo "  [work_dir]  The working directory to read .env file and execute scripts from."
  echo "  [in_lt] The input localtrust file that the channel rankings is based on."
  echo "  [venv] The path where a python3 virtualenv has been created."
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
pip install -r requirements.txt
python3 -m channels.main -i founders degen base optimism farcaster -l $IN_LT 
deactivate
