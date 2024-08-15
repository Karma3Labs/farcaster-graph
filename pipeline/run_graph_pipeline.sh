#!/bin/bash

while getopts i:w:o:v: flag
do
    case "${flag}" in
        i) IN_DIR=${OPTARG};;
        o) OUT_DIR=${OPTARG};;
        w) WORK_DIR=${OPTARG};;
        v) VENV=${OPTARG};;
    esac
done

if [ -z "$WORK_DIR" ] || [ -z "$OUT_DIR" ] || [ -z "$IN_DIR" ] || [ -z "$VENV" ]; then
  echo "Usage:   $0 -w [work_dir] -i [in_dir] -o [out_dir] -v [venv]"
  echo ""
  echo "Example: $0 -w . -i /tmp -o /tmp -v /home/ubuntu/venvs/fc-graph-env3/"
  echo ""
  echo "Params:"
  echo "  [work_dir]  The working directory to read .env file and execute scripts from."
  echo "  [in_dir] The input directory to read the csv files."
  echo "  [out_dir] The output directory to write the graph file."
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

mkdir -p $OUT_DIR

source $VENV/bin/activate
pip install -r requirements.txt
python3 -m graph.gen_igraph -i $IN_DIR/localtrust.following.csv -o $OUT_DIR -p fc_following_fid
touch $OUT_DIR/fc_following_fid_SUCCESS
python3 -m graph.gen_igraph -i $IN_DIR/localtrust.engagement.csv -o $OUT_DIR -p fc_engagement_fid
touch $OUT_DIR/fc_engagement_fid_SUCCESS
deactivate
