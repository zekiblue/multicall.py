from joblib import Parallel, delayed
from multicall import Call
from multicall.utils import await_awaitable

CHAI = "0x06AF07097C9Eeb7fD685c692751D5C66dB49c215"


def from_wei(value):
    return value / 1e18


def test_call(web3_conn):
    call = Call(CHAI, "name()(string)", [["name", None]], _w3=web3_conn)
    assert call() == {"name": "Chai"}


def test_call_with_args(web3_conn):
    call = Call(CHAI, "balanceOf(address)(uint256)", [["balance", from_wei]], _w3=web3_conn)
    assert isinstance(call([CHAI])["balance"], float)


def test_call_with_predefined_args(web3_conn):
    call = Call(CHAI, ["balanceOf(address)(uint256)", CHAI], [["balance", from_wei]], _w3=web3_conn)
    assert isinstance(call()["balance"], float)


def test_call_with_origin(web3_conn):
    # Simulate the top holder sending 1 wei to the contract
    call = Call(
        CHAI,
        ["transfer(address,uint256)(bool)", CHAI, 1],
        [["success", None]],
        origin="0x3ee18B2214AFF97000D974cf647E7C347E8fa585",
        _w3=web3_conn,
    )
    assert call()["success"]


def test_call_async(web3_conn):
    call = Call(CHAI, "name()(string)", [["name", None]], _w3=web3_conn)
    assert await_awaitable(call) == {"name": "Chai"}


def test_call_with_args_async(web3_conn):
    call = Call(CHAI, "balanceOf(address)(uint256)", [["balance", from_wei]], _w3=web3_conn)
    assert isinstance(await_awaitable(call.coroutine([CHAI]))["balance"], float)


def test_call_with_predefined_args_async(web3_conn):
    call = Call(CHAI, ["balanceOf(address)(uint256)", CHAI], [["balance", from_wei]], _w3=web3_conn)
    assert isinstance(await_awaitable(call)["balance"], float)


def test_call_threading(web3_conn):
    Parallel(4, "threading")(
        delayed(Call(CHAI, "name()(string)", [["name", None]], _w3=web3_conn))() for i in range(10)
    )


# @pytest.mark.skip(reason="upgraded web3")
# def test_call_multiprocessing():
#     # NOTE can't have middlewares for multiprocessing
#     web3.provider.middlewares = tuple()
#     web3.middleware_onion.clear()
#     # TODO figure out why multiprocessing fails if you don't call request_func here
#     web3.provider.request_func(web3, web3.middleware_onion)
#     Parallel(4, "multiprocessing")(
#         delayed(Call(CHAI, "name()(string)", [["name", None]], _w3=web3))() for i in range(10)
#     )
