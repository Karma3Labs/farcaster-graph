FROM apache/airflow:latest

COPY . /pipeline
WORKDIR /pipeline

RUN source /pipeline/.env
# RUN python3 -m venv .venv
RUN pip install --upgrade pip

RUN pip install -r requirements.txt

# RUN source /pipeline/bin/activate


# COPY requirements.txt /requirements.txt
# RUN pip install --user --upgrade pip
# RUN pip install --no-cache-dir --user -r /requirements.txt
