import itertools
import time
from typing import Annotated
from typing import Iterable

from fastapi import APIRouter, Depends, Query, HTTPException
from loguru import logger
from asyncpg.pool import Pool

from .config import settings
from .dependencies.db_pool import get_db
from .dependencies.graph import get_engagement_graph
from .models.graph_model import Graph

router = APIRouter(tags=["eoas"])

async def fetch_korder_neighbors(
  addresses: list[str],
  max_degree: Annotated[int, Query(le=5)] = 2,
  max_neighbors: Annotated[int | None, Query(le=1000)] = 100,
  graph: Graph = Depends(get_engagement_graph),        
) -> Iterable :
  try:
    klists = []
    mindist_and_order = 1
    limit = max_neighbors
    while mindist_and_order <= max_degree:
        neighbors = graph.graph.neighborhood(
            addresses, order=mindist_and_order, mode="out", mindist=mindist_and_order
        )
        klists.append(graph.graph.vs[neighbors[0][:limit]]["name"])
        # klists.append([bytes.fromhex(addr[2:]) for addr in graph.graph.vs[neighbors[0][:limit]]["name"]])
        limit = limit - len(neighbors[0])
        if limit <= 0:
            break # we have reached limit of neighbors
        mindist_and_order += 1
    # end of while
    return list(itertools.chain(*klists))
  except ValueError:
    raise HTTPException(status_code=404, detail="Neighbors not found")

@router.get("/neighbors/engagement")
async def get_neighbors_engagement(
  addresses: list[str],
  k: Annotated[int, Query(le=5)] = 2,
  limit: Annotated[int | None, Query(le=1000)] = 100,
  graph: Graph = Depends(get_engagement_graph),
  pool: Pool = Depends(get_db)
):
  logger.info(addresses)
  neighbors = await fetch_korder_neighbors(addresses, k, limit, graph)
  logger.info(neighbors)
  start_time = time.perf_counter()
  sql_query = """
    SELECT 
      '0x'||encode(f1.custody_address,'hex') as i,
      '0x'||encode(f2.custody_address,'hex') as j, 
      lt.v
    FROM localtrust as lt
    INNER JOIN fids as f1 on (f1.fid = cast(lt.i as int8))
    INNER JOIN fids as f2 on (f2.fid = cast(lt.j as int8))
    WHERE 
      strategy_id=3
      AND date=(SELECT max(date) FROM localtrust where strategy_id=3)
      AND 
        '0x' || encode(f1.custody_address, 'hex') = ANY($1::text[])
        -- fids.custody_address = ANY($1::bytea[])
    LIMIT 10
  """
  # Take a connection from the pool.
  async with pool.acquire() as connection:
      # Open a transaction.
      async with connection.transaction():
          with connection.query_logger(logger.trace):
              # Run the query passing the request argument.
              rows = await connection.fetch(
                                        sql_query, 
                                        neighbors, 
                                        # limit, 
                                        timeout=settings.POSTGRES_TIMEOUT_SECS
                                      )
  logger.info(f"query took {time.perf_counter() - start_time} secs")
  return {"result": rows}
