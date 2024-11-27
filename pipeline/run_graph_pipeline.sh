#!/bin/bash

while getopts i:o:p:w:v: flag
do
    case "${flag}" in
        i) IN_FILE=${OPTARG};;
        o) OUT_DIR=${OPTARG};;
        p) OUT_PREFIX=${OPTARG};;
        w) WORK_DIR=${OPTARG};;
        v) VENV=${OPTARG};;
    esac
done

if [ -z "$IN_FILE" ] || [ -z "$OUT_DIR" ] || [ -z "$OUT_PREFIX" ] || [ -z "$WORK_DIR" ] || [ -z "$VENV" ]; then
  echo "Usage:   $0 -w [work_dir]  -v [venv] -i [in_file] -o [out_dir] -p [out_prefix]"
  echo ""
  echo "Example: $0 -w . -v /home/ubuntu/venvs/fc-graph-env3/ -i /tmp -o /tmp -p test"
  echo ""
  echo "Params:"
  echo "  [work_dir]  The working directory to read .env file and execute scripts from."
  echo "  [venv] The path where a python3 virtualenv has been created."
  echo "  [in_file] The input localtrust (i,j,v edge list) csv file."
  echo "  [out_dir] The output directory to write the graph file."
  echo "  [out_prefix] The prefix of the output graph files."
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
#pip install -r requirements.txt
python3 -m graph.gen_igraph -i $IN_FILE -o $OUT_DIR -p $OUT_PREFIX
touch $OUT_DIR/${OUT_PREFIX}_SUCCESS
deactivate
