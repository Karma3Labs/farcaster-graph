from enum import Enum

class ChannelRankingsTimeframe(str, Enum):
    LIFETIME = 'lifetime'
    SIXTY_DAYS = '60d'
    SEVEN_DAYS = '7d'

CHANNEL_RANKING_STRATEGY_NAMES = {
    ChannelRankingsTimeframe.LIFETIME: 'channel_engagement',
    ChannelRankingsTimeframe.SIXTY_DAYS: '60d_engagement',
    ChannelRankingsTimeframe.SEVEN_DAYS: '7d_engagement',
}

class OpenrankCategory(str, Enum):
    TEST = 'test'
    PROD = 'prod'