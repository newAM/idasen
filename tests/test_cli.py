from idasen import cli
from idasen import IdasenDesk
from idasen.cli import count_to_level
from idasen.cli import DEFAULT_CONFIG
from idasen.cli import from_config
from idasen.cli import get_parser
from idasen.cli import init
from idasen.cli import load_config
from idasen.cli import main
from idasen.cli import pair
from idasen.cli import subcommand_to_callable
from idasen.cli import xdg_config_home
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from typing import Dict
from typing import Optional
from unittest import mock
from unittest.mock import patch
import argparse
import logging
import os
import platform
import pytest
import sys
import yaml


@pytest.mark.parametrize(
    ("env", "output"),
    [
        pytest.param(None, Path.home() / ".config", id="none"),
        pytest.param("", Path.home() / ".config", id="empty_string"),
        pytest.param("/abs/../path", Path("/abs/../path"), id="traversal"),
        pytest.param("relative/path", Path.home() / ".config", id="relative"),
        pytest.param("/home/user/CONFIG", Path("/home/user/CONFIG"), id="absolute"),
    ],
)
def test_xdg_config_home(env: Optional[str], output: Path):
    if env is None:
        test_env = {}
    else:
        test_env = {"XDG_CONFIG_HOME": env}
    with patch.dict(os.environ, test_env):
        assert xdg_config_home() == output


def test_get_parser_smoke():
    assert isinstance(get_parser(DEFAULT_CONFIG), argparse.ArgumentParser)


def test_load_config_no_file():
    assert load_config("not_a_real_file_path") == {}


def test_load_config_invalid_schema(tmpdir: str):
    file_path = os.path.join(tmpdir, "config.yaml")
    with open(file_path, "w") as f:
        f.write("extra_key: 456\n")

    with pytest.raises(SystemExit):
        load_config(file_path)


def test_load_config_reserved_position(tmpdir: str):
    file_path = os.path.join(tmpdir, "config.yaml")
    config: Dict[str, Any] = {
        "mac_address": "AA:AA:AA:AA:AA:AA",
        "positions": {"sit": 0.90},
    }

    with open(file_path, "w") as f:
        yaml.dump(config, f)

    assert load_config(file_path) == config

    config["positions"]["init"] = 0.90

    with open(file_path, "w") as f:
        yaml.dump(config, f)

    with pytest.raises(SystemExit):
        load_config(file_path)


async def test_init_exists_no_force():
    with mock.patch.object(os.path, "isfile", return_value=True):
        assert await init(args=argparse.Namespace(force=False)) == 1


@pytest.mark.parametrize("discover_return", ["AA:AA:AA:AA:AA:AA", None])
async def test_init(discover_return: Optional[str]):
    with (
        mock.patch.object(os.path, "isfile", return_value=True),
        mock.patch.object(yaml, "dump") as dump_mock,
        mock.patch.object(
            IdasenDesk,
            "discover",
            return_value=discover_return,
        ),
        mock.patch.object(os, "makedirs"),
        mock.patch("builtins.open"),
    ):
        assert await init(args=argparse.Namespace(force=True)) == 0
        dump_mock.assert_called_once()


async def test_pair():
    with (
        mock.patch.object(IdasenDesk, "disconnect", side_effect=None),
        mock.patch.object(IdasenDesk, "connect", side_effect=None),
        mock.patch.object(IdasenDesk, "pair", side_effect=None),
        mock.patch.object(IdasenDesk, "__init__", return_value=None),
    ):
        assert await pair(args=argparse.Namespace(mac_address="a")) is None


async def test_pair_darwin():
    with (
        mock.patch.object(IdasenDesk, "disconnect", side_effect=None),
        mock.patch.object(IdasenDesk, "connect", side_effect=None),
        mock.patch.object(IdasenDesk, "pair", side_effect=NotImplementedError),
        mock.patch.object(platform, "system", return_value="Darwin"),
        mock.patch.object(IdasenDesk, "__init__", return_value=None),
    ):
        assert await pair(args=argparse.Namespace(mac_address="a")) == 1


async def test_pair_not_darwin():
    with (
        mock.patch.object(IdasenDesk, "disconnect", side_effect=None),
        mock.patch.object(IdasenDesk, "connect", side_effect=None),
        mock.patch.object(IdasenDesk, "pair", side_effect=NotImplementedError),
        mock.patch.object(platform, "system", return_value="NotDarwin"),
        mock.patch.object(IdasenDesk, "__init__", return_value=None),
        pytest.raises(NotImplementedError),
    ):
        await pair(args=argparse.Namespace(mac_address="a"))


class Parser:
    def __init__(self):
        self.error_called = False

    def error(self, msg: str):  # noqa: ARG002
        self.error_called = True


def test_from_config_empty():
    from_config(SimpleNamespace(), {}, Parser(), "")


def test_from_config_cli_set_config_unset():
    args = SimpleNamespace(mac_address="a")
    from_config(args, {}, Parser(), "mac_address")
    assert args.mac_address == "a"


def test_from_config_cli_unset_config_set():
    args = SimpleNamespace(mac_address=None)
    from_config(args, {"mac_address": "b"}, Parser(), "mac_address")
    assert args.mac_address == "b"


def test_from_config_both_set():
    args = SimpleNamespace(mac_address="a")
    from_config(args, {"mac_address": "b"}, Parser(), "mac_address")
    assert args.mac_address == "a"


def test_from_config_none_set():
    parser = Parser()
    from_config(SimpleNamespace(mac_address=None), {}, parser, "mac_address")
    assert parser.error_called is True


@pytest.mark.parametrize(
    "count, level",
    [
        (0, logging.CRITICAL),
        (1, logging.ERROR),
        (2, logging.WARNING),
        (3, logging.INFO),
        (4, logging.DEBUG),
        (5, logging.DEBUG),
    ],
)
def test_count_to_level(count: int, level: int):
    assert count_to_level(count) == level


seen_it = []


@pytest.mark.parametrize(
    "sub",
    ["init", "pair", "monitor", "sit", "height", "speed", "stand", "save", "delete"],
)
def test_subcommand_to_callable(sub: str):
    global seen_it

    func = subcommand_to_callable(sub, DEFAULT_CONFIG)
    assert callable(func)
    assert func not in seen_it
    seen_it.append(func)


def test_main_to_exit():
    mock_args = SimpleNamespace(sub="not_a_real_sub_command", version=False, verbose=0)

    async def do_nothing(args: argparse.Namespace):
        assert args == mock_args

    with (
        mock.patch.object(
            argparse.ArgumentParser,
            "parse_args",
            return_value=mock_args,
        ),
        mock.patch.object(cli, "subcommand_to_callable", return_value=do_nothing),
        mock.patch.object(sys, "exit") as sys_exit_mock,
    ):
        main()
        sys_exit_mock.assert_called_once_with(0)


def test_main_internal_error():
    with (
        mock.patch.object(
            argparse.ArgumentParser,
            "parse_args",
            return_value=SimpleNamespace(
                sub="not_a_real_sub_command", version=False, verbose=0
            ),
        ),
        pytest.raises(AssertionError),
    ):
        main()


@pytest.mark.parametrize(
    "sub",
    [
        "init",
        "pair",
        "monitor",
        "sit",
        "height",
        "speed",
        "stand",
        "add",
        "delete",
        None,
    ],
)
def test_main_version(sub: Optional[str]):
    with (
        mock.patch.object(
            argparse.ArgumentParser,
            "parse_args",
            return_value=SimpleNamespace(sub=sub, version=True, verbose=0, force=False),
        ),
        mock.patch.object(sys, "exit") as sys_exit_mock,
    ):
        main()
        sys_exit_mock.assert_called_once_with(0)


def test_main_no_sub():
    with (
        mock.patch.object(
            argparse.ArgumentParser,
            "parse_args",
            return_value=SimpleNamespace(
                sub=None, version=False, verbose=0, force=False
            ),
        ),
        mock.patch.object(sys, "exit") as sys_exit_mock,
    ):
        main()
        sys_exit_mock.assert_called_once_with(1)
