#!/bin/bash

while getopts w:v:t:s:r: flag
do
    case "${flag}" in
        w) WORK_DIR=${OPTARG};;
        v) VENV=${OPTARG};;
        t) TASK=${OPTARG};;
        s) SCOPE=${OPTARG};;
        r) REASON=${OPTARG};;
    esac
done

if [ -z "$WORK_DIR" ] || [ -z "$VENV" ] || [ -z "$TASK" ]; then
  echo "Usage:   $0 -w [work_dir] -v [venv] -t [task]"
  echo "Usage:   $0 -w [work_dir] -v [venv] -t [task] -s [scope] -r [reason]"
  echo ""
  echo "Example: $0 -w . -v /home/ubuntu/venvs/fc-graph-env3/ -t prep -s weekly -r reason"
  echo "         $0 -w . -v /home/ubuntu/venvs/fc-graph-env3/ -t distrib"
  echo "         $0 -w . -v /home/ubuntu/venvs/fc-graph-env3/ -t verify"
  echo ""
  echo "Params:"
  echo "  [work_dir] The working directory to read .env file and execute scripts from."
  echo "  [venv] The path where a python3 virtualenv has been created."
  echo "  [task] The task to perform: prep or distrib or verify."
  echo "  [scope] The scope of channels to import: airdrop or daily calculation."
  echo "  [reason] The reason for the distribution."
  echo ""
  exit
fi

if [ "$TASK" = "prep" ]; then
  if [ -z "$SCOPE" ] || [ -z "$REASON" ]; then
    echo "Please specify -s (scope) and -r (reason) for the prep task."
    exit 1
  fi
fi

source $WORK_DIR/.env

# set -x
set -e
set -o pipefail

function log() {
  echo "`date` - $1"
}

source $VENV/bin/activate
#pip install -r requirements.txt
if [ "$TASK" = "prep" ]; then
    python3 -m channels.main_tokens -t prep -s "$SCOPE" -r "$REASON"
    deactivate
elif [ "$TASK" = "distrib" ]; then
    python3 -m channels.main_tokens -t distrib
    deactivate    
elif [ "$TASK" = "verify" ]; then      
    python3 -m channels.main_tokens -t verify
    deactivate
else
    echo "Invalid task specified. Use 'prep', 'distrib' or 'verify'."
    exit 1    
fi
