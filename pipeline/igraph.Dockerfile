# FROM python:3.12-alpine
# not taking the alpine route because packages like psutil don't install without gcc
FROM python:3.12-slim

RUN pip install --upgrade pip

WORKDIR /server

# don't copy code yet otherwise docker layers will get invalidated every code push
COPY ./requirements.txt /server

RUN python -m ensurepip --upgrade
RUN python -m pip install --no-cache-dir --upgrade -r requirements.txt

# copy rest of the code
COPY . /server

CMD ["uvicorn", "graph.serve_igraph:app", "--host", "0.0.0.0", "--port", "8000", "--timeout-keep-alive", "300"]