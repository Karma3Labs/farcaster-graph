FROM apache/airflow:2.10.3
# Switch to root to install additional packages
USER root

RUN \
	apt-get update && \
	apt-get -y install zip && \
	mkdir -p aws-installer && \
	curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "aws-installer/awscliv2.zip" && \
	(cd aws-installer && unzip awscliv2.zip && ./aws/install) && \
	rm -rf aws-installer

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
RUN pip install apache-airflow-providers-pagerduty==3.7.2 discord-webhook==1.3.1 apache-airflow-providers-ssh==3.11.2


