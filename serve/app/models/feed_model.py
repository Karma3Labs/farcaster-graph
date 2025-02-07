from enum import StrEnum
from typing import Optional, Annotated

from pydantic import BaseModel, Field

class SortingOrder(StrEnum):
    POPULAR = 'popular'
    RECENT = 'recent'
    HOUR = 'hour'
    REACTIONS = 'reactions'

class FeedType(StrEnum):
    POPULAR = 'popular'
    TRENDING = 'trending'

class CastsTimeframe(StrEnum):
    WEEK = 'week'
    MONTH = 'month'
    SIX_MONTHS = 'six_months'


class ProviderMetadata(BaseModel):
    feed_type: Optional[Annotated[FeedType, Field(alias="feedType")]]
    timeframe: Optional[CastsTimeframe]