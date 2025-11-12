import asyncio
from datetime import timedelta
from functools import wraps
from typing import Any, Awaitable, Callable, ParamSpec, Sequence, TypeVar

from loguru import logger

P = ParamSpec("P")
R = TypeVar("R")
S = TypeVar("S", bound=Sequence[Any])


class PreemptiveRefresher:
    def __init__(self):
        self.__refresh_tasks: set[asyncio.Task] = set()

    def refresh(
        self, if_slower_than: timedelta, in_: timedelta
    ) -> Callable[[Callable[P, Awaitable[R]]], Callable[P, Awaitable[R]]]:
        def decorator(f: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R]]:
            @wraps(f)
            async def wrapper(*poargs: P.args, **kwargs: P.kwargs) -> R:
                loop = asyncio.get_running_loop()
                start_time = loop.time()
                result = await f(*poargs, **kwargs)
                end_time = loop.time()
                if timedelta(seconds=(end_time - start_time)) > if_slower_than:
                    args = [repr(arg) for arg in poargs]
                    args.extend(
                        f"{name}={repr(value)}" for name, value in kwargs.items()
                    )
                    logger.debug(
                        f"slow cached function call {f.__name__}({', '.join(args)}), "
                        f"scheduling preemptive refresh in {in_}"
                    )

                    async def refresh():
                        try:
                            await asyncio.sleep(in_.total_seconds())
                            await wrapper(*poargs, **kwargs)  # discard result
                        finally:
                            self.__refresh_tasks.discard(asyncio.current_task())

                    refresh_task = asyncio.create_task(refresh())
                    self.__refresh_tasks.add(refresh_task)
                return result

            return wrapper

        return decorator


pr = PreemptiveRefresher()
