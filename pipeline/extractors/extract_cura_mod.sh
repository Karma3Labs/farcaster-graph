#!/bin/bash

while getopts w:v:c: flag
do
    case "${flag}" in
        w) WORK_DIR=${OPTARG};;
        v) VENV=${OPTARG};;
        c) CSV_FILE=${OPTARG};;
    esac
done

if [ -z "$VENV" ]  || [ -z "$WORK_DIR" ] || [ -z "$CSV_FILE" ]; then
  echo "Usage:   $0 -w [work_dir] -v [venv] -c [csv_file] "
  echo ""
  echo "Example: $0 -w . -v /home/ubuntu/farcaster-graph/publisher/.venv -c channels/Top_Channels.csv"
  echo ""
  echo "Params:"
  echo "  [work_dir]  The working directory to read .env file and execute scripts from."
  echo "  [venv]      The path where a python3 virtualenv has been created."
  echo "  [csv_file]  The path where a csv file has list of top channel ids"
  echo ""
  exit
fi

set -e
set -o pipefail 

# Setup environment variables
echo "Setting up environment variables"
source $WORK_DIR/.env

# Activate
echo "Activating Python 3.12 environment"
source $VENV/bin/activate

# Install
echo "Installing requirements"
#pip install -r requirements.txt

# Run
echo "Running cura channel mod data extractor with flags $CSV_FILE"
/usr/bin/env python3 -m extractors.cura_mod_extractor -c "$CSV_FILE"   

if [ $? -ne 0 ]; then
  echo "Failed to run script"
  exit 1
fi

# Teardown
echo "Deactivating Python 3.12 environment"
deactivate
