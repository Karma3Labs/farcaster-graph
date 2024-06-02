#!/bin/bash

while getopts w:o:s:v: flag
do
    case "${flag}" in
        o) OUT_DIR=${OPTARG};;
        s) S3_BKT=${OPTARG};;
    esac
done

if [ -z "$OUT_DIR" ] || [ -s "$S3_BKT" ]; then
  echo "Usage:   $0 -o [out_dir] -s [s3_bkt]"
  echo ""
  echo "Example: $0 -o /tmp -s k3l-openrank-farcaster"
  echo ""
  echo "Params:"
  echo "  [out_dir]   The output directory to write the graph file."
  echo "  [s3_bkt]    The s3 bucket to pull the graph file from."
  echo ""
  exit
fi

# set -x
set -e
set -o pipefail

aws s3 cp s3://${S3_BKT}/personal_graph.parquet $OUT_DIR/personal_graph.parquet.new

if [ -n "$OUT_DIR/personal_graph.parquet" ]; then
  new_size=`du -m $OUT_DIR/personal_graph.parquet.new | cut -f1`
  prev_size=`du -m $OUT_DIR/personal_graph.parquet | cut -f1`
  size_diff="$((new_size-prev_size))"
  if [[ $size_diff -lt -100 ]]; then
    then
      echo 'New graph smaller than previously generated graph. Abort script.'
      exit 1
  fi
mv $OUT_DIR/personal_graph.parquet.new $OUT_DIR/personal_graph.parquet
# touch success file so that serving code can reload
touch $OUT_DIR/personal_graph_SUCCESS