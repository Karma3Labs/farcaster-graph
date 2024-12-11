#!/bin/bash

while getopts w:v:c:s:j:t:d flag
do
    case "${flag}" in
        w) WORK_DIR=${OPTARG};;
        v) VENV=${OPTARG};;
        c) CSV_FILE=${OPTARG};;
        s) SCOPE=${OPTARG};;
        j) JOB_TYPE=${OPTARG};;
        t) TASK=${OPTARG};;
        d) DAEMON_FLAG="-d";;
    esac
done

if [ -z "$TASK" ] || [ -z "$JOB_TYPE" ] || [ -z "$VENV" ]  || [ -z "$WORK_DIR" ]; then
  echo "Prep Usage: $0 -o prep -w [work_dir] -v [venv] -j [job_type] "
  echo "Fetch Usage:   $0 -o fetch -w [work_dir] -v [venv] -s [scope] -j [job_type] -c [csv_file] "
  echo "Daemon Usage:   $0 -o fetch -w [work_dir] -v [venv] -s [scope] -j [job_type] -c [csv_file] -d "
  echo "Cleanup Usage: $0 -o cleanup -w [work_dir] -v [venv] -j [job_type] "
  echo ""
  echo "Example: $0 -o prep -w . -v /home/ubuntu/farcaster-graph/publisher/.venv -j followers"
  echo "         $0 -o fetch-w . -v /home/ubuntu/farcaster-graph/publisher/.venv -c ./Top_Channels.csv -s top -j followers"
  echo "         $0 -o fetch-w . -v /home/ubuntu/farcaster-graph/publisher/.venv -c ./Top_Channels.csv -s all -j followers"
  echo "         $0 -o fetch -w . -v /home/ubuntu/farcaster-graph/publisher/.venv -c ./Top_Channels.csv -s all -d"
  echo "         $0 -o cleanup -w . -v /home/ubuntu/farcaster-graph/publisher/.venv -j followers"
  echo ""
  echo "Params:"
  echo "  [task] The task to perform: prep or fetch or cleanup"
  echo "  [work_dir]  The working directory to read .env file and execute scripts from."
  echo "  [venv]      The path where a python3 virtualenv has been created."
  echo "  [scope]     The scope of channels to import: top or all"
  echo "  [job_type]  The type of job to run: followers or members"
  echo "  [csv_file]  The path where a csv file has list of top channel ids"
  echo "  [d]         (optional) to run the script in daemon mode"
  echo ""
  exit
fi

if [ "$TASK" = "fetch" ]; then
  if [ -z "$SCOPE" ] || [ -z "$CSV_FILE" ]; then
    echo "Please specify -z (scope) and -c (csv_file) for the fetch task."
    exit 1
  fi
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
if [ "$TASK" = "prep" ]; then
  echo "Running prep with flags $JOB_TYPE"
  /usr/bin/env python3 -m extractors.main_channel_fids prep -j $JOB_TYPE
elif [ "$TASK" = "fetch" ]; then
  echo "Running fetch with flags $CSV_FILE $SCOPE $JOB_TYPE $DAEMON_FLAG"
  /usr/bin/env python3 -m extractors.main_channel_fids fetch -c $CSV_FILE -s $SCOPE -j $JOB_TYPE $DAEMON_FLAG 
elif [ "$TASK" = "cleanup" ]; then
  echo "Running cleanup with flags $JOB_TYPE"
  /usr/bin/env python3 -m extractors.main_channel_fids cleanup -j $JOB_TYPE
else
  echo "Invalid task specified. Use 'prep' or 'fetch' or 'cleanup'."
  exit 1
fi

if [ $? -ne 0 ]; then
  echo "Failed to run script"
  exit 1
fi

# Teardown
echo "Deactivating Python 3.12 environment"
deactivate
