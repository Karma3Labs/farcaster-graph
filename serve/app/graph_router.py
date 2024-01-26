from fastapi import APIRouter, Query
from loguru import logger


router = APIRouter(tags=["eoas"])

@router.get("/neighbors/engagement")
async def get_neighbors_engagement(addresses: list[str]):
  logger.info(addresses)
  return {"addresses": addresses}