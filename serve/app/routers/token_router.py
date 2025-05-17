from collections.abc import Sequence
from typing import Self

from asyncpg import Pool
from eth_typing import ChecksumAddress
from eth_utils import to_bytes, to_checksum_address
from fastapi import APIRouter, Depends, HTTPException, Path, Query
from pydantic import BaseModel, ValidationError, field_validator

from ..dependencies import db_pool
from ..dependencies.db_utils import get_token_balances

router = APIRouter(prefix="/{token}", tags=["Token"])


class Token(BaseModel):
    """
    Token address.

    TODO(ek) - expand to CAIP-19, to add chain ID and stuff.
    """

    address: ChecksumAddress

    @field_validator("address", mode="before")
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
    except ValidationError as e:
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
