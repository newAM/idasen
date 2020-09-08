from idasen import IdasenDesk
from tests.test_idasen import MockBleakClient
import asyncio
import pytest


@pytest.fixture(autouse=True)
def add_desk(doctest_namespace: dict):
    class DoctestDesk(IdasenDesk):
        def __init__(self, mac: str):
            super().__init__(mac=mac)
            self._client = MockBleakClient()

    doctest_namespace["IdasenDesk"] = DoctestDesk
    doctest_namespace["asyncio"] = asyncio
