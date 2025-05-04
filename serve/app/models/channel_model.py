from enum import Enum, StrEnum
from pydantic import BaseModel


class ChannelRankingsTimeframe(str, Enum):
    LIFETIME = 'lifetime'
    SIXTY_DAYS = '60d'
    SEVEN_DAYS = '7d'
    ONE_DAY = '1d'


CHANNEL_RANKING_STRATEGY_NAMES = {
    ChannelRankingsTimeframe.LIFETIME: 'channel_engagement',
    ChannelRankingsTimeframe.SIXTY_DAYS: '60d_engagement',
    ChannelRankingsTimeframe.SEVEN_DAYS: '7d_engagement',
    ChannelRankingsTimeframe.ONE_DAY: '1d_engagement',
}


class OpenrankCategory(StrEnum):
    TEST = 'test'
    PROD = 'prod'


# Deprecated
class ChannelPointsOrderBy(StrEnum):
    TOTAL_POINTS = 'total_points'
    DAILY_POINTS = 'daily_points'


class ChannelEarningsOrderBy(StrEnum):
    TOTAL = 'total'
    WEEKLY = 'weekly'
    DAILY = 'daily'
    LATEST = 'latest'


class ChannelEarningsScope(StrEnum):
    AIRDROP = 'airdrop'
    DAILY = 'daily'


class ChannelEarningsType(StrEnum):
    POINTS = 'points'
    TOKENS = 'tokens'


class ChannelFidType(StrEnum):
    MEMBER = 'member'
    FOLLOWER = 'follower'
