#!/bin/bash

while getopts i:o:w:v: flag
do
    case "${flag}" in
        i) IN_CSV=${OPTARG};;
        o) OUT_DIR=${OPTARG};;
        w) WORK_DIR=${OPTARG};;
        v) VENV=${OPTARG};;
    esac
done

if [ -z "$IN_CSV" ] || [ -z "$OUT_DIR" ] || [ -z "$WORK_DIR" ] || [ -z "$VENV" ]; then
  echo "Usage:   $0 -i [in_csv] -o [out_dir] -w [work_dir] -v [venv]"
  echo ""
  echo "Example: $0 -i /home/ubuntu/serve_files/lt_engagement_fid.csv -w . -o /tmp/personal-graph/ -v .venv"
  echo ""
  echo "Params:"
  echo "  [in_csv]  The source file to read dataframe from."
  echo "  [out_dir] The output directory to write the graph file."
  echo "  [work_dir]  The working directory to read .env file and execute scripts from."
  echo "  [venv] The path where a python3 virtualenv has been created."
  echo ""
  exit
fi


source $WORK_DIR/.env

# set -x
set -e
set -o pipefail

source $VENV/bin/activate
pip install -r requirements.txt
python3 -m graph.gen_personal_graph_amp -i $IN_CSV -o $OUT_DIR -p 10 -c 100 -m 1000
deactivate
