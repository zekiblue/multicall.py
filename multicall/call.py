from typing import Any, Callable, Iterable, List, Optional, Tuple, Union

import eth_retry
from cchecksum import to_checksum_address
from eth_typing import Address, ChecksumAddress, HexAddress
from eth_typing.abi import Decodable
from web3 import Web3

from multicall.constants import Network, w3
from multicall.exceptions import StateOverrideNotSupported
from multicall.loggers import setup_logger
from multicall.signature import Signature, _get_signature
from multicall.utils import (
    _get_semaphore,
    chain_id,
    get_async_w3,
    run_in_subprocess,
    state_override_supported,
)

logger = setup_logger(__name__)

AnyAddress = Union[str, Address, ChecksumAddress, HexAddress]


class Call:
    __slots__ = (
        "target",
        "returns",
        "block_id",
        "gas_limit",
        "state_override_code",
        "w3",
        "args",
        "function",
        "signature",
        "origin",
    )

    def __init__(
        self,
        target: AnyAddress,
        function: Union[
            str, Iterable[Union[str, Any]]
        ],  # 'funcName(dtype)(dtype)' or ['funcName(dtype)(dtype)', input0, input1, ...]
        returns: Optional[Iterable[Tuple[str, Callable]]] = None,
        block_id: Optional[int] = None,
        gas_limit: Optional[int] = None,
        state_override_code: Optional[str] = None,
        # This needs to be None in order to use process_pool_executor
        _w3: Web3 = None,
        origin: Optional[AnyAddress] = None,
    ) -> None:
        self.target = to_checksum_address(target)
        self.returns = returns
        self.block_id = block_id
        self.gas_limit = gas_limit
        self.state_override_code = state_override_code
        self.w3 = _w3
        self.origin = to_checksum_address(origin) if origin else None

        self.args: Optional[List[Any]]
        if isinstance(function, list):
            self.function, *self.args = function
        else:
            self.function = function
            self.args = None

        self.signature = _get_signature(self.function)

    def __repr__(self) -> str:
        return f"<Call {self.function} on {self.target[:8]}>"

    @property
    def data(self) -> bytes:
        return self.signature.encode_data(self.args)

    def decode_output(
        output: Decodable,
        signature: Signature,
        returns: Optional[Iterable[Tuple[str, Callable]]] = None,
        success: Optional[bool] = None,
    ) -> Any:
        if success is None:
            apply_handler = lambda handler, value: handler(value)  # noqa: E731
        else:
            apply_handler = lambda handler, value: handler(success, value)  # noqa: E731

        if success is None or success:
            try:
                decoded = signature.decode_data(output)
            except Exception:
                success, decoded = False, [None] * (1 if not returns else len(returns))  # type: ignore
        else:
            decoded = [None] * (1 if not returns else len(returns))  # type: ignore

        logger.debug("returns: %s", returns)
        logger.debug("decoded: %s", decoded)

        if returns:
            return {
                name: apply_handler(handler, value) if handler else value
                for (name, handler), value in zip(returns, decoded)
            }
        else:
            return decoded if len(decoded) > 1 else decoded[0]

    @eth_retry.auto_retry
    def __call__(
        self,
        args: Optional[Any] = None,
        _w3: Optional[Web3] = None,
        *,
        block_id: Optional[int] = None,
    ) -> Any:
        _w3 = self.w3 or _w3 or w3
        args = prep_args(
            self.target,
            self.signature,
            args or self.args,
            block_id or self.block_id,
            self.origin,
            self.gas_limit,
            self.state_override_code,
        )
        return Call.decode_output(
            _w3.eth.call(*args),
            self.signature,
            self.returns,
        )

    def __await__(self) -> Any:
        return self.coroutine().__await__()

    @eth_retry.auto_retry
    async def coroutine(
        self,
        args: Optional[Any] = None,
        _w3: Optional[Web3] = None,
        *,
        block_id: Optional[int] = None,
    ) -> Any:
        _w3 = self.w3 or _w3 or w3

        if self.state_override_code and not state_override_supported(_w3):
            raise StateOverrideNotSupported(
                f"State override is not supported on {Network(chain_id(_w3)).__repr__()[1:-1]}."
            )

        async with _get_semaphore():
            output = await get_async_w3(_w3).eth.call(
                *await run_in_subprocess(
                    prep_args,
                    self.target,
                    self.signature,
                    args or self.args,
                    block_id or self.block_id,
                    self.origin,
                    self.gas_limit,
                    self.state_override_code,
                )
            )

        return await run_in_subprocess(Call.decode_output, output, self.signature, self.returns)


def prep_args(
    target: str,
    signature: Signature,
    args: Optional[Any],
    block_id: Optional[int],
    origin: str,
    gas_limit: int,
    state_override_code: str,
) -> List:
    calldata = signature.encode_data(args)

    args = [{"to": target, "data": calldata}, block_id]

    if origin:
        args[0]["from"] = origin

    if gas_limit:
        args[0]["gas"] = gas_limit

    if state_override_code:
        args.append({target: {"code": state_override_code}})

    return args
