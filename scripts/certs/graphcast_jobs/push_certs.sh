#!/bin/bash

while getopts h: flag
do
	case "${flag}" in
        h) REMOTE_HOST=${OPTARG};;
    esac
done

if [ -z "$REMOTE_HOST" ]; then
	echo "Usage:   $0 -h [remote_host]"
	echo ""
	echo "Example: $0 -h 37.27.108.188"
	echo ""
	echo "Params:"
	echo "  [remote_host]	host to which the pem files have to be copied over to"
	echo""
	exit
fi


# Function to log messages with a timestamp
log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1"
}

# Source the environment variables from the .env file
if [ -f .env ]; then
    log_message "Loading .env file."
    source .env
else
    log_message "Error: .env file not found."
    exit 1
fi

# Check if NGINX_CONFIG, REMOTE_USER, REMOTE_HOST, and REMOTE_DIR are set
if [ -z "$NGINX_CONFIG" ] || [ -z "$REMOTE_USER" ] || [ -z "$REMOTE_DIR" ] || [ -z "$SSH_PRIV_KEY" ]; then
    log_message "Error: NGINX_CONFIG, REMOTE_USER, REMOTE_HOST, REMOTE_DIR and SSH_PRIV_KEY environment variables must be set."
    exit 1
fi

log_message "Starting sync_certificates.sh script."

# Extract the certificate file paths from the Nginx config file
log_message "Extracting certificate file paths from the Nginx config file."
CERT_FILES=$(grep -E 'ssl_certificate|ssl_certificate_key' $NGINX_CONFIG | awk '{print $2}' | tr -d ';')

# SCP the certificate files to the remote server
for FILE in $CERT_FILES; do
    log_message "Transferring $FILE to ${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_DIR}."
    sudo scp -p -i $SSH_PRIV_KEY $FILE ${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_DIR}
done

log_message "Script completed."
