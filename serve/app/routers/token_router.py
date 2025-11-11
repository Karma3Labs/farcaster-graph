import logging
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from typing import Annotated, Optional, Self

from asyncpg import Pool
from eth_typing import ChecksumAddress
from eth_utils import to_bytes, to_checksum_address
from fastapi import APIRouter, Depends, HTTPException, Path, Query
from pydantic import BaseModel, ValidationError, field_validator

from ..dependencies import db_pool, db_utils
from ..dependencies.db_utils import (
    Fip2Token,
    get_all_token_balances,
    get_token_balances,
    search_fip2_tokens,
)
from ..dependencies.token_feed import get_token_feed
from ..models.feed_model import WeightsField

_logger = logging.getLogger(__name__)

router = APIRouter(tags=["Token"])


class Token(BaseModel):
    """
    Token address.

    TODO(ek) - expand to CAIP-19, to add chain ID and stuff.
    """

    address: ChecksumAddress

    @field_validator("address", mode="before")
    @classmethod
    def ensure_address(cls, v):
        try:
            return to_checksum_address(v)
        except Exception:
            raise ValueError(f"Invalid token address: {v!r}")

    @classmethod
    def from_str(cls, v: str) -> Self:
        return cls(address=to_checksum_address(v))


def get_token(token: str = Path(description="ERC20 token address")) -> Token:
    try:
        return Token.from_str(token)
    except ValidationError:
        raise HTTPException(status_code=422, detail=f"Invalid token {token!r}")


@router.get("/balances")
async def get_balances(
    token: Token = Depends(get_token),
    fids: Sequence[int] = Query(..., alias="fid", min_items=1),
    pool: Pool = Depends(db_pool.get_db),
):
    rows = await get_token_balances(to_bytes(hexstr=token.address), fids, pool)
    balances = {fid: value for fid, value in rows}
    return {
        "balances": [
            {"fid": fid, "value": str(int(balances.get(fid, 0)))} for fid in fids
        ]
    }


# ---------------------------------------------------------------------------
# New endpoint: /balances/all – full or top‑N leaderboard
# ---------------------------------------------------------------------------
@router.get("/{token}/balances/all")
async def get_all_balances(  # noqa: D401
    *,
    token: Token = Depends(get_token),
    limit: int | None = Query(
        None,
        gt=0,
        le=10000,
        description="Optional cap on the number of rows (useful for leaderboards)",
    ),
    pool: Pool = Depends(db_pool.get_db),
):
    """Return **all** FID balances for *token*, sorted high→low.

    If `?limit=` is supplied, only the first *N* rows are returned.  This is
    handy when building a public leaderboard (e.g., top‑100 holders).
    """

    try:
        rows = await get_all_token_balances(
            to_bytes(hexstr=token.address), pool=pool, limit=limit
        )
    except Exception as exc:  # pragma: no cover – bubble up DB issues cleanly
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return {
        "balances": [
            {"fid": row["fid"], "value": str(int(row["value"]))} for row in rows
        ]
    }


@router.get("/{token}/leaderboards/trader")
async def get_trader_leaderboard(
    *,
    token: Token = Depends(get_token),
    start_time: datetime | None = Query(
        None,
        description="Minimum action timestamp (default: `end_time` - `duration`",
    ),
    end_time: datetime | None = Query(
        None,
        description="Maximum action timestamp (default: now)",
    ),
    duration: timedelta | None = Query(
        None,
        description="Action duration (default: 1 day)",
    ),
    weights: Annotated[
        WeightsField,
        Query(
            description="action weights, in L*C*R*Y* form (default: `L1C10R5Y1`)",
        ),
    ] = "L1C0R1Y1",
    pool: Pool = Depends(db_pool.get_db),
):
    if end_time is None:
        end_time = datetime.now(tz=UTC)
    if start_time is None:
        if duration is None:
            duration = timedelta(days=1)
        start_time = end_time - duration
    elif duration is not None:
        raise HTTPException(
            status_code=400,
            detail="Cannot specify both `start_time` and `duration`",
        )
    leaderboard = await db_utils.get_trader_leaderboard(
        chain_id=8453,
        token_address=token.address,
        start_time=start_time,
        end_time=end_time,
        global_trust_strategy_id=9,
        weights=weights,
        pool=pool,
    )
    return {"result": leaderboard}


@router.get("/{token}/feed")
async def get_feed(
    *,
    token: Token = Depends(get_token),
    token_symbol: str,
    int_chain_id: int,
    viewer_fid: str,
    cursor: Optional[str] = None,
):
    try:
        return await get_token_feed(
            int_chain_id, token.address, cursor, token_symbol, viewer_fid
        )
    except Exception as exc:  # pragma: no cover – bubble up DB issues cleanly
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/trending-fip2")
async def get_trending_fip2(
    *,
    chain_id: int = Query(8453, description="chain ID"),
    start_time: datetime | None = Query(
        None,
        description="Minimum action timestamp (default: `end_time` - `duration`",
    ),
    end_time: datetime | None = Query(
        None,
        description="Maximum action timestamp (default: now)",
    ),
    duration: timedelta | None = Query(
        None,
        description="Action duration (default: 1 day)",
    ),
    weights: Annotated[
        WeightsField,
        Query(
            description="action weights, in L*C*R*Y* form (default: `L1C10R5Y1`)",
        ),
    ] = "L1C1R1Y1",
    decay_rate: float = Query(0.9, description="exponential decay rate per day"),
    offset: int = Query(0, ge=0, description="offset"),
    limit: int = Query(100, ge=1, le=1000, description="limit"),
    pool: Pool = Depends(db_pool.get_db),
):
    if end_time is None:
        end_time = datetime.now(tz=UTC)
    if start_time is None:
        if duration is None:
            duration = timedelta(days=1)
        start_time = end_time - duration
    elif duration is not None:
        raise HTTPException(
            status_code=400,
            detail="Cannot specify both `start_time` and `duration`",
        )
    return {
        "result": await db_utils.get_trending_fip2(
            start_time=start_time,
            end_time=end_time,
            decay_rate=decay_rate,
            chain_id=chain_id,
            offset=offset,
            limit=limit,
            pool=pool,
            weights=weights,
        )
    }


@router.get("/search-fip2", response_model=list[Fip2Token])
async def search_tokens_fip2(
    *,
    term: str = Query(
        ...,
        description="Search term: 0x-prefixed full address, $-prefixed symbol, or description substring",
        min_length=1,
    ),
    chain_id: int | None = Query(
        None,
        description="Optional chain ID to filter results to a specific chain",
    ),
    pool: Pool = Depends(db_pool.get_db),
) -> list[Fip2Token]:
    """
    Search for FIP-2 tokens based on the provided search term.

    - **0x-prefixed full address (42 chars)**: Exact match against token address
    - **$-prefixed symbol**: Prefix match against symbol field (matches both $XXX and XXX in DB)
    - **Other text**: Case-insensitive substring match against description field
    - **chain_id (optional)**: Filter results to a specific blockchain (e.g., 1 for Ethereum, 8453 for Base)

    Returns an array of matching tokens with chain_id, address (0x-prefixed hex), symbol, and description.
    """
    try:
        results = await search_fip2_tokens(term, pool, chain_id=chain_id)
        return results
    except Exception as exc:
        _logger.error(
            f"Error searching tokens with term {term!r} and chain_id {chain_id}: {exc}"
        )
        raise HTTPException(status_code=500, detail=str(exc)) from exc
