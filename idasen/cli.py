from . import IdasenDesk
from typing import Callable
from typing import List
from typing import Optional
import argparse
import asyncio
import logging
import os
import sys
import voluptuous as vol
import yaml

home = os.path.expanduser("~")
idasen_config_directory = os.path.join(home, ".config", "idasen")
idasen_config_path = os.path.join(idasen_config_directory, "idasen.yaml")

default_config = {
    "stand_height": 1.1,
    "sit_height": 0.75,
    "mac_address": "AA:AA:AA:AA:AA:AA",
}

config_schema = vol.Schema(
    {
        "mac_address": vol.All(str, vol.Length(min=17, max=17)),
        "stand_height": vol.All(
            vol.Any(float, int),
            vol.Range(min=IdasenDesk.MIN_HEIGHT, max=IdasenDesk.MAX_HEIGHT),
        ),
        "sit_height": vol.All(
            vol.Any(float, int),
            vol.Range(min=IdasenDesk.MIN_HEIGHT, max=IdasenDesk.MAX_HEIGHT),
        ),
    },
    extra=False,
)


def load_config(path: str = idasen_config_path) -> dict:
    """ Load user config. """
    try:
        with open(path, "r") as f:
            config = yaml.load(f, Loader=yaml.FullLoader)
    except FileNotFoundError:
        return {}

    try:
        return config_schema(config)
    except vol.Invalid as e:
        sys.stderr.write(f"Invalid configuration: {e}\n")
        sys.exit(1)


def add_common_args(parser: argparse.ArgumentParser):
    parser.add_argument(
        "--mac-address",
        dest="mac_address",
        type=str,
        help="MAC address of the Idasen desk.",
    )
    parser.add_argument(
        "--verbose", "-v", action="count", default=0, help="Increase logging verbosity."
    )


def get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="ikea IDÅSEN desk control")
    sub = parser.add_subparsers(dest="sub", help="Subcommands", required=True)

    height_parser = sub.add_parser("height", help="Get the desk height.")
    monitor_parser = sub.add_parser("monitor", help="Monitor the desk position.")
    sit_parser = sub.add_parser("sit", help="Move the desk to a sitting position.")
    stand_parser = sub.add_parser("stand", help="Move the desk to a standing position.")
    init_parser = sub.add_parser("init", help="Initialize a new configuration file.")

    stand_parser.add_argument(
        "--stand-height", type=float, help="Standing height in meters."
    )

    sit_parser.add_argument(
        "--sit-height", type=float, help="Sitting height in meters."
    )

    init_parser.add_argument(
        "-f",
        "--force",
        action="store_true",
        help="Overwrite any existing configuration files.",
    )

    add_common_args(height_parser)
    add_common_args(monitor_parser)
    add_common_args(sit_parser)
    add_common_args(stand_parser)

    return parser


async def init(args: argparse.Namespace) -> int:
    if not args.force and os.path.isfile(idasen_config_path):
        sys.stderr.write("Configuration file already exists.\n")
        sys.stderr.write("Use --force to overwrite existing configuration.\n")
        return 1
    else:
        mac = await IdasenDesk.discover()
        if mac is not None:
            sys.stderr.write(f"Discovered desk's MAC address: {mac}")
            default_config["mac_address"] = mac
        else:
            sys.stderr.write("Failed to discover desk's MAC address")
        os.makedirs(idasen_config_directory, exist_ok=True)
        with open(idasen_config_path, "w") as f:
            f.write(
                "# https://idasen.readthedocs.io/en/latest/index.html#configuration\n"
            )
            yaml.dump(default_config, f)
        sys.stderr.write(f"Created new configuration file at: {idasen_config_path}")

    return 0


async def monitor(args: argparse.Namespace) -> int:
    try:
        async with IdasenDesk(args.mac_address) as desk:
            previous_height = 0.0
            while True:
                height = await desk.get_height()
                if abs(height - previous_height) > 0.001:
                    sys.stdout.write(f"{height:.3f} meters\n")
                    sys.stdout.flush()
                previous_height = height
    except KeyboardInterrupt:
        pass


async def height(args: argparse.Namespace):
    async with IdasenDesk(args.mac_address) as desk:
        height = await desk.get_height()
        sys.stdout.write(f"{height:.3f} meters\n")


async def stand(args: argparse.Namespace):
    async with IdasenDesk(args.mac_address) as desk:
        await desk.move_to_target(target=args.stand_height)


async def sit(args: argparse.Namespace):
    async with IdasenDesk(args.mac_address) as desk:
        await desk.move_to_target(target=args.sit_height)


def from_config(
    args: argparse.Namespace, config: dict, parser: argparse.ArgumentParser, key: str
):
    if hasattr(args, key) and getattr(args, key) is None:
        if key in config:
            setattr(args, key, config[key])
        else:
            parser.error(f"{key} must be provided via the CLI or the config file")


def count_to_level(count: int) -> int:
    if count == 1:
        return logging.ERROR
    elif count == 2:
        return logging.WARNING
    elif count == 3:
        return logging.INFO
    elif count >= 4:
        return logging.DEBUG

    return logging.CRITICAL


def subcommand_to_callable(sub: str) -> Callable:
    if sub == "init":
        return init
    elif sub == "monitor":
        return monitor
    elif sub == "sit":
        return sit
    elif sub == "height":
        return height
    elif sub == "stand":
        return stand
    else:
        raise AssertionError(f"internal error, please report this bug {sub=}")


def main(args: Optional[List[str]] = None):
    parser = get_parser()
    args = parser.parse_args(args)
    config = load_config()

    from_config(args, config, parser, "mac_address")
    from_config(args, config, parser, "stand_height")
    from_config(args, config, parser, "sit_height")

    level = count_to_level(args.verbose)

    root_logger = logging.getLogger()

    handler = logging.StreamHandler(stream=sys.stderr)
    handler.setLevel(level)
    formatter = logging.Formatter("{levelname} {name} {message}", style="{")
    handler.setFormatter(formatter)
    root_logger.addHandler(handler)
    root_logger.setLevel(level)

    func = subcommand_to_callable(args.sub)

    rc = asyncio.run(func(args))

    if rc is None:
        rc = 0

    sys.exit(rc)


if __name__ == "__main__":
    main()
