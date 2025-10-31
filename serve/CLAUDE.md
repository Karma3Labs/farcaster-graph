# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a FastAPI-based service that provides reputation graphs based on social interactions on the Farcaster Protocol. It serves graph-based rankings, personalized scores, and social network metadata through REST APIs.

## Architecture

### Core Components

- **FastAPI Application** (`app/main.py`): Main application with CORS, telemetry, and multiple routers
- **Graph Models**: Pre-computed engagement and the following graphs stored as pickled pandas DataFrames and igraph objects
- **Database Layer**: AsyncPG connection pool for PostgreSQL queries (Farcaster data)
- **EigenTrust Integration**: External Go service for trust computations (`GO_EIGENTRUST_URL`)
- **Caching**: Multi-level caching with memoization and optional disk cache (cashews)

### Key Routers

- `graph_router`: BFS traversal of social graphs (engagement/following)
- `localtrust_router`: Personalized trust scores using EigenTrust
- `globaltrust_router`: Global reputation rankings
- `metadata_router`: Handle/address resolution
- `channel_router`, `cast_router`, `user_router`: Content and user endpoints
- `token_router`, `frame_router`: Token and frame-specific endpoints

### Graph Loading

Graphs are loaded from pickle files at startup:
- "Engagement" graph: `ENGAGEMENT_GRAPH_PATH_PREFIX` + `_df.pkl` / `_ig.pkl`
- "Following" graph: `FOLLOW_GRAPH_PATH_PREFIX` + `_df.pkl` / `_ig.pkl`
- 90-day graph: `NINETYDAYS_GRAPH_PATH_PREFIX` + `_df.pkl` / `_ig.pkl`

## Development Commands

### Setup
```bash
# Install dependencies (using Poetry)
poetry install

# Or with uv (preferred)
uv sync

# Copy and configure environment
cp .env.sample .env
# Edit .env with database credentials and graph paths
```

### Running the Service
```bash
# Development with auto-reload
uvicorn app.main:app --reload

# Production
uvicorn app.main:app --host 0.0.0.0 --port 8080
```

### Code Quality
```bash
# Format and lint code
./scripts/lint.sh

# Or manually:
isort --profile=black .
black .

# SQL linting
sqlfluff lint --dialect postgres app/
```

### Testing
```bash
# API documentation and testing
# Visit http://localhost:8000/docs for Swagger UI
```

## Key Configuration

Environment variables (`.env` file):
- `DB_*`: PostgreSQL connection for Farcaster data
- `GO_EIGENTRUST_URL`: EigenTrust service endpoint
- `*_GRAPH_PATH_PREFIX`: Paths to graph pickle files
- `EIGENTRUST_*`: Algorithm parameters (alpha, epsilon, max_iter)
- `LOG_LEVEL`, `LOG_LEVEL_CORE`: Logging configuration

## Database Schema Notes

The service expects PostgreSQL with Farcaster protocol data including:
- `k3l_cast_action`: Cast interactions
- `k3l_user_data`: User metadata  
- `k3l_links`: Follow relationships
- `k3l_rank`: Global rankings
- `k3l_channel_rewards_config`: Channel configuration flags (is_ranked, is_points, is_tokens)
- Various materialized views for aggregations

## Performance Considerations

- Uses pandas with performance extensions (`USE_PANDAS_PERF`)
- Connection pooling with configurable size (`POSTGRES_POOL_SIZE`)
- Async operations throughout with asyncpg
- Memory-intensive graph operations monitored via `utils.log_memusage()`
- Caching at multiple levels (memoization, disk cache)

## Common Tasks

### Adding New Endpoints
1. Create router in `app/routers/`
2. Define models in `app/models/`
3. Register router in `app/main.py`
4. Add database queries to `app/dependencies/db_utils.py` if needed

### Recently Added Endpoints
- `GET /channels/config/{channel}`: Returns channel configuration flags (is_ranked, is_points, is_tokens) from k3l_channel_rewards_config table

### Updating Graph Data
1. Generate new graph artifacts via pipeline (../pipeline)
2. Update graph path prefixes in `.env`
3. Restart service to reload graphs

### Monitoring
- Prometheus metrics exposed via PrometheusMiddleware
- OpenTelemetry instrumentation available
- Health check endpoint at root `/`