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

JOBTIME=$(date +%Y%m%d%H%M%S)

source $WORK_DIR/.env

# set -x
set -e
set -o pipefail

mkdir -p ${OUT_DIR}/temp-${JOBTIME}

source $VENV/bin/activate
pip install -r requirements.txt

# generate graph with 10 processes, 100 child threads and 1000 neighbors
python3 -m graph.gen_personal_graph_amp -i $IN_CSV -o ${OUT_DIR}/temp-${JOBTIME} -p 10 -c 100 -m 1000

# if graph creation succeeded, replace previous job output with current job output 
rm -rf ${OUT_DIR}/temp
mv ${OUT_DIR}/temp-${JOBTIME} ${OUT_DIR}/temp

# consolidate approx 4000 small pqt files into 1 big parquet file
python3 -m graph.rechunk_graph_pqt -i ${OUT_DIR}/temp -o $OUT_DIR/personal_graph.parquet

# TODO copy personal_graph.parquet to S3
deactivate
