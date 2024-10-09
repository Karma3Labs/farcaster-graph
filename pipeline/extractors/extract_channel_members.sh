#!/bin/bash

while getopts w:v:c:s:d flag
do
    case "${flag}" in
        w) WORK_DIR=${OPTARG};;
        v) VENV=${OPTARG};;
        c) CSV_FILE=${OPTARG};;
        s) SCOPE=${OPTARG};;
        d) DAEMON_FLAG="-d";;
    esac
done

if [ -z "$SCOPE" ] || [ -z "$CSV_FILE" ] || [ -z "$VENV" ]  || [ -z "$WORK_DIR" ]; then
  echo "Usage:   $0 -w [work_dir] -v [venv] -s [scope] -c [csv_file] "
  echo "Daemon Usage:   $0 -w [work_dir] -v [venv] -s [scope] -c [csv_file] -d "
  echo ""
  echo "Example: $0 -w . -v /home/ubuntu/farcaster-graph/publisher/.venv -c ./Top_Channels.csv -s top"
  echo "         $0 -w . -v /home/ubuntu/farcaster-graph/publisher/.venv -c ./Top_Channels.csv -s all"
  echo "         $0 -w . -v /home/ubuntu/farcaster-graph/publisher/.venv -c ./Top_Channels.csv -s all -d"
  echo ""
  echo "Params:"
  echo "  [work_dir]  The working directory to read .env file and execute scripts from."
  echo "  [venv]      The path where a python3 virtualenv has been created."
  echo "  [scope]     The scope of channels to import: top or all"
  echo "  [csv_file]  The path where a csv file has list of top channel ids"
  echo "  [d]         (optional) to run the script in daemon mode"
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
pip install -r requirements.txt

# Run
echo "Running channel members import with flags $CSV_FILE $SCOPE $DAEMON_FLAG"
/usr/bin/env python3 -m extractors.main_channel_members -c $CSV_FILE -s $SCOPE $DAEMON_FLAG

# Teardown
echo "Deactivating Python 3.12 environment"
deactivate
