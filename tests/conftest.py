import os
import sys
import pytest
from web3 import Web3


@pytest.fixture(scope="session")
def web3_conn():
    # web3 = Web3(Web3.HTTPProvider())
    return Web3(Web3.HTTPProvider(f"https://mainnet.infura.io/v3/{os.environ['WEB3_INFURA_PROJECT_ID']}"))


@pytest.fixture(scope="session")
def async_web3_conn():
    return Web3(Web3.AsyncHTTPProvider(f"https://mainnet.infura.io/v3/{os.environ['WEB3_INFURA_PROJECT_ID']}"))


sys.path.insert(0, os.path.abspath("."))
