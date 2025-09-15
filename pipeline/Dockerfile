FROM apache/airflow:2.10.3
# Switch to root to install additional packages
USER root

# Fix potential permission issues and update package list
RUN chmod -R a+rX /var/lib/apt/lists /var/cache/apt/archives && \
  apt-get clean && \
  rm -rf /var/lib/apt/lists/* && \
  mkdir -p /var/lib/apt/lists/partial && \
  apt-get update && \
  apt-get -y install zip

RUN curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
RUN unzip awscliv2.zip

RUN ./aws/install

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

# Use Airflow constraints file for compatible package versions
RUN pip install -r /pipeline/requirements.txt --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-2.10.3/constraints-3.12.txt"
RUN pip install apache-airflow-providers-pagerduty==3.7.2 discord-webhook==1.3.1 apache-airflow-providers-ssh==3.11.2 --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-2.10.3/constraints-3.12.txt"


