from datetime import timedelta
from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field, TypeAdapter

from ..config import settings
from .score_model import ScoreAgg


class SortingOrder(StrEnum):
    SCORE = 'score'
    POPULAR = 'popular'
    RECENT = 'recent'
    TIME_BUCKET = 'time_bucket'
    HOUR = 'hour'
    DAY = 'day'
    REACTIONS = 'reactions'
    BALANCE = 'balance'


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

CASTS_AGE_TD = {
    CastsTimeframe.DAY: timedelta(days=1),
    CastsTimeframe.WEEK: timedelta(days=7),
    CastsTimeframe.MONTH: timedelta(days=30),
    CastsTimeframe.THREE_MONTHS: timedelta(days=91),
    CastsTimeframe.SIX_MONTHS: timedelta(days=183),
}


class CastsTimeDecay(StrEnum):
    MINUTE = 'minute'
    HOUR = 'hour'
    DAY = 'day'
    NEVER = 'never'

    @property
    def timedelta(self) -> timedelta:
        try:
            return CASTS_TIME_DECAY_TIMEDELTAS[self]
        except KeyError:
            raise ValueError("{self!r} has no equivalent timedelta")


CASTS_TIME_DECAY_TIMEDELTAS = {
    CastsTimeDecay.MINUTE: timedelta(minutes=1),
    CastsTimeDecay.HOUR: timedelta(hours=1),
    CastsTimeDecay.DAY: timedelta(days=1),
}


ScoreThresholdField = Annotated[float, Field(alias="scoreThreshold", ge=0.0)]
ReactionsThresholdField = Annotated[int, Field(alias="reactionsThreshold", ge=0)]
CutoffPtileField = Annotated[int, Field(alias="cutoffPtile", le=100, ge=0)]
SortingOrderField = Annotated[SortingOrder, Field(alias="sortingOrder")]
TimeDecayField = Annotated[CastsTimeDecay, Field(alias="timeDecay")]
TimeDecayBaseField = Annotated[float, Field(alias="timeDecayBase", gt=0, le=0)]
TimeDecayPeriodField = Annotated[timedelta, Field(alias="timeDecayPeriod")]
TimeBucketLengthField = Annotated[timedelta, Field(alias="timeBucketLength")]
TimeoutSecsField = Annotated[int, Field(alias="timeoutSecs", ge=3, le=30)]
LimitCastsField = Annotated[
    int | None,
    Field(
        alias="limitCasts",
        description="limit number of casts per caster per time bucket; None/null (default) = unlimited",
    ),
]
SessionIdField = Annotated[str, Field(alias="sessionId")]
TokenAddressField = Annotated[str, Field(alias="tokenAddress")]
MinBalanceField = Annotated[Decimal, Field(alias="minBalance")]


class TrendingFeed(BaseModel):
    feed_type: Annotated[Literal['trending'], Field(alias="feedType")]
    lookback: CastsTimeframe = CastsTimeframe.WEEK
    agg: ScoreAgg = ScoreAgg.SUM
    score_threshold: ScoreThresholdField = 0.000000001
    reactions_threshold: ReactionsThresholdField = 1
    cutoff_ptile: CutoffPtileField = 100
    weights: str = 'L1C0R1Y1'
    sorting_order: SortingOrderField = SortingOrder.DAY
    time_decay: TimeDecayField = CastsTimeDecay.HOUR
    normalize: bool = True
    shuffle: bool = False
    timeout_secs: TimeoutSecsField = settings.FEED_TIMEOUT_SECS
    session_id: SessionIdField = None
    channels: list[str] | None = None


class PopularFeed(BaseModel):
    feed_type: Annotated[Literal['popular'], Field(alias="feedType")]
    lookback: CastsTimeframe = CastsTimeframe.WEEK
    agg: ScoreAgg = ScoreAgg.SUM
    score_threshold: ScoreThresholdField = 0.000000001
    reactions_threshold: ReactionsThresholdField = 10
    weights: str = 'L1C1R1Y1'
    sorting_order: SortingOrderField = SortingOrder.SCORE
    time_decay: TimeDecayField = CastsTimeDecay.NEVER
    normalize: bool = True
    timeout_secs: TimeoutSecsField = settings.FEED_TIMEOUT_SECS
    session_id: SessionIdField = None
    channels: list[str] = None


class FarconFeed(BaseModel):
    feed_type: Annotated[Literal['farcon'], Field(alias="feedType")]
    lookback: CastsTimeframe = CastsTimeframe.WEEK
    agg: ScoreAgg = ScoreAgg.SUM
    score_threshold: ScoreThresholdField = 0.0
    reactions_threshold: ReactionsThresholdField = 1
    cutoff_ptile: CutoffPtileField = 100
    weights: str = 'L1C1R1Y1'
    sorting_order: SortingOrderField = SortingOrder.HOUR
    time_decay: TimeDecayField = CastsTimeDecay.HOUR
    normalize: bool = True
    shuffle: bool = False
    timeout_secs: TimeoutSecsField = settings.FEED_TIMEOUT_SECS
    session_id: SessionIdField = None
    channels: list[str] | None = ["farcon", "farcon-nyc"]


class TokenFeed(BaseModel):
    feed_type: Annotated[Literal['token'], Field(alias="feedType")]
    token_address: TokenAddressField
    min_balance: MinBalanceField = Decimal(1)
    lookback: timedelta = timedelta(days=3)
    agg: ScoreAgg = ScoreAgg.SUMCUBEROOT
    score_threshold: ScoreThresholdField = 0.9
    reactions_threshold: ReactionsThresholdField = 1
    cutoff_ptile: CutoffPtileField = 100
    weights: str = 'L1C1R1Y1'
    sorting_order: SortingOrderField = SortingOrder.DAY
    time_bucket_length: TimeBucketLengthField = timedelta(hours=8)
    limit_casts: LimitCastsField = None
    time_decay_base: TimeDecayBaseField = 0.9
    time_decay_period: TimeDecayPeriodField = timedelta(days=1)
    normalize: bool = True
    shuffle: bool = False
    timeout_secs: TimeoutSecsField = settings.FEED_TIMEOUT_SECS
    session_id: SessionIdField = None
    channels: list[str] | None = None


class NewUsersFeed(BaseModel):
    feed_type: Annotated[Literal['newUsers'], Field(alias="feedType")]
    caster_age: timedelta = timedelta(days=90)
    lookback: timedelta = timedelta(weeks=1)
    agg: ScoreAgg = ScoreAgg.SUM
    score_threshold: ScoreThresholdField = 0.0
    reaction_threshold: ReactionsThresholdField = 1
    cutoff_ptile: CutoffPtileField = 90
    weights: str = 'L1C1R1Y1'
    sorting_order: SortingOrderField = SortingOrder.RECENT
    time_bucket_length: TimeBucketLengthField = timedelta(hours=8)
    limit_casts: LimitCastsField = None
    time_decay_base: TimeDecayBaseField = 0.9
    time_decay_period: TimeDecayPeriodField = timedelta(days=1)
    normalize: bool = True
    shuffle: bool = False
    timeout_secs: TimeoutSecsField = settings.FEED_TIMEOUT_SECS
    # TODO(ek): needed? find out by logging
    session_id: SessionIdField = None


class SearchScores(BaseModel):
    score_type: Annotated[Literal['search'], Field(alias="scoreType")]
    agg: ScoreAgg = ScoreAgg.SUM
    score_threshold: ScoreThresholdField = 0.000000001
    weights: str = 'L1C1R1Y1'
    sorting_order: SortingOrderField = SortingOrder.SCORE
    time_decay: TimeDecayField = CastsTimeDecay.NEVER
    normalize: bool = True


class ReplyScores(BaseModel):
    score_type: Annotated[Literal['reply'], Field(alias="scoreType")]
    agg: ScoreAgg = ScoreAgg.SUM
    score_threshold: ScoreThresholdField = 0.000000001
    weights: str = 'L1C1R1Y1'
    sorting_order: SortingOrderField = SortingOrder.RECENT
    time_decay: TimeDecayField = CastsTimeDecay.NEVER
    normalize: bool = True


FeedMetadata = TypeAdapter(
    Annotated[
        Union[TrendingFeed, PopularFeed, FarconFeed, TokenFeed, NewUsersFeed],
        Field(discriminator="feed_type"),
    ]
)

ScoresMetadata = TypeAdapter(
    Annotated[Union[SearchScores, ReplyScores], Field(discriminator="score_type")]
)
