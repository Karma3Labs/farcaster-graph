# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Farcaster social network graph processing pipeline that calculates trust metrics using EigenTrust algorithms and powers the Cura platform APIs.

## Development Commands

### Setup
```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt -r requirements-dev.txt
```

### Linting and Formatting
```bash
# Recommended: Use the script that runs all linters
./scripts/lint.sh

# Individual linters
ruff check --fix .
ruff format .
sqlfluff lint
```

### Docker Services
```bash
docker-compose up  # Start Airflow cluster with all services
```

## Architecture Overview

### Core Pipeline Flow
1. **Data Extraction** (`/extractors/`) - Fetches Farcaster casts, channels, and interactions
2. **Graph Generation** (`/graph/`) - Builds social graphs from interaction data
3. **Trust Computation** (`/globaltrust/`) - Calculates EigenTrust scores via Go service
4. **Channel Processing** (`/channels/`) - Rankings, token distributions, metrics
5. **API Serving** - FastAPI endpoints for graph data access

### Key Directories
- `/dags/` - Airflow DAG definitions for orchestrated workflows
- `/k3l/fcgraph/pipeline/` - Core package module with CLI and utilities
- `/schema/` - Database schema definitions and migrations
- `/config.py` - Central configuration using Pydantic settings

### Database Connections
The system uses multiple PostgreSQL instances configured via environment variables:
- Primary database for read/write operations
- Replica for read-heavy workloads
- Sandbox for development/testing

### External Dependencies
- **EigenTrust Go Service** - Performs trust calculations
- **Cura Smart Contract Manager** - Blockchain integration
- **Dune Analytics API** - On-chain data retrieval

## Important Patterns

### Data Processing
- Uses pandas/polars for large-scale data manipulation
- Async operations with asyncpg for database queries
- Parquet files for intermediate data storage

### Error Handling
- Use `exc_info=True` when logging exceptions
- Implement proper exception chaining with `raise ... from`

### Airflow DAGs
- Located in `/dags/` directory
- Main EigenTrust pipeline runs every 6 hours
- Use XCom for inter-task communication

### Configuration
- Environment variables loaded via `.env` files
- Settings validated using Pydantic models in `config.py`
- Database connections managed through pgBouncer for pooling

## Testing Approach
The codebase uses pytest but specific test commands should be discovered from existing test files when needed.