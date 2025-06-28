import re
from enum import StrEnum
from typing import NamedTuple, Self


class ScoreAgg(StrEnum):
    RMS = 'rms'
    SUMSQUARE = 'sumsquare'
    SUM = 'sum'
    SUMCUBEROOT = 'sumcuberoot'


class Voting(StrEnum):
    SINGLE = 'single'
    MULTIPLE = 'multiple'
    # TODO
    # QUADRATIC = 'quadratic'


class QueryType(StrEnum):
    SUPERLITE = 'superlite'
    LITE = 'lite'
    HEAVY = 'heavy'


class EngagementType(StrEnum):
    V1 = '1.0'
    V3 = '2.0'


engagement_ids = dict()
engagement_ids[EngagementType.V1] = 3
engagement_ids[EngagementType.V3] = 9


class Weights(NamedTuple):
    cast: int = 10
    recast: int = 5
    reply: int = 7
    like: int = 1

    @classmethod
    def from_str(cls, weights_str: str) -> Self:
        wts = re.search(
            r'^([lL]([0-9]+))?([cC]([0-9]+))?([rR]([0-9]+))?([yY]([0-9]+))?$',
            weights_str,
        )
        if wts is None:
            raise ValueError(f"Invalid weights {weights_str=}")
        return cls(
            like=0 if wts.group(2) is None else int(wts.group(2)),
            cast=0 if wts.group(4) is None else int(wts.group(4)),
            recast=0 if wts.group(6) is None else int(wts.group(6)),
            reply=0 if wts.group(8) is None else int(wts.group(8)),
        )

    def __str__(self) -> str:
        return f"L{self.like}C{self.cast}R{self.recast}Y{self.reply}"
