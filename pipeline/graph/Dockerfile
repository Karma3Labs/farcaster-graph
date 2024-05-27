# FROM python:3.12-alpine
# not taking the alpine route because packages like psutil don't install without gcc
FROM python:3.12-slim

RUN pip install --upgrade pip

WORKDIR /server

COPY . /server
RUN python -m ensurepip --upgrade
RUN python -m pip install --no-cache-dir --upgrade -r requirements.txt

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]