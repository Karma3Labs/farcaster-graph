import logging
import time
from collections.abc import Iterable
from datetime import UTC, datetime, timedelta
from numbers import Real
from typing import Protocol, Self

_logger = logging.getLogger(__name__)


# Wanted to have here:
#
# class Rangeable[S](Protocol):
#     """Protocol for types that support range-like operations."""
#
#     def __add__(self, other: S) -> Self: ...
#     def __lt__(self, other: Self) -> bool: ...
#
# But PyCharm doesn't like `range_to[T: Rangeable[S], S](...).
# Not sure if that syntax is prohibited by any PEP, but don't use it for now.
#
# TODO(ek) - figure out an acceptable annotation syntax, or remove the above.


def range_to[T, S](start: T, stop: T, step: S) -> Iterable[T]:
    """
    Work like `range()` but with any start/stop/step types.

    :param start: The start value.
    :param stop: The stop value (exclusive).
    :param step: The step size.
    """
    while start < stop:
        yield start
        start += step


def range_for[T, S](start: T, distance: S, step: S) -> Iterable[T]:
    """
    Work like `range_to()` but with a `distance` (from `start`) instead of `stop`.

    :param start: The start value.
    :param distance: The distance at or beyond which to stop iteration.
    :param step: The step size.
    """
    yield from range_to(start, start + distance, step)


def time_until(deadline: datetime) -> timedelta:
    """
    Calculate the time until the given `deadline` using the current time.

    :param deadline: The deadline (in local time zone if naive).
    :return: The time until the deadline.
    """
    tz = None if deadline.tzinfo is None else UTC
    return deadline - datetime.now(tz)


def sleep_until(deadline: datetime | Real) -> None:
    """Sleep until the given deadline."""
    if isinstance(deadline, datetime):
        s = time_until(deadline).total_seconds()
    else:
        s = deadline - time.time()
    if s >= 0:
        time.sleep(s)


def anchor_time(
    t: datetime | timedelta | None,
    at: datetime | None = None,
) -> datetime:
    """
    Anchor the given time `t` at the given reference datetime.

    A time `t` anchored at the anchor (`at`) is:

    - `t` itself if it is already a `datetime` (no anchoring needed);
    - `at + t` if `t` is a `timedelta` (i.e., relative to the anchor); or
    - The anchor `at` itself if `t` is `None`.

    Can be called without an anchor, which defaults to the current time.

    The given/returned `datetime` objects, if naive, are in local time.

    :param t: The potentially relative time to anchor.
    :param at: The reference datetime anchor.
    :return: The given `time` anchored at the given `anchor`.
    """
    if isinstance(t, datetime):
        return t
    if at is None:
        at = datetime.now()
    return at if t is None else at + t


def ticks_until_timeout(
    timeout: timedelta,
    period: timedelta,
    start: datetime | timedelta | None = None,
    delay_start: bool = True,
    skip_clumped: bool = False,
) -> Iterable[datetime]:
    """
    Yield periodic ticks until the `timeout` is reached.

    The given/yielded `datetime` objects, if naive, are in local time.

    :param timeout: The timeout, from the first tick.
    :param period: The tick period.
    :param start: The first tick time - defaults to/is anchored at now
        (see `anchor_time()` for details), and can be changed by `delay_start`:
        - If `delay_start`=`True`, the first tick is delayed by a full `period`
          and happens at `start + period`.
        - If `delay_start`=`False` (default), the first tick is not delayed,
          and happens immediately at `start`.
    :param delay_start: Whether to delay the first tick by `period`.  See `start` for details.
    :param skip_clumped: Whether to skip ticks that are well in the past
        and would cause the next tick to be processed immediately.
    """
    start = anchor_time(start)
    if delay_start:
        start += period
    for tick in range_for(start, timeout, period):
        if time_until(tick) <= -period:
            _logger.debug(f"clumped {tick=}")
            if skip_clumped:
                continue
        else:
            sleep_until(tick)
        yield tick
