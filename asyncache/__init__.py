"""
Helpers to use [cachetools](https://github.com/tkem/cachetools) with
asyncio.
"""

import asyncio
import functools
from collections.abc import Awaitable, MutableMapping
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from typing import Any, Callable, ParamSpec, TypeVar

from cachetools import keys

__all__ = ["cached"]


_KT = TypeVar("_KT")
_T = TypeVar("_T")
_P = ParamSpec("_P")


@asynccontextmanager
async def AsyncNullContext():
    """noop context manager"""
    yield


def cached(
    cache: MutableMapping[_KT, asyncio.Future[_T]],
    # can’t find a way to easily express that arguments must be hashable
    key: Callable[_P, _KT] = keys.hashkey,  # type: ignore
    lock: AbstractAsyncContextManager[Any] | None = None,
) -> Callable[[Callable[_P, Awaitable[_T]]], Callable[_P, Awaitable[_T]]]:
    """
    Decorator to wrap a function or a coroutine with a memoizing callable
    that saves results in a cache.

    When ``lock`` is provided for a standard function, it's expected to
    implement ``__aenter__`` and ``__aexit__`` that will be used to lock
    the cache when gets updated.
    """
    lock = lock or AsyncNullContext()

    def decorator(
        func: Callable[_P, Awaitable[_T]],
    ) -> Callable[_P, Awaitable[_T]]:
        @functools.wraps(func)
        async def wrapper(*args: _P.args, **kwargs: _P.kwargs) -> _T:
            k = key(*args, **kwargs)

            run_coro = False
            fut: asyncio.Future[_T]
            async with lock:
                try:
                    fut = cache[k]
                except KeyError:
                    fut = asyncio.get_running_loop().create_future()
                    cache[k] = fut
                    run_coro = True

            if run_coro:
                try:
                    cache[k].set_result(await func(*args, **kwargs))
                except Exception as e:
                    cache[k].set_exception(e)

            return await fut

        return wrapper

    return decorator
