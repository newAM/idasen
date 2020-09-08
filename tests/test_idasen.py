from asyncio import AbstractEventLoop
from idasen import _bytes_to_meters
from idasen import IdasenDesk
from typing import Callable
import asyncio
import idasen
import pytest


@pytest.fixture(scope="session")
def event_loop() -> AbstractEventLoop:
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


class MockBleakClient:
    """ Mocks the bleak client for unit testing. """

    async def __aenter__(self):
        self._height = 1.0
        self._connected = True
        return self

    async def __aexit__(self, *args, **kwargs):
        self._connected = False
        return

    async def is_connected(self) -> bool:
        return self._connected

    async def start_notify(self, uuid: str, callback: Callable):
        callback(uuid, bytearray([0x00, 0x00, 0x00, 0x00]))
        callback(None, bytearray([0x00, 0x00, 0x00, 0x00]))

    async def write_gatt_char(
        self, uuid: str, command: bytearray, response: bool = False
    ):
        if uuid == idasen._UUID_COMMAND:
            if command == idasen._COMMAND_UP:
                self._height += 0.001
            elif command == idasen._COMMAND_DOWN:
                self._height -= 0.001

    async def read_gatt_char(self, uuid: str) -> bytearray:
        norm = self._height - IdasenDesk.MIN_HEIGHT
        norm *= 10000
        norm = int(norm)
        low_byte = norm & 0xFF
        high_byte = (norm >> 8) & 0xFF
        return bytearray([low_byte, high_byte, 0x00, 0x00])


# Switch this to a real mac address if you want to do live testing.
# This will wear out your motors faster than normal usage.
desk_mac: str = "AA:AA:AA:AA:AA:AA"


@pytest.fixture(scope="session")
async def desk(event_loop: AbstractEventLoop) -> IdasenDesk:
    desk = IdasenDesk(mac=desk_mac)
    if desk_mac == "AA:AA:AA:AA:AA:AA":
        desk._client = MockBleakClient()

    assert not await desk.is_connected()

    async with desk:
        yield desk


@pytest.mark.asyncio
async def test_is_connected(desk: IdasenDesk):
    assert await desk.is_connected()


def test_mac(desk: IdasenDesk):
    assert desk.mac == desk_mac


@pytest.mark.asyncio
async def test_up(desk: IdasenDesk):
    initial = await desk.get_height()
    await desk.move_up()
    assert await desk.get_height() - initial > 0


@pytest.mark.asyncio
async def test_down(desk: IdasenDesk):
    initial = await desk.get_height()
    await desk.move_down()
    assert await desk.get_height() - initial < 0


@pytest.mark.asyncio
async def test_get_height(desk: IdasenDesk):
    height = await desk.get_height()
    assert isinstance(height, float)


@pytest.mark.asyncio
@pytest.mark.parametrize("target", [0.0, 2.0])
async def test_move_to_target_raises(desk: IdasenDesk, target: float):
    with pytest.raises(ValueError):
        await desk.move_to_target(target)


@pytest.mark.asyncio
@pytest.mark.parametrize("target", [0.7, 1.1])
async def test_move_to_target(desk: IdasenDesk, target: float):
    await desk.move_to_target(target)
    assert abs(await desk.get_height() - target) < 0.005


@pytest.mark.parametrize(
    "raw, result",
    [
        (bytearray([0x64, 0x19, 0x00, 0x00]), IdasenDesk.MAX_HEIGHT),
        (bytearray([0x00, 0x00, 0x00, 0x00]), IdasenDesk.MIN_HEIGHT),
        (bytearray([0x51, 0x04, 0x00, 0x00]), 0.7305),
        (bytearray([0x08, 0x08, 0x00, 0x00]), 0.8256),
    ],
)
def test_bytes_to_meters(raw: bytearray, result: float):
    assert _bytes_to_meters(raw) == result
