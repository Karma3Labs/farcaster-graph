from collections.abc import Sequence
from typing import Any, TypeVar, cast

S = TypeVar("S", bound=Sequence[Any])


def paginate(whole: S, offset: int = 0, limit: int | None = None) -> S:
    if limit is None:
        return cast(S, whole[offset:])
    else:
        return cast(S, whole[offset : (offset + limit)])
