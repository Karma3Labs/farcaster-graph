#!/bin/bash

# Script to sync FCM registration FIDs with webhook endpoint
# Usage: ./run_fcm_webhook_sync.sh [-w working_dir] [-v venv_dir]

set -e

WORKING_DIR=${PWD}
VENV_DIR=".venv"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -w|--working-dir)
            WORKING_DIR="$2"
            shift # past argument
            shift # past value
            ;;
        -v|--venv-dir)
            VENV_DIR="$2"
            shift # past argument
            shift # past value
            ;;
        -h|--help)
            echo "Usage: $0 [-w working_dir] [-v venv_dir]"
            echo "  -w, --working-dir    Working directory (default: current directory)"
            echo "  -v, --venv-dir       Virtual environment directory (default: .venv)"
            exit 0
            ;;
        -*|--*)
            echo "Unknown option $1"
            exit 1
            ;;
        *)
            echo "Unknown argument $1"
            exit 1
            ;;
    esac
done

echo "============================================="
echo "FCM Webhook Sync Started"
echo "Working Directory: ${WORKING_DIR}"
echo "Virtual Environment: ${VENV_DIR}"
echo "Timestamp: $(date)"
echo "============================================="

# Change to working directory
cd "${WORKING_DIR}"

# Activate virtual environment
if [ -f "${VENV_DIR}/bin/activate" ]; then
    echo "Activating virtual environment: ${VENV_DIR}"
    source "${VENV_DIR}/bin/activate"
else
    echo "Virtual environment not found at ${VENV_DIR}/bin/activate"
    exit 1
fi

# Run the FCM webhook sync
echo "Running FCM webhook sync..."
python -m fcm.webhook_sync

echo "============================================="
echo "FCM Webhook Sync Completed Successfully"
echo "Timestamp: $(date)"
echo "============================================="