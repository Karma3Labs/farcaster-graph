from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Annotated

from pydantic import (
    BaseModel,
    BeforeValidator,
    Field,
    SerializerFunctionWrapHandler,
    ValidationInfo,
    WrapSerializer,
)

from ..models import JSON, UUID, CoinAmount, EthAddress, TxHash


class RoundMethod(Enum):
    """Per-round token distribution methods."""

    UNIFORM = "uniform"
    PROPORTIONAL = "proportional"


def _parse_round_method(value: str, _info: ValidationInfo) -> RoundMethod:
    return RoundMethod(value)


def _serialize_round_method(
    value: RoundMethod, _handler: SerializerFunctionWrapHandler, _info: ValidationInfo
) -> str:
    return value.value


RoundMethod = Annotated[
    RoundMethod,
    BeforeValidator(_parse_round_method),
    WrapSerializer(_serialize_round_method),
]


class Request(BaseModel):
    """Token distribution request."""

    id: UUID
    timestamp: datetime
    chain_id: int
    token_address: EthAddress
    amount: CoinAmount  # raw amount before decimal scaling
    round_method: RoundMethod
    num_recipients_per_round: int = Field(ge=0)
    metadata: JSON
    recipient_token_community: EthAddress


class FundingTx(BaseModel):
    id: UUID
    request_id: UUID
    timestamp: datetime
    hash: TxHash
    sender: EthAddress
    recipient: EthAddress
    amount: CoinAmount = Field(gt=0)
    metadata: JSON


class Round(BaseModel):
    id: UUID
    request_id: UUID
    timestamp: datetime
    scheduled: datetime
    amount: CoinAmount = Field(gt=0)
    method: RoundMethod | None
    num_recipients: int | None = Field(ge=0)
    metadata: JSON


class Log(BaseModel):
    id: UUID
    round_id: UUID
    timestamp: datetime
    receiver: EthAddress | None  # Can be None if the user has no wallet
    amount: CoinAmount = Field(gt=0)
    tx_hash: TxHash | None
    fid: int = Field(gt=0)
    points: int = Field(gt=0)
