from bleak import BleakClient
from bleak import discover
from typing import Dict
from typing import Optional
from typing import Tuple
import asyncio
import logging


_UUID_HEIGHT: str = "99fa0021-338a-1024-8a49-009c0215f78a"
_UUID_COMMAND: str = "99fa0002-338a-1024-8a49-009c0215f78a"
_UUID_REFERENCE_INPUT: str = "99fa0031-338a-1024-8a49-009c0215f78a"

_COMMAND_REFERENCE_INPUT_STOP: bytearray = bytearray([0x01, 0x80])
_COMMAND_UP: bytearray = bytearray([0x47, 0x00])
_COMMAND_DOWN: bytearray = bytearray([0x46, 0x00])
_COMMAND_STOP: bytearray = bytearray([0xFF, 0x00])

# height calculation offset in meters, assumed to be the same for all desks


def _bytes_to_meters(raw: bytearray) -> float:
    """ Converts a value read from the desk in bytes to meters. """
    raw_len = len(raw)
    expected_len = 4
    assert (
        raw_len == expected_len
    ), f"Expected raw value to be {expected_len} bytes long, got {raw_len} bytes"

    high_byte = int(raw[1])
    low_byte = int(raw[0])
    raw = (high_byte << 8) + low_byte
    return float(raw / 10000) + IdasenDesk.MIN_HEIGHT


class _DeskLoggingAdapter(logging.LoggerAdapter):
    """ Prepends logging messages with the desk MAC address. """

    def process(self, msg: str, kwargs: Dict[str, str]) -> Tuple[str, Dict[str, str]]:
        return f"[{self.extra['mac']}] {msg}", kwargs


class IdasenDesk:
    """
    Idasen desk.

    Args:
        mac: Bluetooth MAC address of the desk.

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

    def __init__(self, mac: str):
        self._logger = _DeskLoggingAdapter(
            logger=logging.getLogger(__name__), extra={"mac": mac}
        )
        self._mac = mac
        self._client = BleakClient(self._mac)

    async def __aenter__(self):
        await self._client.__aenter__()
        return self

    async def __aexit__(self, *args, **kwargs) -> Optional[bool]:
        return await self._client.__aexit__(*args, **kwargs)

    async def is_connected(self) -> bool:
        """
        Check connection status of the desk.

        Returns:
            Boolean representing connection status.

        >>> async def example() -> bool:
        ...     async with IdasenDesk(mac="AA:AA:AA:AA:AA:AA") as desk:
        ...         return await desk.is_connected()
        >>> asyncio.run(example())
        True
        """
        return await self._client.is_connected()

    @property
    def mac(self) -> str:
        """ Desk MAC address. """
        return self._mac

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

        while True:
            height = await self.get_height()
            difference = target - height
            self._logger.debug(f"{target=} {height=} {difference=}")
            if abs(difference) < 0.005:  # tolerance of 0.005 meters
                self._logger.info(f"reached target of {target:.3f}")
                await self.stop()
                return
            elif difference > 0:
                await self.move_up()
            elif difference < 0:
                await self.move_down()

    async def stop(self):
        """ Stop desk movement. """
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
        return _bytes_to_meters(await self._client.read_gatt_char(_UUID_HEIGHT))

    @classmethod
    async def discover(cls) -> Optional[str]:
        """
        Try to find the desk's MAC address by discovering currently connected devices.

        Returns:
            MAC address if found, ``None`` if not found.
        """
        try:
            devices = await discover()
        except Exception:
            return None
        return next(
            (device.address for device in devices if device.name.startswith("Desk")),
            None,
        )
