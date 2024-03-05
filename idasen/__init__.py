from bleak import BleakClient
from bleak import BleakScanner
from bleak import BleakGATTCharacteristic
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData
from typing import Any, Awaitable, Callable
from typing import MutableMapping
from typing import Optional
from typing import Tuple
from typing import Union
from inspect import signature
import asyncio
import logging
import struct
import sys


_UUID_HEIGHT: str = "99fa0021-338a-1024-8a49-009c0215f78a"
_UUID_COMMAND: str = "99fa0002-338a-1024-8a49-009c0215f78a"
_UUID_REFERENCE_INPUT: str = "99fa0031-338a-1024-8a49-009c0215f78a"
_UUID_ADV_SVC: str = "99fa0001-338a-1024-8a49-009c0215f78a"
_UUID_DPG: str = "99fa0011-338a-1024-8a49-009c0215f78a"

_COMMAND_REFERENCE_INPUT_STOP: bytearray = bytearray([0x01, 0x80])
_COMMAND_UP: bytearray = bytearray([0x47, 0x00])
_COMMAND_DOWN: bytearray = bytearray([0x46, 0x00])
_COMMAND_STOP: bytearray = bytearray([0xFF, 0x00])
_COMMAND_WAKEUP: bytearray = bytearray([0xFE, 0x00])


# height calculation offset in meters, assumed to be the same for all desks
def _bytes_to_meters_and_speed(raw: bytearray) -> Tuple[float, float]:
    """Converts a value read from the desk in bytes to height in meters and speed."""
    raw_len = len(raw)
    expected_len = 4
    assert (
        raw_len == expected_len
    ), f"Expected raw value to be {expected_len} bytes long, got {raw_len} bytes"

    int_raw, speed_raw = struct.unpack("<Hh", raw)
    meters = float(int(int_raw) / 10000) + IdasenDesk.MIN_HEIGHT
    speed = float(int(speed_raw) / 10000)

    return meters, speed


def _meters_to_bytes(meters: float) -> bytearray:
    """Converts meters to bytes for setting the position on the desk"""
    int_raw: int = int((meters - IdasenDesk.MIN_HEIGHT) * 10000)
    return bytearray(struct.pack("<H", int_raw))


def _is_desk(device: BLEDevice, adv: AdvertisementData) -> bool:
    return _UUID_ADV_SVC in adv.service_uuids


class _DeskLoggingAdapter(logging.LoggerAdapter):
    """Prepends logging messages with the desk MAC address."""

    def process(
        self, msg: str, kwargs: MutableMapping[str, Any]
    ) -> Tuple[str, MutableMapping[str, Any]]:
        return f"[{self.extra['mac']}] {msg}", kwargs  # type: ignore


class IdasenDesk:
    """
    Idasen desk.

    Args:
        mac: Bluetooth MAC address of the desk, or an instance of a BLEDevice.
        exit_on_fail: If set to True, failing to connect will call ``sys.exit(1)``,
            otherwise the exception will be raised.
        disconnected_callback:
            Callback that will be scheduled in the event loop when the client is
            disconnected. The callable must take one argument, which will be
            this client object.

    Note:
        There is no locking to prevent you from running multiple movement
        coroutines simultaneously.

    Example:
        Basic Usage::

            from idasen import IdasenDesk


            async with IdasenDesk(mac="AA:AA:AA:AA:AA:AA") as desk:
                # call methods here...
    """

    #: Minimum desk height in meters.
    MIN_HEIGHT: float = 0.62

    #: Maximum desk height in meters.
    MAX_HEIGHT: float = 1.27

    #: Number of times to retry upon failure to connect.
    RETRY_COUNT: int = 3

    def __init__(
        self,
        mac: Union[BLEDevice, str],
        exit_on_fail: bool = False,
        disconnected_callback: Optional[Callable[[BleakClient], None]] = None,
    ):
        self._exit_on_fail = exit_on_fail
        self._client = BleakClient(
            address_or_ble_device=mac,
            disconnected_callback=disconnected_callback,
        )
        self._mac = mac.address if isinstance(mac, BLEDevice) else mac
        self._logger = _DeskLoggingAdapter(
            logger=logging.getLogger(__name__), extra={"mac": self.mac}
        )
        self._moving = False
        self._move_task: Optional[asyncio.Task] = None

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, *args, **kwargs):
        await self.disconnect()

    async def pair(self):
        """
        Pair with the desk.

        This method is not available on macOS. Instead of manually initiating
        paring, the user will be prompted to pair automatically as soon as it
        is required.

        See :py:meth:`bleak.BleakClient.pair` for more information.
        """
        await self._client.pair()

    async def connect(self):
        """
        Connect to the desk.

        This method is an alternative to the context manager.
        When possible the context manager is preferred.

        >>> async def example() -> bool:
        ...     desk = IdasenDesk(mac="AA:AA:AA:AA:AA:AA")
        ...     await desk.connect()  # don't forget to call disconnect later!
        ...     return desk.is_connected
        >>> asyncio.run(example())
        True
        """
        i = 0
        while True:
            try:
                await self._client.connect()
                await self.wakeup()
                return
            except Exception:
                if i >= self.RETRY_COUNT:
                    self._logger.critical("Connection failed")
                    if self._exit_on_fail:
                        sys.exit(1)
                    raise
                i += 1
                self._logger.warning(
                    f"Failed to connect, retrying ({i}/{self.RETRY_COUNT})..."
                )
                await asyncio.sleep(0.3 * i)

    async def disconnect(self):
        """
        Disconnect from the desk.

        This method is an alternative to the context manager.
        When possible the context manager is preferred.

        >>> async def example() -> bool:
        ...     desk = IdasenDesk(mac="AA:AA:AA:AA:AA:AA")
        ...     await desk.connect()
        ...     await desk.disconnect()
        ...     return desk.is_connected
        >>> asyncio.run(example())
        False
        """
        await self._client.disconnect()

    async def monitor(self, callback: Callable[..., Awaitable[None]]):
        output_service_uuid = "99fa0020-338a-1024-8a49-009c0215f78a"
        output_char_uuid = "99fa0021-338a-1024-8a49-009c0215f78a"

        # Determine the amount of callback parameters
        # 1st one is height, optional 2nd one is speed, more is not supported
        callback_param_count = len(signature(callback).parameters)
        if callback_param_count != 1 and callback_param_count != 2:
            raise ValueError(
                "Invalid callback provided, only 1 or 2 parameters are supported"
            )

        return_speed_value = callback_param_count == 2
        previous_height = 0.0
        previous_speed = 0.0

        async def output_listener(char: BleakGATTCharacteristic, data: bytearray):
            height, speed = _bytes_to_meters_and_speed(data)
            self._logger.debug(f"Got data: {height}m {speed}m/s")

            nonlocal previous_height
            nonlocal previous_speed
            if abs(height - previous_height) < 0.001 and (
                not return_speed_value or abs(speed - previous_speed) < 0.001
            ):
                return
            previous_height = height
            previous_speed = speed

            if return_speed_value:
                await callback(height, speed)
            else:
                await callback(height)

        for service in self._client.services:
            if service.uuid != output_service_uuid:
                continue

            chr_output = service.get_characteristic(output_char_uuid)
            if chr_output is None:
                self._logger.error("No output characteristic found")
                return

            self._logger.debug("Starting notify")
            await self._client.start_notify(chr_output, output_listener)
            return

        self._logger.error("Output service not found")

    @property
    def is_connected(self) -> bool:
        """
        ``True`` if the desk is connected.

        >>> async def example() -> bool:
        ...     async with IdasenDesk(mac="AA:AA:AA:AA:AA:AA") as desk:
        ...         return desk.is_connected
        >>> asyncio.run(example())
        True
        """
        return self._client.is_connected

    @property
    def is_moving(self) -> bool:
        """
        ``True`` if the desk is currently being moved by this class.
        """
        return self._moving

    @property
    def mac(self) -> str:
        """
        Desk MAC address.

        >>> async def example() -> str:
        ...     async with IdasenDesk(mac="AA:AA:AA:AA:AA:AA") as desk:
        ...         return desk.mac
        >>> asyncio.run(example())
        'AA:AA:AA:AA:AA:AA'
        """
        return self._mac

    async def wakeup(self):
        """
        Wakeup the controller from sleep.

        This exists for compatibility with the Linak DPG1C controller,
        it is not necessary with the original idasen controller.

        >>> async def example():
        ...     async with IdasenDesk(mac="AA:AA:AA:AA:AA:AA") as desk:
        ...         await desk.wakeup()
        >>> asyncio.run(example())
        """
        # https://github.com/rhyst/linak-controller/issues/32#issuecomment-1784055470
        await self._client.write_gatt_char(_UUID_DPG, b"\x7F\x86\x00")
        await self._client.write_gatt_char(
            _UUID_DPG,
            b"\x7F\x86\x80\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0A\x0B\x0C\x0D"
            b"\x0E\x0F\x10\x11",
        )
        await self._client.write_gatt_char(_UUID_COMMAND, _COMMAND_WAKEUP)

    async def move_up(self):
        """
        Move the desk upwards.

        This command moves the desk upwards for a fixed duration
        (approximately one second) as set by your desk controller.

        >>> async def example():
        ...     async with IdasenDesk(mac="AA:AA:AA:AA:AA:AA") as desk:
        ...         await desk.move_up()
        >>> asyncio.run(example())
        """
        await self._client.write_gatt_char(_UUID_COMMAND, _COMMAND_UP, response=False)

    async def move_down(self):
        """
        Move the desk downwards.

        This command moves the desk downwards for a fixed duration
        (approximately one second) as set by your desk controller.

        >>> async def example():
        ...     async with IdasenDesk(mac="AA:AA:AA:AA:AA:AA") as desk:
        ...         await desk.move_down()
        >>> asyncio.run(example())
        """
        await self._client.write_gatt_char(_UUID_COMMAND, _COMMAND_DOWN, response=False)

    async def move_to_target(self, target: float):
        """
        Move the desk to the target position.

        Args:
            target: Target position in meters.

        Raises:
            ValueError: Target exceeds maximum or minimum limits.

        >>> async def example():
        ...     async with IdasenDesk(mac="AA:AA:AA:AA:AA:AA") as desk:
        ...         await desk.move_to_target(1.1)
        >>> asyncio.run(example())
        """
        if target > self.MAX_HEIGHT:
            raise ValueError(
                f"target position of {target:.3f} meters exceeds maximum of "
                f"{self.MAX_HEIGHT:.3f}"
            )
        elif target < self.MIN_HEIGHT:
            raise ValueError(
                f"target position of {target:.3f} meters exceeds minimum of "
                f"{self.MIN_HEIGHT:.3f}"
            )

        if self._moving:
            self._logger.error("Already moving")
            return
        self._moving = True

        async def do_move() -> None:
            current_height = await self.get_height()
            if current_height == target:
                return

            # Wakeup and stop commands are needed in order to
            # start the reference input for setting the position
            await self._client.write_gatt_char(_UUID_COMMAND, _COMMAND_WAKEUP)
            await self._client.write_gatt_char(_UUID_COMMAND, _COMMAND_STOP)

            data = _meters_to_bytes(target)

            while self._moving:
                await self._client.write_gatt_char(_UUID_REFERENCE_INPUT, data)
                await asyncio.sleep(0.2)

                # Stop as soon as the speed is 0,
                # which means the desk has reached the target position
                speed = await self.get_speed()
                if speed == 0:
                    break

        self._move_task = asyncio.create_task(do_move())
        await self._move_task
        self._moving = False

    async def stop(self):
        """Stop desk movement."""
        self._moving = False
        if self._move_task:
            self._logger.debug("Desk was moving, waiting for it to stop")
            await self._move_task

        await self._stop()

    async def _stop(self):
        """Send stop commands"""
        self._logger.debug("Sending stop commands")
        await asyncio.gather(
            self._client.write_gatt_char(_UUID_COMMAND, _COMMAND_STOP, response=False),
            self._client.write_gatt_char(
                _UUID_REFERENCE_INPUT, _COMMAND_REFERENCE_INPUT_STOP, response=False
            ),
        )

    async def get_height(self) -> float:
        """
        Get the desk height in meters.

        Returns:
            Desk height in meters.

        >>> async def example() -> float:
        ...     async with IdasenDesk(mac="AA:AA:AA:AA:AA:AA") as desk:
        ...         await desk.move_to_target(1.0)
        ...         return await desk.get_height()
        >>> asyncio.run(example())
        1.0
        """
        height, _ = await self.get_height_and_speed()
        return height

    async def get_speed(self) -> float:
        """
        Get the desk speed in meters per second.

        Returns:
            Desk speed in meters per second.

        >>> async def example() -> float:
        ...     async with IdasenDesk(mac="AA:AA:AA:AA:AA:AA") as desk:
        ...         await desk.move_to_target(1.0)
        ...         return await desk.get_speed()
        >>> asyncio.run(example())
        0.0
        """
        _, speed = await self.get_height_and_speed()
        return speed

    async def get_height_and_speed(self) -> Tuple[float, float]:
        """
        Get the desk height in meters and speed in meters per second.

        Returns:
            Tuple of desk height in meters and speed in meters per second.

        >>> async def example() -> [float, float]:
        ...     async with IdasenDesk(mac="AA:AA:AA:AA:AA:AA") as desk:
        ...         await desk.move_to_target(1.0)
        ...         return await desk.get_height_and_speed()
        >>> asyncio.run(example())
        (1.0, 0.0)
        """
        raw = await self._client.read_gatt_char(_UUID_HEIGHT)
        return _bytes_to_meters_and_speed(raw)

    @staticmethod
    async def discover() -> Optional[str]:
        """
        Try to find the desk's MAC address by discovering currently connected devices.

        Returns:
            MAC address if found, ``None`` if not found.

        >>> asyncio.run(IdasenDesk.discover())
        'AA:AA:AA:AA:AA:AA'
        """
        try:
            device = await BleakScanner.find_device_by_filter(_is_desk)
        except Exception:
            return None

        if device is None:
            return None

        return device.address
