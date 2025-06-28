from typing import Annotated

from pydantic import PlainSerializer, PlainValidator, WithJsonSchema


def _validate_hex_bytes(v: str | bytes) -> bytes:
    match v:
        case bytes():
            return v
        case str():
            v = v.removeprefix("0x")
            try:
                return bytes.fromhex(v)
            except ValueError as e:
                raise ValueError(f"Invalid hex bytes: {v}") from e
        case _:
            raise TypeError(f"Invalid hex bytes type: {type(v)}")


type HexBytes = Annotated[
    bytes,
    PlainValidator(_validate_hex_bytes, json_schema_input_type=str),
    PlainSerializer(lambda v: f"0x{v.hex()}"),
    WithJsonSchema(
        {
            "type": "string",
            "pattern": "^(0x)?([0-9a-fA-F][0-9a-fA-F])*$",
            "examples": [
                "0xdeadbeef",
                "0xDEADBEEF",
                "0x",
                "deadbeef",
                "DEADBEEF",
                "",
            ],
        }
    ),
]
