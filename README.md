# Farcaster Graph

EigenTrust-based reputation and ranking for the [Farcaster](https://www.farcaster.xyz/) social network, built by [Karma3Labs](https://karma3labs.com).

Computes trust scores, personalized rankings, and social graph queries from on-chain Farcaster data using the [EigenTrust](https://en.wikipedia.org/wiki/EigenTrust) algorithm.

## Project Structure

```
farcaster-graph/
├── serve/       # FastAPI server — REST API for querying graphs, scores, and metadata
├── pipeline/    # Airflow DAGs — ETL pipeline for graph generation and trust computation
├── notebooks/   # Jupyter notebooks — data exploration and prototyping
├── sql/         # PostgreSQL schema definitions and migrations
└── scripts/     # Deployment and utility scripts
```

Each sub-project has its own README with detailed setup instructions.

## Prerequisites

- [Python 3.12+](https://www.python.org/downloads/)
- [PostgreSQL](https://www.postgresql.org/) with Farcaster data
- [go-eigentrust](https://github.com/Karma3Labs/go-eigentrust) — EigenTrust computation service
- [Poetry](https://python-poetry.org) (for `serve`) or pip (for `pipeline`)
- [Docker](https://docs.docker.com/get-docker/) (optional, for containerized setup)

## Quick Start: Serve (API Server)

The fastest way to get the API running locally using pre-built sample graphs:

```bash
cd serve

# Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
poetry install

# Configure environment (sample graphs are pre-configured in .env.sample)
cp .env.sample .env

# Start the development server
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`. Swagger docs are at `http://localhost:8000/docs`.

> **Note:** The sample `.env` points to pre-built graphs in `serve/samples/` so you can explore the API without running the full pipeline. For production use, you'll need a PostgreSQL instance with Farcaster data and a running go-eigentrust service.

### Docker

```bash
cd serve
docker compose up
```

## Quick Start: Pipeline (Airflow)

The pipeline generates graphs and computes trust scores on a schedule via Apache Airflow:

```bash
cd pipeline

# Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt -r requirements-dev.txt

# Configure environment
cp .env.sample .env
# Edit .env with your PostgreSQL and go-eigentrust connection details

# Run the graph pipeline manually
/bin/sh run_graph_pipeline.sh -w . -o /tmp/fc_graph
```

### Docker (Airflow)

```bash
cd pipeline
docker compose up
```

Airflow UI will be at `http://localhost:8080`.

## Quick Start: Notebooks

```bash
cd notebooks
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
jupyter notebook
```

## Configuration

Both `serve` and `pipeline` use `.env` files for configuration. See the `.env.sample` in each directory for all available options.

**Key environment variables (serve):**

| Variable | Description | Default |
|---|---|---|
| `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USERNAME`, `DB_PASSWORD` | PostgreSQL connection | — |
| `GO_EIGENTRUST_URL` | go-eigentrust service URL | `http://localhost:8080` |
| `FOLLOW_GRAPH_PATH_PREFIX` | Path prefix for follow graph pickle files | `./samples/fc_following_fid` |
| `ENGAGEMENT_GRAPH_PATH_PREFIX` | Path prefix for engagement graph pickle files | `./samples/fc_engagement_fid` |
| `NINETY_DAYS_GRAPH_PATH_PREFIX` | Path prefix for 90-day graph pickle files | `./samples/fc_90dv3_fid` |
| `EIGENTRUST_ALPHA` | EigenTrust damping factor | `0.5` |

## API Overview

The serve component exposes these endpoint groups (see Swagger UI at `/docs` for full details):

| Group | Prefix | Description |
|---|---|---|
| Graph | `/graph` | BFS traversal of engagement and following graphs |
| Personalized Scores | `/scores/personalized` | EigenTrust-based personalized rankings |
| Global Scores | `/scores/global` | Global reputation rankings |
| Metadata | `/metadata` | Handle/address resolution |
| Channels | `/channels` | Channel rankings, feeds, and token rewards |
| Casts | `/casts` | Cast details and engagement metrics |
| Tokens | `/tokens` | Token balances, feeds, and leaderboards |
| Users | `/users` | User metadata |
| Links | `/links` | Direct follow relationships |

## Development

```bash
# Serve — lint and format
cd serve
isort --profile=black .
black .

# Pipeline — lint and format
cd pipeline
ruff check --fix .
ruff format .
```

## License

This project is licensed under the MIT License — see [LICENSE](LICENSE) for details.
