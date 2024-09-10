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


while getopts o:s: flag
do
    case "${flag}" in
        o) OUT_DIR=${OPTARG};;
        s) S3_BKT=${OPTARG};;
    esac
done

if [ -z "$OUT_DIR" ] || [ -z "$S3_BKT" ]; then
  echo "Usage:   $0  -o [out_dir] -s [s3_bkt]"
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

aws s3 cp s3://${S3_BKT}/personal_graph.parquet $OUT_DIR/personal_graph.parquet