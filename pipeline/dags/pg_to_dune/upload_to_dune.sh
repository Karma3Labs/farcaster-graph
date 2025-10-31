#!/bin/bash

source ./.env
# S3_BUCKET_NAME_CONSTANT=${S3_BUCKET_NAME_CONSTANT:-"k3l-cast-to-dune/constant"}
S3_BUCKET_NAME_CONSTANT=${S3_BUCKET_NAME_CONSTANT:-"k3l-openrank-farcaster"}
S3_BUCKET_NAME_BACKUP=${S3_BUCKET_NAME_BACKUP:-"k3l-farcaster-backups"}
if [[ $(uname) == "Darwin" ]]; then
  TIMESTAMP=$(date -j -v-1d +%Y-%m-%d)
else
  TIMESTAMP=$(date +"%Y-%m-%d" -d yesterday)
fi
CURR_DIR=$PWD
WORK_DIR=$PWD/csv/$TIMESTAMP
GCP_ACTIVE_ACCT=$(gcloud auth list 2>&1 | grep '*' | awk {'print $2'})
GCP_TASK_ACCT=${GCP_TASK_ACCT:-"$(gcloud config get account --quiet)"}
GCS_BUCKET_NAME=${GCS_BUCKET_NAME:-"k3l-crypto/openrank"}
DUNE_API_KEY=${DUNE_API_KEY:-CHANGEME}

set -e
set -o pipefail

# Create the .aws directory if it doesn't exist
mkdir -p ~/.aws

# Write the content to ~/.aws/credentials
echo "[default]
aws_access_key_id=$AWS_ACCESS_KEY_ID
aws_secret_access_key=$AWS_SECRET_ACCESS_KEY
region=$AWS_REGION" > ~/.aws/credentials

# Relative path is not allowed in Postgres COPY TO command
mkdir -p $WORK_DIR

function log() {
    echo "`date` - $1"
}

# Switch to a task-related GCP account if it is different with the active account
switch_gcp_account() {
    if [ $GCP_TASK_ACCT != $GCP_ACTIVE_ACCT ]; then
        gcloud config set account "$GCP_TASK_ACCT"
    fi
}

# Switch back to the active GCP account after task completion
switch_back_gcp_account() {
    if [ $GCP_TASK_ACCT != $GCP_ACTIVE_ACCT ]; then
        gcloud config set account "$GCP_ACTIVE_ACCT"
    fi
}


# Function to export data to CSV and upload to S3
export_to_csv() {
  local table="$1"
  local csv_file="$2"
  local query="$3"

  log "Exporting $table to CSV..."
  PGPASSWORD=$DB_PASSWORD  psql -e -h $DB_HOST -U $DB_USERNAME -d $DB_NAME -p $DB_PORT -c "$query"
  log "Exported $table to $csv_file"
}

export_alt_to_csv() {
  local table="$1"
  local csv_file="$2"
  local query="$3"

  log "Exporting $table from $ALT_DB_HOST to CSV..."
  PGPASSWORD=$ALT_DB_PASSWORD  psql -e -h $ALT_DB_HOST -U $ALT_DB_USERNAME -d $ALT_DB_NAME -p $ALT_DB_PORT -c "$query"
  log "Exported $table to $csv_file"
}

publish_to_s3() {
  local csv_file="$1"
  local s3_bucket="s3://$S3_BUCKET_NAME_CONSTANT/"

  log "GZipping $csv_file"
  /usr/bin/gzip -f $csv_file
  
  upload_to_s3 "$csv_file.gz" "$s3_bucket"
}

publish_to_s3_and_cleanup() {
  local csv_file="$1"

  publish_to_s3 "$csv_file"
  rm "$csv_file.gz"
}

backup_to_s3_and_cleanup() {
  local csv_file="$1"
  local filename="$2"

  local s3_bucket="s3://$S3_BUCKET_NAME_BACKUP/historical/$TIMESTAMP/"

  TS_SECONDS=$(date +%s)
  local csv_gz_file="${WORK_DIR}/${filename}_${TS_SECONDS}.csv.gz"
  mv "$csv_file.gz" "$csv_gz_file"
  upload_to_s3 "$csv_gz_file" "$s3_bucket"
  rm $csv_gz_file
}

upload_to_s3() {
  local csv_file_gz="$1"
  local s3_bucket="$2"

  log "Uploading to S3 folder: $s3_bucket"
  aws s3 cp "${csv_file_gz}" "$s3_bucket"
  log "Uploaded ${csv_file_gz} to $s3_bucket"
}

export_csv_to_bq() {
  if [ -z "$GCS_BUCKET_NAME" ]; then
    log 'No GCS_BUCKET_NAME defined, skipping upload to Google Cloud Storage'
    return
  fi
  local csv_file="$1"
  log "Uploading ${csv_file}.gz to $GCS_BUCKET_NAME/$TIMESTAMP"
  gsutil -h "Content-Type: application/gzip" cp "${csv_file}".gz "gs://$GCS_BUCKET_NAME/$TIMESTAMP/"
}

# Function to export and process globaltrust table
process_globaltrust() {
  filename="k3l_cast_globaltrust"
  csv_file="${WORK_DIR}/$filename.csv"

  export_alt_to_csv "globaltrust" "$csv_file" "\COPY (SELECT i, v, date, strategy_id FROM globaltrust WHERE date >= now()-interval '45' day ) TO '${csv_file}' WITH (FORMAT CSV, HEADER)"
  # split_and_post_csv "$csv_file" 10 "dataset_k3l_cast_globaltrust_v2"
  /usr/bin/gzip -f $csv_file
  # export_csv_to_bq "$csv_file"
  backup_to_s3_and_cleanup "$csv_file" "$filename"
}

# Function to export and process globaltrust_config table
process_globaltrust_config() {
  filename="k3l_cast_globaltrust_config"
  csv_file="${WORK_DIR}/$filename.csv"

  export_alt_to_csv "globaltrust_config" "$csv_file" "\COPY (SELECT strategy_id, strategy_name, pretrust, localtrust, alpha, date FROM globaltrust_config) TO '${csv_file}' WITH (FORMAT CSV, HEADER)"
  # split_and_post_csv "$csv_file" 1 "dataset_k3l_cast_globaltrust_config_v2"
  /usr/bin/gzip -f $csv_file
  # export_csv_to_bq "$csv_file"
  backup_to_s3_and_cleanup "$csv_file" "$filename"
}

# Function to export and process localtrust table
process_localtrust_v1() {
  local graph_folder="$1"

  filename="k3l_cast_localtrust"
  csv_file="${WORK_DIR}/k3l_cast_localtrust.csv"

  cat $graph_folder/localtrust.engagement.csv > $csv_file
  tail -n+2 $graph_folder/localtrust.v3engagement.csv >> $csv_file
  tail -n+2 $graph_folder/localtrust.following.csv >> $csv_file

  /usr/bin/gzip -f $csv_file
  backup_to_s3_and_cleanup "$csv_file" "$filename"
}

# DEPRECATED
upload_lifetime_channel_rank_to_public_s3() {
  filename="k3l_channel_rankings"
  csv_file="${WORK_DIR}/$filename.csv"

  export_alt_to_csv \
  "k3l_channel_rank" \
   "$csv_file" \
   "\COPY (SELECT pseudo_id, channel_id, fid, score, rank, compute_ts, strategy_name\
    FROM k3l_channel_rank\
    WHERE strategy_name = 'channel_engagement')\
    TO '${csv_file}' WITH (FORMAT CSV, HEADER)"
  # split_and_post_csv "$csv_file" 20 "dataset_k3l_cast_channel_ranking"
  publish_to_s3_and_cleanup "$csv_file"
}

backup_all_channel_rank_to_private_s3() {
  filename="k3l_channel_rankings_all"
  csv_file="${WORK_DIR}/$filename.csv"
  export_alt_to_csv \
  "k3l_channel_rank" \
   "$csv_file" \
   "\COPY (SELECT pseudo_id, channel_id, fid, score, rank, compute_ts, strategy_name\
    FROM k3l_channel_rank)\
    TO '${csv_file}' WITH (FORMAT CSV, HEADER)"

  /usr/bin/gzip -f $csv_file

  backup_to_s3_and_cleanup "$csv_file" "$filename"
}

backup_channel_points_bal_to_private_s3() {
  filename="k3l_channel_points_bal"
  csv_file="${WORK_DIR}/$filename.csv"
  export_alt_to_csv \
  "k3l_channel_points_bal" \
   "$csv_file" \
   "\COPY (SELECT fid, channel_id, balance, latest_earnings,\
    latest_score, latest_adj_score, insert_ts, update_ts\
    FROM k3l_channel_points_bal)\
    TO '${csv_file}' WITH (FORMAT CSV, HEADER)"

  /usr/bin/gzip -f $csv_file

  backup_to_s3_and_cleanup "$csv_file" "$filename"
}

backup_channel_tokens_bal_to_private_s3() {
  filename="k3l_channel_tokens_bal"
  csv_file="${WORK_DIR}/$filename.csv"
  export_alt_to_csv \
  "k3l_channel_tokens_bal" \
   "$csv_file" \
   "\COPY (SELECT fid, channel_id, balance, latest_earnings,\
    insert_ts, update_ts\
    FROM k3l_channel_tokens_bal)\
    TO '${csv_file}' WITH (FORMAT CSV, HEADER)"

  /usr/bin/gzip -f $csv_file

  backup_to_s3_and_cleanup "$csv_file" "$filename"
}

backup_channel_tokens_log_to_private_s3() {
  filename="k3l_channel_tokens_log"
  csv_file="${WORK_DIR}/$filename.csv"
  export_alt_to_csv \
  "k3l_channel_tokens_log" \
   "$csv_file" \
   "\COPY (SELECT fid, channel_id, amt, latest_points,\
    points_ts, dist_id, dist_status, insert_ts, update_ts,\
    fid_address, dist_reason, txn_hash, batch_id\
    FROM k3l_channel_tokens_log)\
    TO '${csv_file}' WITH (FORMAT CSV, HEADER)"

  /usr/bin/gzip -f $csv_file

  backup_to_s3_and_cleanup "$csv_file" "$filename"
}

overwrite_global_engagement_rankings_in_s3() {
  filename="k3l_global_engagement_rankings"
  tmp_folder="tmp_overwrite_globalrank_for_neynar"
  csv_file="$tmp_folder/$filename.csv"
  mkdir -p $tmp_folder
  shopt -s nullglob
  rm -f "$tmp_folder"/*

  rm -f $csv_file
  export_alt_to_csv \
    "k3l_rank" \
    "$csv_file" \
    "\COPY (SELECT profile_id as fid, score FROM k3l_rank WHERE strategy_id = 9)\
      TO '${csv_file}' WITH (FORMAT CSV, HEADER)"
  publish_to_s3_and_cleanup "$csv_file"
}

# Main script execution
if [[ $# -eq 0 ]]; then
    echo "Usage: $0 {globaltrust|globaltrust_config|localtrust|upload_channel_rank_to_s3}"
    exit 1
fi

# Switch to task-related GCP account
# switch_gcp_account

case "$1" in
    globaltrust)
        process_globaltrust
        ;;
    globaltrust_config)
        process_globaltrust_config
        ;;
    localtrust_v1)
        process_localtrust_v1 $2
        ;;
    upload_channel_rank_to_s3)
        # upload_lifetime_channel_rank_to_public_s3
        backup_all_channel_rank_to_private_s3
        ;;
    backup_channel_points_bal)
        backup_channel_points_bal_to_private_s3
        ;;
    backup_channel_tokens)
        backup_channel_tokens_bal_to_private_s3
        backup_channel_tokens_log_to_private_s3
        ;;
    overwrite_global_engagement_rankings_in_s3)
        overwrite_global_engagement_rankings_in_s3
        ;;
    *)
        echo "Usage: $0 {globaltrust|globaltrust_config|localtrust|upload_channel_rank_to_s3}"
        exit 1
        ;;
esac

# Switch back to the original GCP account
# switch_back_gcp_account

log "All jobs completed!"
