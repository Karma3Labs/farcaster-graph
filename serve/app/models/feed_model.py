from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, Field

class SortingOrder(StrEnum):
    SCORE = 'score'
    POPULAR = 'popular'
    RECENT = 'recent'
    HOUR = 'hour'
    REACTIONS = 'reactions'

class FeedType(StrEnum):
    POPULAR = 'popular'
    TRENDING = 'trending'

class CastsTimeframe(StrEnum):
    DAY = 'day'
    WEEK = 'week'
    MONTH = 'month'
    SIX_MONTHS = 'six_months'

CASTS_AGE = {
    CastsTimeframe.DAY: '1 day',
    CastsTimeframe.WEEK: '1 week',
    CastsTimeframe.MONTH: '1 month',
    CastsTimeframe.SIX_MONTHS: '6 months',
}


class ProviderMetadata(BaseModel):
    feed_type: Annotated[FeedType, Field(alias="feedType")]
    lookback: CastsTimeframe