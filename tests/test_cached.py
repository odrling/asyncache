import asyncio
import functools
import unittest
from collections.abc import Coroutine
from typing import Any, Callable

import cachetools

from asyncache import cached


def sync[**P, T](func: Callable[P, Coroutine[Any, Any, T]]):
    """
    Helper to force an function/method to run synchronously.
    """

    @functools.wraps(func)
    def wrapped(*args: P.args, **kwargs: P.kwargs) -> T:
        return asyncio.run(func(*args, **kwargs))

    return wrapped


class AsyncMixin(unittest.TestCase):
    def cache(self):
        raise NotImplementedError

    async def coro(self, *args, **kwargs):
        if hasattr(self, "count"):
            self.count += 1
        else:
            self.count = 0

        await asyncio.sleep(0)

        return self.count

    @sync
    async def test_decorator_async(self):
        cache = self.cache()
        wrapper = cached(cache)(self.coro)

        self.assertEqual(len(cache), 0)
        self.assertEqual(wrapper.__wrapped__, self.coro)

        self.assertEqual((await wrapper(0)), 0)
        self.assertEqual(len(cache), 1)
        self.assertIn(cachetools.keys.hashkey(0), cache)
        self.assertNotIn(cachetools.keys.hashkey(1), cache)
        self.assertNotIn(cachetools.keys.hashkey(1.0), cache)

        self.assertEqual((await wrapper(1)), 1)
        self.assertEqual(len(cache), 2)
        self.assertIn(cachetools.keys.hashkey(0), cache)
        self.assertIn(cachetools.keys.hashkey(1), cache)
        self.assertIn(cachetools.keys.hashkey(1.0), cache)

        self.assertEqual((await wrapper(1)), 1)
        self.assertEqual(len(cache), 2)

        self.assertEqual((await wrapper(1.0)), 1)
        self.assertEqual(len(cache), 2)

        self.assertEqual((await wrapper(1.0)), 1)
        self.assertEqual(len(cache), 2)

    @sync
    async def test_decorator_typed_async(self):
        cache = self.cache()
        key = cachetools.keys.typedkey
        wrapper = cached(cache, key=key)(self.coro)

        self.assertEqual(len(cache), 0)
        self.assertEqual(wrapper.__wrapped__, self.coro)

        self.assertEqual((await wrapper(0)), 0)
        self.assertEqual(len(cache), 1)
        self.assertIn(cachetools.keys.typedkey(0), cache)
        self.assertNotIn(cachetools.keys.typedkey(1), cache)
        self.assertNotIn(cachetools.keys.typedkey(1.0), cache)

        self.assertEqual((await wrapper(1)), 1)
        self.assertEqual(len(cache), 2)
        self.assertIn(cachetools.keys.typedkey(0), cache)
        self.assertIn(cachetools.keys.typedkey(1), cache)
        self.assertNotIn(cachetools.keys.typedkey(1.0), cache)

        self.assertEqual((await wrapper(1)), 1)
        self.assertEqual(len(cache), 2)

        self.assertEqual((await wrapper(1.0)), 2)
        self.assertEqual(len(cache), 3)
        self.assertIn(cachetools.keys.typedkey(0), cache)
        self.assertIn(cachetools.keys.typedkey(1), cache)
        self.assertIn(cachetools.keys.typedkey(1.0), cache)

        self.assertEqual((await wrapper(1.0)), 2)
        self.assertEqual(len(cache), 3)

    @sync
    async def test_decorator_lock_async(self):
        class Lock(object):
            count = 0

            async def __aenter__(self):
                Lock.count += 1

            async def __aexit__(self, *exc):
                pass

        cache = self.cache()
        wrapper = cached(cache, lock=Lock())(self.coro)

        self.assertEqual(len(cache), 0)
        self.assertEqual(wrapper.__wrapped__, self.coro)
        self.assertEqual((await wrapper(0)), 0)
        self.assertEqual(Lock.count, 2)
        self.assertEqual((await wrapper(1)), 1)
        self.assertEqual(Lock.count, 4)
        self.assertEqual((await wrapper(1)), 1)
        self.assertEqual(Lock.count, 5)


class DictWrapperTest(AsyncMixin):
    def cache(self):
        return dict()


class LFUTest(AsyncMixin):
    def cache(self):
        return cachetools.LFUCache(10)


class LRUTest(AsyncMixin):
    def cache(self):
        return cachetools.LRUCache(10)


class RRTest(AsyncMixin):
    def cache(self):
        return cachetools.RRCache(10)


class TTLTest(AsyncMixin):
    def cache(self):
        return cachetools.TTLCache(maxsize=10, ttl=10.0)
