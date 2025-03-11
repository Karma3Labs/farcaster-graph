#!/bin/bash
set -e

# Directory where the data will be stored
DATA_DIR="/var/lib/postgresql/data"
CONF_DIR="/var/lib/postgresql/conf"

# Ensure environment variables are set
if [ -z "$PRIMARY_HOST" ] || [ -z "$PRIMARY_PORT" ] || [ -z "$PRIMARY_USER" ] || [ -z "$PRIMARY_PASSWORD" ] || [ -z "$PRIMARY_SLOT_NAME" ]; then
    echo "Error: Environment variables not set correctly."
    exit 1
fi

# Prepare configuration directory (outside of data directory)
mkdir -p $CONF_DIR
cp /usr/local/bin/postgresql.conf $CONF_DIR/postgresql.conf
cp /usr/local/bin/pg_hba.conf $CONF_DIR/pg_hba.conf

# Check if the data directory is empty
if [ "$(ls -A $DATA_DIR)" ]; then
    echo "Data directory is not empty."
else
    echo "Data directory is empty, setting up .pgpass file..."
    echo "$PRIMARY_HOST:$PRIMARY_PORT:*:$PRIMARY_USER:$PRIMARY_PASSWORD" > /root/.pgpass
    chmod 600 /root/.pgpass

    echo "Initiating base backup..."
    pg_config --version
    pg_basebackup -h $PRIMARY_HOST -p $PRIMARY_PORT -D $DATA_DIR -U $PRIMARY_USER -vP -w -Xs -R -S $PRIMARY_SLOT_NAME

    # Set the correct permissions
    chmod 0700 $DATA_DIR
    chown -R postgres:postgres $DATA_DIR
    
    # Move the customized postgresql.conf back to the data directory
    mv $CONF_DIR/postgresql.conf $DATA_DIR/postgresql.conf
    mv $CONF_DIR/pg_hba.conf $DATA_DIR/pg_hba.conf

    echo "Backup and configuration complete. Starting PostgreSQL in standby mode."
fi


# Start PostgreSQL using sudo
exec sudo -u postgres postgres -D $DATA_DIR
