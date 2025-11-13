import uuid
from enum import Enum
from typing import Annotated, Any

from eth_typing import ChecksumAddress
from eth_typing import HexStr as EthHexStr
from eth_utils import to_bytes, to_checksum_address, to_hex
from pydantic import (
    BaseModel,
    BeforeValidator,
    Field,
    SerializationInfo,
    SerializerFunctionWrapHandler,
    ValidationInfo,
    WrapSerializer,
)

type CoinAmount = int
type JSON = None | int | float | str | list[JSON] | dict[str, JSON]


class SerDesDomain(Enum):
    """Serialization/deserialization domain, i.e., what will consume/produce the serialized form."""

    SELF = "self"
    PSYCOPG2 = "psycopg2"
    ASYNCPG = "asyncpg"
    API = "api"


class SerDesContext(BaseModel):
    """Serialization/deserialization context."""

    domain: SerDesDomain = Field(default=SerDesDomain.SELF)


psycopg2_context = SerDesContext(domain=SerDesDomain.PSYCOPG2)
api_context = SerDesContext(domain=SerDesDomain.API)
"""Psycopg2 context for serialization/deserialization."""


# Common serializers


def _serialize_as_str(
    value: Any, _handler: SerializerFunctionWrapHandler, info: SerializationInfo
):
    """
    Serialize as a string, except in SerDesDomain.SELF.

    Use for things like UUID and BigInt, whose string-form literal can be used in all domains (DB and API).
    """
    match info.mode:
        case "json":
            return str(value)
        case "python":
            context: SerDesContext = info.context or SerDesContext()
            match context.domain:
                case SerDesDomain.SELF:
                    return value
                case SerDesDomain.PSYCOPG2 | SerDesDomain.ASYNCPG | SerDesDomain.API:
                    return str(value)
                case _:
                    raise ValueError(f"Unhandled serialization domain {context.domain}")
        case _:
            raise ValueError(f"Unhandled serialization mode {info.mode}")


def _serialize_eth_hex_str(
    value: EthHexStr,
    _handler: SerializerFunctionWrapHandler,
    info: SerializationInfo,
):
    """
    Serialize an `eth_typing.HexStr` as the string itself, except as `bytes` in DB domains.

    Use for things like ChecksumAddress.
    """
    match info.mode:
        case "json":
            return value
        case "python":
            context: SerDesContext = info.context or SerDesContext()
            match context.domain:
                case SerDesDomain.SELF | SerDesDomain.API:
                    return value
                case SerDesDomain.PSYCOPG2 | SerDesDomain.ASYNCPG:
                    return to_bytes(hexstr=value)
                case _:
                    raise ValueError(f"Unhandled serialization domain {context.domain}")
        case _:
            raise ValueError(f"Unhandled serialization mode {info.mode}")


# Type-specific ones follow


def _parse_eth_address(value: Any, info: ValidationInfo) -> ChecksumAddress:
    match info.mode:
        case "json":
            return to_checksum_address(value)
        case "python":
            context: SerDesContext = info.context or SerDesContext()
            match context.domain:
                case SerDesDomain.SELF | SerDesDomain.API:
                    if isinstance(value, str):
                        return to_checksum_address(value)
                    raise ValueError(f"Invalid EthAddress type={type(value)!r}")
                case SerDesDomain.PSYCOPG2 | SerDesDomain.ASYNCPG:
                    if isinstance(value, (bytes, bytearray, memoryview)):
                        return to_checksum_address(value)
                    raise ValueError(f"Invalid EthAddress type={type(value)!r}")
                case _:
                    raise ValueError(
                        f"Unhandled deserialization domain {context.domain}"
                    )
        case _:
            raise ValueError(f"Unhandled deserialization mode {info.mode}")


EthAddress = Annotated[
    ChecksumAddress,
    BeforeValidator(_parse_eth_address),
    WrapSerializer(_serialize_eth_hex_str),
]
"""eth_utils.ChecksumAddress with Pydantic round trip serdes."""


def _parse_uuid(value: Any, info: ValidationInfo) -> uuid.UUID:
    match info.mode:
        case "json":
            if isinstance(value, str):
                return uuid.UUID(value)
            raise ValueError(f"Invalid UUID type={type(value)!r} {value=}")
        case "python":
            context: SerDesContext = info.context or SerDesContext()
            match context.domain:
                case SerDesDomain.SELF:
                    if isinstance(value, uuid.UUID):
                        return value
                    raise ValueError(f"Invalid UUID type={type(value)!r} {value=}")
                case SerDesDomain.PSYCOPG2 | SerDesDomain.ASYNCPG | SerDesDomain.API:
                    if isinstance(value, uuid.UUID):  # UUID handler registered
                        return value
                    if isinstance(value, str):  # UUID handler not registered
                        return uuid.UUID(value)
                    raise ValueError(f"Invalid UUID type={type(value)!r} {value=}")
                case _:
                    raise ValueError(
                        f"Unhandled deserialization domain {context.domain}"
                    )
        case _:
            raise ValueError(f"Unhandled deserialization mode {info.mode}")


UUID = Annotated[
    uuid.UUID, BeforeValidator(_parse_uuid), WrapSerializer(_serialize_as_str)
]
"""`uuid.UUID` with Pydantic round trip serdes."""


def _parse_big_int(value: Any, info: ValidationInfo) -> int:
    match info.mode:
        case "json":
            if isinstance(value, int):
                return value
            if isinstance(value, str):
                return int(value)
            raise ValueError(f"Invalid BigInt type={type(value)!r} {value=}")
        case "python":
            context: SerDesContext = info.context or SerDesContext()
            match context.domain:
                case SerDesDomain.SELF:
                    return value
                case SerDesDomain.PSYCOPG2 | SerDesDomain.ASYNCPG:
                    # value is Decimal; just strip the fractional part
                    return int(value)
                case SerDesDomain.API:
                    # value is integer string or just number
                    return int(value)
                case _:
                    raise ValueError(
                        f"Unhandled deserialization domain {context.domain}"
                    )
        case _:
            raise ValueError(f"Unhandled deserialization mode {info.mode}")


BigInt = Annotated[
    int, BeforeValidator(_parse_big_int), WrapSerializer(_serialize_as_str)
]
"""`int` with Pydantic round trip serdes."""


def _parse_hex_str(value: Any, info: ValidationInfo) -> EthHexStr:
    match info.mode:
        case "json":
            return to_hex(to_bytes(hexstr=value))
        case "python":
            context: SerDesContext = info.context or SerDesContext()
            match context.domain:
                case SerDesDomain.SELF | SerDesDomain.API:
                    return value
                case SerDesDomain.PSYCOPG2 | SerDesDomain.ASYNCPG:
                    return to_hex(value)
                case _:
                    raise ValueError(
                        f"Unhandled deserialization domain {context.domain}"
                    )
        case _:
            raise ValueError(f"Unhandled deserialization mode {info.mode}")


HexStr = Annotated[
    EthHexStr, BeforeValidator(_parse_hex_str), WrapSerializer(_serialize_eth_hex_str)
]

TxHash = Annotated[HexStr, Field(min_length=66, max_length=66)]
CastHash = Annotated[HexStr, Field(min_length=42, max_length=42)]
