#!/bin/bash

while getopts v:s: flag
do
    case "${flag}" in
        v) VENV=${OPTARG};;
        s) S3_BKT=${OPTARG};;
    esac
done

if [ -z "$VENV" ] || [ -z "$S3_BKT" ]; then
  echo "Usage:   $0 -v [venv] -s [s3_bkt]"
  echo ""
  echo "Example: $0 -v /home/ubuntu/venvs/fc-graph-env3/ -s bucket"
  echo ""
  echo "Params:"
  echo "  [venv] The path where a python3 virtualenv has been created."
  echo "  [s3_bkt] The S3 bucket to upload the graph file to."
  echo ""
  exit
fi

# set -x
set -e
set -o pipefail

function log() {
  echo "`date` - $1"
}

FILENAME="top_spammers.json"

source $VENV/bin/activate
pip install -r requirements.txt
python3 -m casts.main_fetch_top_spammers -f $FILENAME
aws s3 cp $FILENAME s3://${S3_BKT}/$FILENAME
rm $FILENAME
deactivate
