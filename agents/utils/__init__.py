from typing import Any, Iterator
import asyncio

class AwaitableValue:
    """Wrapper that is awaitable and proxies common container operations.

    The primary goal is to tolerate test patterns that *double-await* fixtures:

        result = await setup_fixture
        a, b = await result

    The first `await` comes from the test, the internal await returns the
    underlying value (tuple, dict, list, etc.).  When the test chooses not to
    await, the wrapper still behaves like the wrapped value thanks to method
    proxying.
    """

    __slots__ = ("_value",)

    def __init__(self, value: Any):
        self._value = value

    # ------------------------------------------------------------
    # Awaitable protocol – returns the wrapped value
    # ------------------------------------------------------------
    def __await__(self):
        async def _inner():  # pragma: no cover – trivial coroutine
            return self._value
        return _inner().__await__()

    # ------------------------------------------------------------
    # Proxy container behaviour so object can be used without awaiting
    # ------------------------------------------------------------
    def __iter__(self) -> Iterator:  # type: ignore[override]
        return iter(self._value)  # Supports tuple/list/dict iteration

    def __len__(self):  # noqa: D401
        return len(self._value)

    def __getitem__(self, item):
        return self._value[item]

    def __getattr__(self, item):
        # Delegate attribute access to the wrapped value
        return getattr(self._value, item)

    def __repr__(self):  # noqa: D401
        return f"AwaitableValue({self._value!r})"
