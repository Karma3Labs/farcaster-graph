# FROM python:3.12-alpine
# not taking the alpine route because packages like psutil don't install without gcc
FROM python:3.12-slim

RUN pip install --upgrade pip

RUN pip install poetry

# single app container
# no need to create virtual envs
# install dependencies into the systems python environment 
ENV POETRY_VERSION=1.7.1 \
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_CREATE=false

WORKDIR /code

COPY pyproject.toml poetry.lock ./
COPY README.md ./

# we don't want to rebuild all the layers after every app code change
# ignore app code for now
# uncomment the next line if we start using dev/test specific dependencies
# RUN poetry install --without dev,test --no-root
RUN poetry install --no-root

COPY ./app /code/app
COPY ./static /code/static
COPY .env.docker ./.env

# install app code, this is the last image layer and has to be rebuilt
# uncomment the next line if we start using dev/test specific dependencies
# RUN poetry install --without dev,test
RUN poetry install --no-root

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
