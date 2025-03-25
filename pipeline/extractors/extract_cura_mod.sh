#!/bin/bash

while getopts w:v:rd flag
do
    case "${flag}" in
        w) WORK_DIR=${OPTARG};;
        v) VENV=${OPTARG};;
        r) RUN_FLAG="--run";;
        d) DRYRUN_FLAG="--dry-run";;
    esac
done

if [ -z "$VENV" ]  || [ -z "$WORK_DIR" ] || [ -z "$RUN_FLAG" ]; then
  echo "Usage:   $0 -w [work_dir] -v [venv] -r -d "
  echo ""
  echo "Example: $0 -w . -v /home/ubuntu/farcaster-graph/publisher/.venv -r"
  echo "Example: $0 -w . -v /home/ubuntu/farcaster-graph/publisher/.venv -r -d"
  echo ""
  echo "Params:"
  echo "  [work_dir]  The working directory to read .env file and execute scripts from."
  echo "  [venv]      The path where a python3 virtualenv has been created."
  echo "  [run] Flag to run the script."
  echo "  [dryrun] Flag to run the script in dry-run mode."
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
echo "Running cura channel mod data extractor with flags"
/usr/bin/env python3 -m extractors.cura_mod_extractor $RUN_FLAG $DRYRUN_FLAG

if [ $? -ne 0 ]; then
  echo "Failed to run script"
  exit 1
fi

# Teardown
echo "Deactivating Python 3.12 environment"
deactivate
