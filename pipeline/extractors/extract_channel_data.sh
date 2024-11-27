#!/bin/bash

while getopts w:v:c:s:d flag
do
    case "${flag}" in
        w) WORK_DIR=${OPTARG};;
        v) VENV=${OPTARG};;
    esac
done

if [ -z "$VENV" ]  || [ -z "$WORK_DIR" ]; then
  echo "Usage:   $0 -w [work_dir] -v [venv] "
  echo ""
  echo "Example: $0 -w . -v /home/ubuntu/farcaster-graph/publisher/.venv "
  echo ""
  echo "Params:"
  echo "  [work_dir]  The working directory to read .env file and execute scripts from."
  echo "  [venv]      The path where a python3 virtualenv has been created."
  echo ""
  exit
fi

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
echo "Running channel data import"
/usr/bin/env python3 -m extractors.main_channel_data  

# Teardown
echo "Deactivating Python 3.12 environment"
deactivate
