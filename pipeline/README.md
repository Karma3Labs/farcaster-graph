# Pre-requisites
1. Install [psql](https://www.timescale.com/blog/how-to-install-psql-on-mac-ubuntu-debian-windows/) on your local machine.
2. Run an instance of Postgres DB with data from Farcaster (installed locally or on a remote server)  - for example, a database instance of [Farcaster Replicator](https://github.com/farcasterxyz/hub-monorepo/tree/main/apps/replicator)
3. Install [Python 3.12](https://www.python.org/downloads/)
4. Create a Python [virtualenv](https://docs.python.org/3/library/venv.html) somewhere on your machine - for example,`python3 -m venv .venv` will create a virtualenv in your current directory.
5. Copy/rename the `.env.sample` file into `.env` and update the details of the Postgres DB from step 2 and the virutalenv from step 3.

# Run the pipeline
`sh run_pipeline.sh -w . -o /tmp/fc_graph`