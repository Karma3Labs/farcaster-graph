#!/bin/bash

set -e

# Function to log messages with a timestamp
log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1"
}

# Source the environment variables from the .env file
if [ -f .env ]; then
    source .env
else
    log_message "Error: .env file not found."
    exit 1
fi

# Check if CONFIG and WORK_DIR are set
if [ -z "$NGINX_CONFIG" ] || [ -z "$WORK_DIR" ]; then
    log_message "Error: CONFIG and WORK_DIR environment variables must be set."
    exit 1
fi

log_message "Starting check_certificates.sh script."

# Extract the certificate file paths from the Nginx config file
log_message "Extracting certificate file paths from the Nginx config file."
CERT_FILES=$(grep -E 'ssl_certificate|ssl_certificate_key' $NGINX_CONFIG | awk '{print $2}' | tr -d ';')

# Flag to indicate if any files were moved
FILES_MOVED=false

# Check and move the files if they exist
for FILE in $CERT_FILES; do
    FILE_NAME=$(basename $FILE)
    DIR_NAME=$(dirname $FILE)
    if [ -f ${WORK_DIR}/${FILE_NAME} ]; then
        log_message "Moving ${WORK_DIR}/${FILE_NAME} to $FILE."
        sudo mkdir -p $DIR_NAME
        sudo mv ${WORK_DIR}/${FILE_NAME} $FILE
        FILES_MOVED=true
    else
        log_message "File ${WORK_DIR}/${FILE_NAME} not found."
    fi
done

# Reload Nginx if any files were moved
if [ "$FILES_MOVED" = true ]; then
    log_message "Files moved. Reloading Nginx."
    sudo nginx -s reload
else
    log_message "No files moved. Nginx reload not required."
fi

# Clean up the *.pem files from the work directory
log_message "Cleaning up .pem files from the work directory."
rm -f ${WORK_DIR}/*.pem

log_message "Script completed."
