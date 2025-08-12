#!/bin/bash

# dayOfYear=`date '+%j'`
# hourOfDay=`date '+%H'`
# hourOfYear="$((dayOfYear * 24 + hourOfDay))"
# echo $dayOfYear $hourOfDay $hourOfYear
# hour_interval=48

# # TODO use the mtime of the existing parquet file and
# # ..if current time - mtime > 1 hour, start compute
# if [ `expr $hourOfYear % $hour_interval` -eq 0 ]; then
#    echo "This is hour $hour_interval. Continuing with script."
# else
#    echo "This not hour $hour_interval. Exiting now."
#    exit 0
# fi


while getopts i:o:s:w:v:l:t:f:r:m: flag
do
    case "${flag}" in
        i) IN_CSV=${OPTARG};;
        o) OUT_DIR=${OPTARG};;
        s) S3_BKT=${OPTARG};;
        w) WORK_DIR=${OPTARG};;
        v) VENV=${OPTARG};;
        t) TASK=${OPTARG};;
        f) FIDS=${OPTARG};;
        r) RUN_ID=${OPTARG};;
        m) MAP_INDEX=${OPTARG};;
    esac
done

if [ -z "$IN_CSV" ] || [ -z "$WORK_DIR" ] || [ -z "$VENV" ] || [ -z "$OUT_DIR" ] || [ -z "$S3_BKT" ] || [ -z "$TASK" ]; then
  echo "Usage:   $0 -i [in_csv] -w [work_dir] -v [venv] -o [out_dir] -s [s3_bkt] -t [task] -f [fids] -r [run_id] -m [map_index]"
  echo ""
  echo "Example: $0 \ "
  echo "  -i /home/ubuntu/serve_files/lt_engagement_fid.csv \ "
  echo "  -w . \ "
  echo "  -v .venv \ "
  echo "  -o /tmp/personal-graph/ \ "
  echo "  -s k3l-openrank-farcaster \ "
  echo ""
  echo "Params:"
  echo "  [in_csv]  The source file to read dataframe from."
  echo "  [out_dir] The output directory to write the graph file."
  echo "  [work_dir]  The working directory to read .env file and execute scripts from."
  echo "  [venv] The path where a python3 virtualenv has been created."
  echo "  [s3_bkt] The S3 bucket to upload the graph file to."
  echo "  [task] task to run. choose one: graph_reload, generate, fetch_fids, consolidate"
  echo "  [fids] comma separated fids to run '1,2,3,420,69'"
  echo "  [run_id] airflow run id. eg) 'manual__2024-07-22T06:46:15.813325+00:00' "
  echo "  [map_index] airflow map index"
  echo ""
  exit
fi

source $WORK_DIR/.env

set -x
set -e
set -o pipefail

mkdir -p ${OUT_DIR}/${RUN_ID}

TMP_GRAPH_OUT=${OUT_DIR}/${RUN_ID}_temp_graph/
mkdir -p $TMP_GRAPH_OUT
TMP_GRAPH_PKL="${TMP_GRAPH_OUT}/edges_df.pkl"
# rm ${OUT_DIR}/temp-graph/*

echo "Executing task: $TASK"
if [ "$TASK" = "fetch_fids" ]; then
  echo "Activating virtual env"
  source $VENV/bin/activate

  echo "PIP installing"
  pip install -r requirements.txt

  echo "Fetching node edges from $IN_CSV"
  python3 -m graph.fetch_nodes_edges -i $IN_CSV -c 1000 -o $TMP_GRAPH_PKL
elif [ "$TASK" = "graph_reload" ]; then
  # TODO - Fix this ugly code
  # Reload twice because we have 2 instances of igraph server round robin load
  # Fail if any response other than 200
  # Reload graph takes a while so set timeout to 5 mins
  curl -X 'GET' $PERSONAL_IGRAPH_URL/_reload --fail --max-time 600
  echo "One graph instance reloaded"
  curl -X 'GET' $PERSONAL_IGRAPH_URL/_reload --fail --max-time 600
  echo "Another graph instance reloaded"
elif [ "$TASK" = "generate" ]; then
  source $VENV/bin/activate
  pip install -r requirements.txt
  # ls $TMP_GRAPH_OUT
  # echo "received FIDS: $FIDS"

  # generate graph with 10 parallel worker chunks and 1000 neighbors
  python3 -m graph.gen_personal_graph_amp_v1 -i $TMP_GRAPH_PKL -o ${OUT_DIR}/${RUN_ID} -c 60 -m 1000 -f $FIDS -s $MAP_INDEX

elif [ "$TASK" = "consolidate" ]; then
  source $VENV/bin/activate
  pip install -r requirements.txt

  # remove parsed pkl file from the job
  rm -rf $TMP_GRAPH_OUT

  # if previous graph compute exists, confirm that the new output is larger in size
  if [ -d "$OUT_DIR/temp" ]; then
    new_size=$(du -sm ${OUT_DIR}/${RUN_ID} | cut -f1)
    prev_size=$(du -sm ${OUT_DIR}/temp | cut -f1)
    size_diff=$((new_size - prev_size))
    if [[ $size_diff -lt -500 ]]; then
      echo 'New graph parts much smaller than previously generated graph parts. Abort script.'
      exit 1
    fi
  fi

  # if graph creation succeeded, replace previous job output with current job output
  rm -rf ${OUT_DIR}/temp
  mv ${OUT_DIR}/${RUN_ID} ${OUT_DIR}/temp

  # consolidate approx 4000 small pqt files into 1 big parquet file
  python3 -m graph.rechunk_graph_pqt -i ${OUT_DIR}/temp -o $OUT_DIR/personal_graph.parquet.new

  # if previous graph file exists, confirm that the new file is larger in size
  if [ -f "$OUT_DIR/personal_graph.parquet" ]; then
    new_size=$(du -sm $OUT_DIR/personal_graph.parquet.new | cut -f1)
    prev_size=$(du -sm $OUT_DIR/personal_graph.parquet | cut -f1)
    size_diff=$((new_size - prev_size))
    if [[ $size_diff -lt -150 ]]; then
      echo 'New graph file much smaller than previously generated graph file. Abort script.'
      exit 1
    fi
  fi
  mv $OUT_DIR/personal_graph.parquet.new $OUT_DIR/personal_graph.parquet

  deactivate

  aws s3 cp $OUT_DIR/personal_graph.parquet s3://${S3_BKT}/
  intDayOfWeek=$(date '+%u') # keep up to last 7 days of backup copies
  aws s3 cp $OUT_DIR/personal_graph.parquet s3://${S3_BKT}/historical/${intDayOfWeek}/
elif [ "$TASK" = "cleanup" ]; then
  echo "removing $TMP_GRAPH_OUT"
  rm -rf $TMP_GRAPH_OUT

  echo "removing ${OUT_DIR}/${RUN_ID}"
  rm -rf ${OUT_DIR}/${RUN_ID}
else
  echo "Invalid task specified."
  exit 1
fi