from pydantic import BaseModel

from ..models import CastHash


class LeaderboardRow(BaseModel):
    """Represents a single leaderboard row."""

    order_rank: int
    fid: int
    pfp: str
    username: str
    score: int
    cast_hashes: list[CastHash]
