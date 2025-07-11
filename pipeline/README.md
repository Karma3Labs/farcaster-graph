# fcgraph-pipeline

## Prerequisites
1. Install [psql](https://www.timescale.com/blog/how-to-install-psql-on-mac-ubuntu-debian-windows/) on your local machine.
2. Run an instance of Postgres DB with data from Farcaster (installed locally or on a remote server)
3. Install [Python 3.12](https://www.python.org/downloads/) or higher.
   * On Ubuntu, you can use the system Python as long as it's 3.12 or higher,
     but make sure its optional `venv` module is available:
     ```shell
     # See if you're using system Python (/usr/bin/python3)
     which python3
     # Check the version, must be 3.12+
     python3 -V
     # Install venv module if missing
     python3 -m venv --help > /dev/null || sudo apt-get install --yes python3-venv
     ```
4. Create a Python [virtualenv](https://docs.python.org/3/library/venv.html) in this directory (`pipelines/`)
   and install requirements:
   ```shell
   python3 -m venv .venv
   .venv/bin/pip install -r requirements.txt -r requirements-dev.txt
   ```
5. Copy/rename the `.env.sample` file into `.env` and update the details of the Postgres DB from step 2.

## Run a pipeline script
```shell
(source .venv/bin/activate && /bin/sh run_pipeline.sh -w . -o /tmp/fc_graph)
```
(Replace `run_pipeline.sh` and its arguments with one of the real pipeline scripts.)