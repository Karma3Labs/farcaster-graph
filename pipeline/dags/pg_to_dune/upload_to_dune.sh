#!/bin/bash

source ./.env
S3_BUCKET_NAME_CONSTANT=${S3_BUCKET_NAME_CONSTANT:-"k3l-cast-to-dune/constant"}
S3_BUCKET_NAME_DAILY=${S3_BUCKET_NAME_DAILY:-"k3l-cast-to-dune"}
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

export_to_s3() {
  local csv_file="$1"
  local s3_bucket="$2"

  log "GZipping $csv_file"
  /usr/bin/gzip -f $csv_file

  log "Uploading to S3 folder: $s3_bucket"
  aws s3 cp "${csv_file}.gz" "$s3_bucket"
  log "Uploaded ${csv_file}.gz to $s3_bucket"
}

export_historical_to_s3_and_cleanup() {
  local csv_file="$1"
  local filename="$2"

  local s3_bucket="s3://$S3_BUCKET_NAME_DAILY/historical/$TIMESTAMP/"

  TS_SECONDS=$(date +%s)
  local csv_gz_file="${WORK_DIR}/${filename}_${TS_SECONDS}.csv.gz"
  mv "$csv_file.gz" "$csv_gz_file"
  export_gzip_to_s3 "$csv_gz_file" "$s3_bucket"
  rm $csv_gz_file
}

export_gzip_to_s3() {
  local csv_file="$1"
  local s3_bucket="$2"

  log "Uploading to S3 folder: $s3_bucket"
  aws s3 cp "${csv_file}" "$s3_bucket"
  log "Uploaded ${csv_file} to $s3_bucket"
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

split_and_post_csv() {
  local original_file="$1"
  local num_parts="$2"
  local table_name="$3"

  # Check if all arguments are provided
  if [[ -z "$original_file" || -z "$num_parts" || -z "$table_name" ]]; then
    echo "Usage: split_and_post_csv <original_file> <num_parts> <table_name>"
    return 1
  fi

  tmp_folder=tmp_${table_name}
  mkdir -p "$tmp_folder"
  shopt -s nullglob
  rm -f "$tmp_folder"/*

  # Extract the header
  header_file="$tmp_folder/header_$table_name.csv"
  head -n 1 "$original_file" > $header_file

  # Calculate the number of lines per part, excluding the header
  total_lines=$(wc -l < "$original_file")
  lines_per_part=$(( (total_lines - 1) / num_parts + 1 ))

  # Split the file without the header into parts
  tail -n +2 "$original_file" | split -l "$lines_per_part" - $tmp_folder/split_

  # Add the header to each split file and make an HTTP POST request
  for file in $tmp_folder/split_*
  do
    cat $header_file "$file" > "${file}.csv"

    log "Inserting ${file}.csv to ${table_name}"

    # Make the HTTP POST request
    response=$(curl -s -w "\nHTTP_CODE: %{http_code}\n" -X POST \
        -H "X-DUNE-API-KEY: ${DUNE_API_KEY}" \
        -H "Content-Type: text/csv" \
        --upload-file "${file}.csv" \
        "https://api.dune.com/api/v1/table/openrank/${table_name}/insert")
    # Extract the HTTP code from the response
    http_code=$(echo "$response" | tail -n 1 | cut -d ' ' -f 2)
    response_body=$(echo "$response" | sed '$d')

    # Log the response and check for successful upload
    log "HTTP code: $http_code,  Body:$response_body"

    if [[ "$http_code" -eq 200 ]]; then
      log "Successfully uploaded ${file}.csv"
    else
      log "Failed to upload ${file}.csv. HTTP response code: $http_code"
      exit 1
    fi

    # Clean up the temporary split file
    rm "$file" "${file}.csv"
  done

  # Clean up the header file
  rm $header_file
}

# Function to export and process globaltrust table
process_globaltrust() {
  filename="k3l_cast_globaltrust"
  csv_file="${WORK_DIR}/$filename.csv"
  s3_bucket="s3://$S3_BUCKET_NAME_CONSTANT/"
  export_to_csv "globaltrust" "$csv_file" "\COPY (SELECT i, v, date, strategy_id FROM globaltrust WHERE date >= now()-interval '45' day ) TO '${csv_file}' WITH (FORMAT CSV, HEADER)"
  # split_and_post_csv "$csv_file" 10 "dataset_k3l_cast_globaltrust_v2"
  export_to_s3 "$csv_file" "$s3_bucket"
  # export_csv_to_bq "$csv_file"
  export_historical_to_s3_and_cleanup "$csv_file" "$filename"
}

# Function to export and process globaltrust_config table
process_globaltrust_config() {
  filename="k3l_cast_globaltrust_config"
  csv_file="${WORK_DIR}/$filename.csv"
  s3_bucket="s3://$S3_BUCKET_NAME_CONSTANT/"
  export_to_csv "globaltrust_config" "$csv_file" "\COPY (SELECT strategy_id, strategy_name, pretrust, localtrust, alpha, date FROM globaltrust_config) TO '${csv_file}' WITH (FORMAT CSV, HEADER)"
  # split_and_post_csv "$csv_file" 1 "dataset_k3l_cast_globaltrust_config_v2"
  export_to_s3 "$csv_file" "$s3_bucket"
  #export_csv_to_bq "$csv_file"
  export_historical_to_s3_and_cleanup "$csv_file" "$filename"
}

# Function to export and process localtrust table
process_localtrust_v1() {
  local graph_folder="$1"

  filename="k3l_cast_localtrust"
  csv_file="${WORK_DIR}/k3l_cast_localtrust.csv"
  s3_bucket="s3://$S3_BUCKET_NAME_CONSTANT/"

  cat $graph_folder/localtrust.engagement.csv > $csv_file
  cat $graph_folder/localtrust.following.csv >> $csv_file

  export_to_s3 "$csv_file" "$s3_bucket"
  export_historical_to_s3_and_cleanup "$csv_file" "$filename"
}

# Function to export and process k3l_channel_rank table
process_channel_rank() {
  filename="k3l_channel_rankings"
  csv_file="${WORK_DIR}/$filename.csv"
  s3_bucket="s3://$S3_BUCKET_NAME_CONSTANT/"
  export_to_csv "k3l_channel_rank" "$csv_file" "\COPY (SELECT pseudo_id, channel_id, fid, score, rank, compute_ts, strategy_name FROM k3l_channel_rank) TO '${csv_file}' WITH (FORMAT CSV, HEADER)"
  # split_and_post_csv "$csv_file" 20 "dataset_k3l_cast_channel_ranking"
  export_to_s3 "$csv_file" "$s3_bucket"
  #export_csv_to_bq "$csv_file"
  export_historical_to_s3_and_cleanup "$csv_file" "$filename"
}

insert_globaltrust_to_dune_v2() {
  filename="k3l_cast_globaltrust_incremental"
  tmp_folder="tmp_insert_globaltrust_to_dune_v2"
  csv_file="$tmp_folder/${filename}.csv"
  mkdir -p $tmp_folder
  shopt -s nullglob
  rm -f "$tmp_folder"/*

  source ./.venv/bin/activate
  pip install dune_client
  DUNE_API_KEY=$DUNE_API_KEY QUERY_ID=3896616 FILTER_COLUMN="date" python -m app.check_last_timestamp > globaltrust_v2_last_date
  last_date=$(cat globaltrust_v2_last_date)
  rm globaltrust_v2_last_date

  export_to_csv "globaltrust" "$csv_file" "\COPY (SELECT i, v, date, strategy_id FROM globaltrust WHERE date > '${last_date}' ) TO '${csv_file}' WITH (FORMAT CSV, HEADER)"
  split_and_post_csv "$csv_file" 10 "dataset_k3l_cast_globaltrust_v2"
  rm $csv_file
  rm -rf $tmp_folder
}

insert_globaltrust_to_dune_v3() {
  filename="k3l_cast_globaltrust_full"
  tmp_folder="tmp_insert_globaltrust_to_dune_v3"
  csv_file="$tmp_folder/${filename}.csv"
  mkdir -p $tmp_folder
  shopt -s nullglob
  rm -f "$tmp_folder"/*

  export_to_csv "globaltrust" "$csv_file" "\COPY (SELECT i, v, date, strategy_id FROM globaltrust) TO '${csv_file}' WITH (FORMAT CSV, HEADER)"

  dune_table_name="dataset_k3l_cast_globaltrust"
  _clear_dune_table "openrank" $dune_table_name

  split_and_post_csv "$csv_file" 25 $dune_table_name
  rm $csv_file
  rm -rf $tmp_folder
}


insert_channel_rank_to_dune_v3() {
  filename="k3l_channel_rankings_full"
  tmp_folder="tmp_insert_channelrank_to_dune_v3"
  csv_file="$tmp_folder/$filename.csv"
  mkdir -p $tmp_folder
  shopt -s nullglob
  rm -f "$tmp_folder"/*

  rm -f $csv_file
  export_to_csv "k3l_channel_rank" "$csv_file" "\COPY (SELECT pseudo_id, channel_id, fid, score, rank, compute_ts, strategy_name FROM k3l_channel_rank) TO '${csv_file}' WITH (FORMAT CSV, HEADER)"

  dune_table_name="dataset_k3l_cast_channel_ranking"
  _clear_dune_table "openrank" $dune_table_name
  split_and_post_csv "$csv_file" 10 $dune_table_name
  rm $csv_file
  rm -rf $tmp_folder
}

insert_channel_rank_to_dune_v2() {
  filename="k3l_channel_rankings_incremental_v2"
  tmp_folder="tmp_insert_channelrank_to_dune_v2"
  csv_file="$tmp_folder/$filename.csv"
  mkdir -p $tmp_folder
  shopt -s nullglob
  rm -f "$tmp_folder"/*

  rm -f $csv_file
  export_to_csv "k3l_channel_rank" "$csv_file" "\COPY (SELECT pseudo_id, channel_id, fid, score, rank, compute_ts, strategy_name FROM k3l_channel_rank) TO '${csv_file}' WITH (FORMAT CSV, HEADER)"

  dune_table_name="dataset_k3l_cast_channel_ranking"
  _clear_dune_table "openrank" $dune_table_name
  split_and_post_csv "$csv_file" 10 $dune_table_name
  rm $csv_file
  rm -rf $tmp_folder
}

create_dune_globaltrust_table() {
  local dune_table_name="$1"

  # Make the HTTP POST request
  response=$(curl --request POST \
    --url https://api.dune.com/api/v1/table/create \
    --header "X-DUNE-API-KEY: ${DUNE_API_KEY}" \
    --header 'Content-Type: application/json' \
    --data '{
    "namespace":"openrank",
    "table_name":"'"${dune_table_name}"'",
    "description": "OpenRank global ranking of Farcaster users",
    "is_private": false,
    "schema": [{"name": "i", "type": "bigint"}, {"name": "v", "type": "double"}, {"name": "date", "type": "varchar"}, {"name": "strategy_id", "type": "integer"}]
  }' -w "%{http_code}")

  # Extract the HTTP code from the response
  http_code="${response: -3}"
  response_body="${response::-3}"

  # Log the response and check for successful upload
  log "HTTP code: $http_code, Body: $response_body"

  if [[ "$http_code" -eq 200 || "$http_code" -eq 201 ]]; then
    log "Successfully created ${dune_table_name}.csv"
  else
    log "Failed to create ${dune_table_name}.csv. HTTP response code: $http_code"
    exit 1
  fi

  filename="k3l_cast_globaltrust_full"
  csv_file="${WORK_DIR}/${filename}.csv"
  rm -f "${WORK_DIR}/${filename}.csv"
  export_to_csv "globaltrust" "$csv_file" "\COPY (SELECT i, v, date, strategy_id FROM globaltrust) TO '${csv_file}' WITH (FORMAT CSV, HEADER)"
  split_and_post_csv "$csv_file" 10 "$dune_table_name"
  rm $csv_file

}

_clear_dune_table() {
  local namespace="$1"
  local dune_table_name="$2"

  # Make the HTTP POST request
  response=$(curl --request POST \
    --url https://api.dune.com/api/v1/table/${namespace}/${dune_table_name}/clear \
    --header "X-DUNE-API-KEY: ${DUNE_API_KEY}" \
    --header 'Content-Type: application/json' \
    -w "%{http_code}")

  # Extract the HTTP code from the response
  http_code="${response: -3}"
  response_body="${response::-3}"

  # Log the response and check for successful upload
  log "HTTP code: $http_code, Body: $response_body"

  if [[ "$http_code" -eq 200 || "$http_code" -eq 201 ]]; then
    log "Successfully cleared ${namespace}.${dune_table_name}"
  else
    log "Failed to clear ${namespace}.${dune_table_name}. HTTP response code: $http_code"
    exit 1
  fi
}

# Main script execution
if [[ $# -eq 0 ]]; then
    echo "Usage: $0 {globaltrust|globaltrust_config|localtrust|channel_rank|insert_globaltrust_to_dune|insert_channel_rank_to_dune}"
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
    channel_rank)
        process_channel_rank
        ;;
    insert_globaltrust_to_dune_v2)
        insert_globaltrust_to_dune_v2
        ;;
    insert_channel_rank_to_dune_v2)
        insert_channel_rank_to_dune_v2
        ;;
    insert_globaltrust_to_dune_v3)
        insert_globaltrust_to_dune_v3
        ;;
    insert_channel_rank_to_dune_v3)
        insert_channel_rank_to_dune_v3
        ;;
    create_dune_globaltrust_table)
        create_dune_globaltrust_table $2
        ;;
    *)
        echo "Usage: $0 {globaltrust|globaltrust_config|localtrust|channel_rank|insert_globaltrust_to_dune|insert_channel_rank_to_dune}"
        exit 1
        ;;
esac

# Switch back to the original GCP account
# switch_back_gcp_account

log "All jobs completed!"
