FROM apache/airflow:latest

# Set working directory
WORKDIR /pipeline

# Copy only the necessary files for initial setup
COPY requirements.txt /pipeline/requirements.txt
COPY .env /pipeline/.env

# Source environment variables
RUN /bin/bash -c "source /pipeline/.env"

# RUN python3 -m venv .venv
RUN pip install --upgrade pip

RUN pip install -r /pipeline/requirements.txt

# RUN source /pipeline/bin/activate


# COPY requirements.txt /requirements.txt
# RUN pip install --user --upgrade pip
# RUN pip install --no-cache-dir --user -r /requirements.txt
