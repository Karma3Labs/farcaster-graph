FROM apache/airflow:latest
# Switch to root to install additional packages
USER root

# Fix potential permission issues and update package list
RUN chmod -R a+rX /var/lib/apt/lists /var/cache/apt/archives && \
  apt-get clean && \
  rm -rf /var/lib/apt/lists/* && \
  mkdir -p /var/lib/apt/lists/partial && \
  apt-get update && \
  apt-get -y install zip

# Switch back to the airflow user
USER airflow

# Set working directory
WORKDIR /pipeline

# Copy only the necessary files for initial setup
COPY requirements.txt /pipeline/requirements.txt
COPY .env /pipeline/.env

# Source environment variables
RUN /bin/bash -c "source /pipeline/.env"

RUN pip install --upgrade pip

RUN pip install -r /pipeline/requirements.txt

RUN curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
RUN unzip awscliv2.zip

USER root
RUN ./aws/install
USER airflow
