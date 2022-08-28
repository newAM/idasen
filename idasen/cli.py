import functools

from . import IdasenDesk
from typing import Any
from typing import Callable
from typing import Dict
from typing import List
from typing import Optional
import argparse
import asyncio
import importlib.metadata
import logging
import os
import sys
import voluptuous as vol
import yaml

HOME = os.path.expanduser("~")
IDASEN_CONFIG_DIRECTORY = os.path.join(HOME, ".config", "idasen")
IDASEN_CONFIG_PATH = os.path.join(IDASEN_CONFIG_DIRECTORY, "idasen.yaml")

DEFAULT_CONFIG: Dict[str, Any] = {
    "positions": {"stand": 1.1, "sit": 0.75},
    "mac_address": "AA:AA:AA:AA:AA:AA",
}

CONFIG_SCHEMA = vol.Schema(
    {
        "mac_address": vol.All(str, vol.Length(min=17, max=17)),
        "positions": {
            str: vol.All(
                vol.Any(float, int),
                vol.Range(min=IdasenDesk.MIN_HEIGHT, max=IdasenDesk.MAX_HEIGHT),
            )
        },
    },
    extra=False,
)

RESERVED_NAMES = {"init", "monitor", "height", "save", "delete"}


def save_config(config: dict, path: str = IDASEN_CONFIG_PATH):
    with open(path, "w") as f:
        yaml.dump(config, f)


def load_config(path: str = IDASEN_CONFIG_PATH) -> dict:
    """Load user config."""
    try:
        with open(path, "r") as f:
            config = yaml.load(f, Loader=yaml.FullLoader)
    except FileNotFoundError:
        return {}

    # convert old config file format
    if "positions" not in config:
        config["positions"] = dict()
        config["positions"]["sit"] = config.pop(
            "sit_height", DEFAULT_CONFIG["positions"]["sit"]
        )
        config["positions"]["stand"] = config.pop(
            "stand_height", DEFAULT_CONFIG["positions"]["stand"]
        )

        save_config(config, path)

    try:
        config = CONFIG_SCHEMA(config)
    except vol.Invalid as e:
        print(f"Invalid configuration: {e}", file=sys.stderr)
        sys.exit(1)
    else:
        for position in config["positions"]:
            if position in RESERVED_NAMES:
                print(
                    "Invalid configuration, "
                    f"position with name '{position}' is a reserved name.",
                    file=sys.stderr,
                )
                sys.exit(1)

        return config


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
    parser.add_argument(
        "--version", action="store_true", help="Prints version information."
    )


def get_parser(config: dict) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="ikea IDÅSEN desk control")
    add_common_args(parser)
    sub = parser.add_subparsers(dest="sub", help="Subcommands", required=False)

    height_parser = sub.add_parser("height", help="Get the desk height.")
    monitor_parser = sub.add_parser("monitor", help="Monitor the desk position.")
    init_parser = sub.add_parser("init", help="Initialize a new configuration file.")
    save_parser = sub.add_parser("save", help="Save current desk position.")
    save_parser.add_argument("name", help="Position name")
    delete_parser = sub.add_parser("delete", help="Remove position with given name.")
    delete_parser.add_argument("name", help="Position name")

    positions = config.get("positions", {})
    for name, value in positions.items():
        subcommand = sub.add_parser(name, help=f"Move the desk to {value}m.")
        add_common_args(subcommand)

    init_parser.add_argument(
        "-f",
        "--force",
        action="store_true",
        help="Overwrite any existing configuration files.",
    )

    add_common_args(init_parser)
    add_common_args(height_parser)
    add_common_args(monitor_parser)
    add_common_args(save_parser)
    add_common_args(delete_parser)

    return parser


async def init(args: argparse.Namespace) -> int:
    if not args.force and os.path.isfile(IDASEN_CONFIG_PATH):
        print("Configuration file already exists.", file=sys.stderr)
        print("Use --force to overwrite existing configuration.", file=sys.stderr)
        return 1
    else:
        mac = await IdasenDesk.discover()
        if mac is not None:
            print(f"Discovered desk's MAC address: {mac}", file=sys.stderr)
            DEFAULT_CONFIG["mac_address"] = mac
        else:
            print("Failed to discover desk's MAC address", file=sys.stderr)
        os.makedirs(IDASEN_CONFIG_DIRECTORY, exist_ok=True)
        with open(IDASEN_CONFIG_PATH, "w") as f:
            f.write("# https://newam.github.io/idasen/index.html#configuration\n")
            yaml.dump(DEFAULT_CONFIG, f)
        print(
            f"Created new configuration file at: {IDASEN_CONFIG_PATH}", file=sys.stderr
        )

    return 0


async def monitor(args: argparse.Namespace) -> None:
    try:
        async with IdasenDesk(args.mac_address, exit_on_fail=True) as desk:
            previous_height = 0.0
            while True:
                height = await desk.get_height()
                if abs(height - previous_height) > 0.001:
                    print(f"{height:.3f} meters", flush=True)
                previous_height = height
    except KeyboardInterrupt:
        pass


async def height(args: argparse.Namespace):
    async with IdasenDesk(args.mac_address, exit_on_fail=True) as desk:
        height = await desk.get_height()
        print(f"{height:.3f} meters")


async def move_to(args: argparse.Namespace, position: float) -> None:
    async with IdasenDesk(args.mac_address, exit_on_fail=True) as desk:
        await desk.move_to_target(target=position)


async def save(args: argparse.Namespace, config: dict) -> int:
    if args.name in RESERVED_NAMES:
        print(f"Position with name '{args.name}' is a reserved name.", file=sys.stderr)
        return 1

    async with IdasenDesk(args.mac_address, exit_on_fail=True) as desk:
        height = await desk.get_height()

    config["positions"][args.name] = height
    save_config(config)

    print(f"Saved position '{args.name}' with height: {height}m.")
    return 0


async def delete(args: argparse.Namespace, config: dict) -> int:
    position = config["positions"].pop(args.name, None)
    if args.name in RESERVED_NAMES:
        print(f"Position with name '{args.name}' is a reserved name.", file=sys.stderr)
        return 1
    elif position is None:
        print(f"Position with name '{args.name}' doesn't exist.", file=sys.stderr)
    else:
        save_config(config)
        print(f"Position with name '{args.name}' removed.")

    return 0


def from_config(
    args: argparse.Namespace,
    config: dict,
    parser: argparse.ArgumentParser,
    key: str,
    raise_error: bool = True,
):
    if hasattr(args, key) and getattr(args, key) is None:
        if key in config:
            setattr(args, key, config[key])
        elif raise_error:
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


def subcommand_to_callable(sub: str, config: dict) -> Callable:
    if sub == "init":
        return init
    elif sub == "monitor":
        return monitor
    elif sub == "height":
        return height
    elif sub == "save":
        return functools.partial(save, config=config)
    elif sub == "delete":
        return functools.partial(delete, config=config)
    elif sub in config.get("positions", {}):
        position = config["positions"][sub]
        return functools.partial(move_to, position=position)
    else:
        raise AssertionError(f"internal error, please report this bug {sub=}")


def main(argv: Optional[List[str]] = None):
    config = load_config()
    parser = get_parser(config)
    args = parser.parse_args(argv)

    from_config(args, config, parser, "mac_address", raise_error=args.sub != "init")

    level = count_to_level(args.verbose)

    root_logger = logging.getLogger()

    handler = logging.StreamHandler(stream=sys.stderr)
    handler.setLevel(level)
    formatter = logging.Formatter("{levelname} {name} {message}", style="{")
    handler.setFormatter(formatter)
    root_logger.addHandler(handler)
    root_logger.setLevel(level)

    if args.version:
        version = importlib.metadata.version("idasen")
        print(version)
        sys.exit(0)
    elif args.sub is None:
        print("A subcommand is required")
        parser.print_usage()
        sys.exit(1)
    else:

        func = subcommand_to_callable(args.sub, config)

        rc = asyncio.run(func(args))

        if rc is None:
            rc = 0

        sys.exit(rc)


if __name__ == "__main__":
    main()
