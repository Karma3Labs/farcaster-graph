from enum import Enum

class ChannelRankingsTimeframe(str, Enum):
    LIFETIME = 'lifetime'
    SIXTY_DAYS = '60d'
    SEVEN_DAYS = '7d'
    ONE_DAY = '1d'

CHANNEL_RANKING_STRATEGY_NAMES = {
    ChannelRankingsTimeframe.LIFETIME: 'channel_engagement',
    ChannelRankingsTimeframe.SIXTY_DAYS: '60d_engagement',
    ChannelRankingsTimeframe.SEVEN_DAYS: '7d_engagement',
    ChannelRankingsTimeframe.ONE_DAY: '1d_engagement'
}

class OpenrankCategory(str, Enum):
    TEST = 'test'
    PROD = 'prod'

class ChannelPointsOrderBy(str, Enum):
    TOTAL_POINTS = 'total_points'
    DAILY_POINTS = 'daily_points'
