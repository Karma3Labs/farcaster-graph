#!/usr/bin/env bash

# Token distribution runner script
# Usage: ./run_token_distribution.sh [-w working_dir] [-v venv_dir] [-t task]

set -e

# Defaults
WORKING_DIR="."
VENV_DIR=".venv"
TASK="process"  # process or verify

# Parse arguments
while getopts "w:v:t:h" opt; do
    case $opt in
        w) WORKING_DIR="$OPTARG";;
        v) VENV_DIR="$OPTARG";;
        t) TASK="$OPTARG";;
        h) echo "Usage: $0 [-w working_dir] [-v venv_dir] [-t task]"
           echo "Tasks: process (default), verify"
           exit 0;;
        *) echo "Invalid option. Use -h for help."
           exit 1;;
    esac
done

# Change to working directory
cd "$WORKING_DIR"

# Activate virtual environment
if [ -d "$VENV_DIR" ]; then
    echo "Activating virtual environment: $VENV_DIR"
    source "$VENV_DIR/bin/activate"
else
    echo "Virtual environment not found: $VENV_DIR"
    exit 1
fi

# Set Python path
export PYTHONPATH="$WORKING_DIR:$PYTHONPATH"

echo "Running token distribution task: $TASK"
echo "Working directory: $(pwd)"
echo "Python: $(which python)"

# Run the appropriate task
case $TASK in
    process)
        echo "Processing pending token distributions..."
        python -c "
from k3l.fcgraph.pipeline.token_distribution_operator import run_token_distribution
run_token_distribution()
"
        ;;
    verify)
        echo "Verifying token distributions..."
        python -c "
from k3l.fcgraph.pipeline.token_distribution_operator import verify_distributions
verify_distributions()
"
        ;;
    *)
        echo "Unknown task: $TASK"
        echo "Valid tasks: process, verify"
        exit 1
        ;;
esac

echo "Token distribution task completed: $TASK"