import pytest
import asyncio

# from brownie import web3
from multicall.utils import (
    await_awaitable,
    raise_if_exception,
    gather,
    get_endpoint,
    get_async_w3,
    run_in_subprocess,
    raise_if_exception_in,
    get_event_loop,
)
from web3.providers.async_base import AsyncBaseProvider

from web3.auto import w3


class UST(Exception):
    pass


oopsie = UST("oops")


def work():
    pass


async def coro():
    return


def exception_coro():
    raise oopsie


def test_await_awaitable():
    assert await_awaitable(coro()) is None  # noqa: F405


def test_raise_if_exception():
    with pytest.raises(UST):
        raise_if_exception(UST("oops"))


def test_raise_if_exception_in():
    with pytest.raises(UST):
        raise_if_exception_in(["BTC", "ETH", UST("oops")])


def test_gather():
    assert await_awaitable(gather([coro(), coro(), coro(), coro(), coro()])) == [
        None,
        None,
        None,
        None,
        None,
    ]


def test_gather_with_exception():
    with pytest.raises(UST):
        await_awaitable(gather([coro(), coro(), coro(), coro(), exception_coro()]))


@pytest.mark.skip(reason="no local endpoint setup")
def test_get_endpoint_web3py_auto():
    assert get_endpoint(w3) == "http://localhost:8545"


def test_get_async_w3_with_sync(web3_conn):
    w3_ = get_async_w3(web3_conn)
    assert w3_.eth.is_async
    assert isinstance(w3_.provider, AsyncBaseProvider)
    assert await_awaitable(w3_.eth.chain_id) == 1


def test_get_async_w3_with_async(web3_conn):
    async_w3 = get_async_w3(web3_conn)
    w3_ = get_async_w3(async_w3)
    assert w3_ == async_w3
    assert await_awaitable(w3_.eth.chain_id) == 1


def test_run_in_subprocess():
    assert await_awaitable(run_in_subprocess(work)) is None


def test_get_event_loop():
    assert get_event_loop() == asyncio.get_event_loop()


def test_get_event_loop_in_thread():
    def task():
        assert get_event_loop() == asyncio.get_event_loop()

    await_awaitable(get_event_loop().run_in_executor(None, task))
