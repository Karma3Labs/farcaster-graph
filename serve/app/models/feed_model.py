from enum import StrEnum
from typing import Annotated, Literal, Union

from .score_model import ScoreAgg

from pydantic import BaseModel, Field, TypeAdapter

class SortingOrder(StrEnum):
    SCORE = 'score'
    POPULAR = 'popular'
    RECENT = 'recent'
    HOUR = 'hour'
    DAY = 'day'
    REACTIONS = 'reactions'

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

class CastsTimeDecay(StrEnum):
    MINUTE = 'minute'
    HOUR = 'hour'
    DAY = 'day'
    NEVER = 'never'

class TrendingFeed(BaseModel):
    feed_type: Annotated[Literal['trending'], Field(alias="feedType")]
    lookback: CastsTimeframe = CastsTimeframe.WEEK
    agg: ScoreAgg = ScoreAgg.SUM
    weights: str = 'L1C0R1Y1'
    sorting_order: Annotated[SortingOrder, Field(alias="sortingOrder")] = SortingOrder.DAY
    time_decay: Annotated[CastsTimeDecay, Field(alias="timeDecay")] = CastsTimeDecay.HOUR
    normalize: bool = True
    shuffle: bool = False

class PopularFeed(BaseModel):
    feed_type: Annotated[Literal['popular'], Field(alias="feedType")]
    lookback: CastsTimeframe = CastsTimeframe.WEEK
    agg: ScoreAgg = ScoreAgg.SUM
    weights: str = 'L1C1R1Y1'
    sorting_order: Annotated[SortingOrder, Field(alias="sortingOrder")] = SortingOrder.SCORE
    time_decay: Annotated[CastsTimeDecay, Field(alias="timeDecay")] = CastsTimeDecay.NEVER
    normalize: bool = True

FeedMetadata = TypeAdapter(Annotated[
    Union[TrendingFeed, PopularFeed],
    Field(discriminator="feed_type"),
])
