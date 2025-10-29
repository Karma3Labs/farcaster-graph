import logging
from collections.abc import Sequence
from typing import Self

from asyncpg import Pool
from eth_typing import ChecksumAddress
from eth_utils import to_bytes, to_checksum_address
from fastapi import APIRouter, Depends, HTTPException, Path, Query
from pydantic import BaseModel, ValidationError, field_validator

from ..dependencies import db_pool
from ..dependencies.db_utils import get_all_token_balances, get_token_balances

_logger = logging.getLogger(__name__)

router = APIRouter(prefix="/{token}", tags=["Token"])


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
    fids: Sequence[int] = Query(..., alias='fid', min_items=1),
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
@router.get("/balances/all")
async def get_all_balances(  # noqa: D401
    *,
    token: Token = Depends(get_token),
    limit: int | None = Query(
        None,
        gt=0,
        le=10000,
        description="Optional cap on number of rows (useful for leaderboards)",
    ),
    pool: Pool = Depends(db_pool.get_db),
):
    """Return **all** FID balances for *token*, sorted high→low.

    If `?limit=` is supplied, only the first *N* rows are returned.  This is
    handy when building a public leaderboard (e.g. top‑100 holders).
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
