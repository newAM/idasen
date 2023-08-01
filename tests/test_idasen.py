from asyncio import AbstractEventLoop
from idasen import _bytes_to_meters, _is_desk
from idasen import IdasenDesk
from types import SimpleNamespace
from typing import AsyncGenerator
from typing import Callable
from typing import Generator
from unittest import mock
import asyncio
import bleak
import idasen
import pytest


@pytest.fixture(scope="session")
def event_loop() -> Generator[AbstractEventLoop, None, None]:
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# Switch this to a real mac address if you want to do live testing.
# This will wear out your motors faster than normal usage.
desk_mac: str = "AA:AA:AA:AA:AA:AA"


class MockCharacteristic:
    """Mocks a GATT Characteristic"""

    @property
    def uuid(self):
        return "99fa0020-338a-1024-8a49-009c0215f78a"

    def get_characteristic(self, uuid):
        return ""


class MockBleakClient:
    """Mocks the bleak client for unit testing."""

    def __init__(self):
        self._height = 1.0
        self.is_connected = False

    async def __aenter__(self):
        self._height = 1.0
        self.is_connected = True
        return self

    async def __aexit__(self, *args, **kwargs):
        self.is_connected = False
        return

    async def connect(self):
        self.is_connected = True

    async def disconnect(self):
        self.is_connected = False

    async def start_notify(self, uuid: str, callback: Callable):
        await callback(uuid, bytearray([0x00, 0x00, 0x00, 0x00]))
        await callback(None, bytearray([0x10, 0x00, 0x00, 0x00]))

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

    @property
    def address(self) -> str:
        return desk_mac

    @property
    def services(self):
        return [MockCharacteristic()]


@pytest.fixture(scope="session")
async def desk(event_loop: AbstractEventLoop) -> AsyncGenerator[IdasenDesk, None]:
    desk = IdasenDesk(mac=desk_mac)
    if desk_mac == "AA:AA:AA:AA:AA:AA":
        desk._client = MockBleakClient()  # type: ignore

    assert not desk.is_connected

    async with desk:
        yield desk


async def test_is_connected(desk: IdasenDesk):
    assert desk.is_connected


def test_mac(desk: IdasenDesk):
    assert desk.mac == desk_mac


async def test_pair(desk: IdasenDesk):
    if desk_mac != "AA:AA:AA:AA:AA:AA":
        return

    desk._client.pair = mock.AsyncMock()  # type: ignore
    await desk.pair()
    desk._client.pair.assert_called_once()


async def test_up(desk: IdasenDesk):
    initial = await desk.get_height()
    await desk.move_up()
    assert await desk.get_height() - initial > 0


async def test_down(desk: IdasenDesk):
    initial = await desk.get_height()
    await desk.move_down()
    assert await desk.get_height() - initial < 0


async def test_get_height(desk: IdasenDesk):
    height = await desk.get_height()
    assert isinstance(height, float)


async def test_monitor(desk: IdasenDesk):
    monitor_callback = mock.AsyncMock()
    await desk.monitor(monitor_callback)
    monitor_callback.assert_has_calls([mock.call(0.62), mock.call(0.6216)])


@pytest.mark.parametrize("target", [0.0, 2.0])
async def test_move_to_target_raises(desk: IdasenDesk, target: float):
    with pytest.raises(ValueError):
        await desk.move_to_target(target)


@pytest.mark.parametrize("target", [0.7, 1.1])
async def test_move_to_target(desk: IdasenDesk, target: float):
    await desk.move_to_target(target)
    assert abs(await desk.get_height() - target) < 0.005


async def test_move_stop():
    desk = IdasenDesk(mac=desk_mac)
    client = MockBleakClient()
    desk._client = client
    client.write_gatt_char = mock.AsyncMock()

    async def write_gatt_char_mock(
        uuid: str, command: bytearray, response: bool = False
    ):
        if client.write_gatt_char.call_count == 1:
            assert desk.is_moving
        # Force this method to behave asynchronously, otherwise it will block the
        # eventloop
        await asyncio.sleep(0.1)

    client.write_gatt_char.side_effect = write_gatt_char_mock

    async with desk:
        move_task = asyncio.create_task(desk.move_to_target(0.7))
        # Allow the move_task to start looping
        await asyncio.sleep(0.1)

        await desk.stop()
        assert not desk.is_moving
        assert move_task.done()


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


async def test_fail_to_connect(caplog, monkeypatch):
    async def raise_exception(*_):
        raise Exception

    # patch `asyncio.sleep()` to prevent making the tests unnecessarily long.
    monkeypatch.setattr(asyncio, "sleep", mock.AsyncMock())

    caplog.set_level("WARNING")

    desk = IdasenDesk(mac=desk_mac, exit_on_fail=True)
    client = MockBleakClient()
    client.connect = raise_exception
    desk._client = client

    with pytest.raises(SystemExit):
        async with desk:
            pass

    assert caplog.messages == [
        "[AA:AA:AA:AA:AA:AA] Failed to connect, retrying (1/3)...",
        "[AA:AA:AA:AA:AA:AA] Failed to connect, retrying (2/3)...",
        "[AA:AA:AA:AA:AA:AA] Failed to connect, retrying (3/3)...",
        "[AA:AA:AA:AA:AA:AA] Connection failed",
    ]

    caplog.clear()


async def test_discover_exception():
    with mock.patch.object(
        bleak.BleakScanner, "find_device_by_filter", side_effect=Exception
    ) as mock_discover:
        result = await IdasenDesk.discover()
        mock_discover.assert_awaited_once_with(idasen._is_desk)
        assert result is None


async def test_discover_empty():
    with mock.patch.object(
        bleak.BleakScanner, "find_device_by_filter", return_value=None
    ) as mock_discover:
        result = await IdasenDesk.discover()
        mock_discover.assert_awaited_once_with(idasen._is_desk)
        assert result is None


@pytest.mark.parametrize(
    "adv, is_desk",
    [
        (SimpleNamespace(service_uuids=[]), False),
        (SimpleNamespace(service_uuids=["foo"]), False),
        (SimpleNamespace(service_uuids=["foo", idasen._UUID_ADV_SVC, "bar"]), True),
    ],
)
def test_is_desk(adv: SimpleNamespace, is_desk: bool):
    assert _is_desk(None, adv) is is_desk  # type: ignore
