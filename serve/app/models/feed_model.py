from enum import StrEnum
from typing import Annotated, Literal, Union

from .score_model import ScoreAgg
from ..config import settings

from pydantic import BaseModel, Field, TypeAdapter

class SortingOrder(StrEnum):
    SCORE = 'score'
    POPULAR = 'popular'
    RECENT = 'recent'
    HOUR = 'hour'
    DAY = 'day'
    REACTIONS = 'reactions'

class ChannelTimeframe(StrEnum):
    DAY = 'day'
    WEEK = 'week'
    MONTH = 'month'

PARENT_CASTS_AGE = {
    ChannelTimeframe.DAY: '1 day',
    ChannelTimeframe.WEEK: '7 days',
    ChannelTimeframe.MONTH: '30 days',
}

class CastsTimeframe(StrEnum):
    DAY = 'day'
    WEEK = 'week'
    MONTH = 'month'
    THREE_MONTHS = 'three_months'
    SIX_MONTHS = 'six_months'

CASTS_AGE = {
    CastsTimeframe.DAY: '1 day',
    CastsTimeframe.WEEK: '1 week',
    CastsTimeframe.MONTH: '1 month',
    CastsTimeframe.THREE_MONTHS: '3 months',
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
    score_threshold: Annotated[float, Field(alias="scoreThreshold", ge=0.0)] = 0.000000001
    cutoff_ptile: Annotated[int, Field(alias="cutoffPtile", le=100, ge=0)] = 100
    weights: str = 'L1C0R1Y1'
    sorting_order: Annotated[SortingOrder, Field(alias="sortingOrder")] = SortingOrder.DAY
    time_decay: Annotated[CastsTimeDecay, Field(alias="timeDecay")] = CastsTimeDecay.HOUR
    normalize: bool = True
    shuffle: bool = False
    timeout_secs: Annotated[int, Field(alias="timeoutSecs", ge=0, le=30)] = settings.FEED_TIMEOUT_SECS
    session_id: Annotated[str, Field(alias="sessionId")] = None

class PopularFeed(BaseModel):
    feed_type: Annotated[Literal['popular'], Field(alias="feedType")]
    lookback: CastsTimeframe = CastsTimeframe.WEEK
    agg: ScoreAgg = ScoreAgg.SUM
    score_threshold: Annotated[float, Field(alias="scoreThreshold", ge=0.0)] = 0.000000001
    weights: str = 'L1C1R1Y1'
    sorting_order: Annotated[SortingOrder, Field(alias="sortingOrder")] = SortingOrder.SCORE
    time_decay: Annotated[CastsTimeDecay, Field(alias="timeDecay")] = CastsTimeDecay.NEVER
    normalize: bool = True
    timeout_secs: Annotated[int, Field(alias="timeoutSecs", ge=0, le=30)] = settings.FEED_TIMEOUT_SECS
    session_id: Annotated[str, Field(alias="sessionId")] = None

class SearchScores(BaseModel):
    score_type: Annotated[Literal['search'], Field(alias="scoreType")]
    agg: ScoreAgg = ScoreAgg.SUM
    score_threshold: Annotated[float, Field(alias="scoreThreshold", ge=0.0)] = 0.000000001
    weights: str = 'L1C1R1Y1'
    sorting_order: Annotated[SortingOrder, Field(alias="sortingOrder")] = SortingOrder.SCORE
    time_decay: Annotated[CastsTimeDecay, Field(alias="timeDecay")] = CastsTimeDecay.NEVER
    normalize: bool = True

class ReplyScores(BaseModel):
    score_type: Annotated[Literal['reply'], Field(alias="scoreType")]
    agg: ScoreAgg = ScoreAgg.SUM
    score_threshold: Annotated[float, Field(alias="scoreThreshold", ge=0.0)] = 0.000000001
    weights: str = 'L1C1R1Y1'
    sorting_order: Annotated[SortingOrder, Field(alias="sortingOrder")] = SortingOrder.RECENT
    time_decay: Annotated[CastsTimeDecay, Field(alias="timeDecay")] = CastsTimeDecay.NEVER
    normalize: bool = True


FeedMetadata = TypeAdapter(Annotated[
    Union[TrendingFeed, PopularFeed],
    Field(discriminator="feed_type"),
])

ScoresMetadata = TypeAdapter(Annotated[
    Union[SearchScores, ReplyScores],
    Field(discriminator="score_type"),
])
