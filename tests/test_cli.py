from idasen import cli
from idasen.cli import count_to_level
from idasen.cli import from_config
from idasen.cli import get_parser
from idasen.cli import init
from idasen.cli import load_config
from idasen.cli import main
from idasen.cli import subcommand_to_callable
from types import SimpleNamespace
from unittest import mock
import argparse
import logging
import os
import pytest
import sys
import yaml


def test_get_parser_smoke():
    assert isinstance(get_parser(), argparse.ArgumentParser)


def test_load_config_no_file():
    assert load_config("not_a_real_file_path") == {}


def test_load_config_invalid_schema(tmpdir: str):
    file_path = os.path.join(tmpdir, "config.yaml")
    with open(file_path, "w") as f:
        f.write("extra_key: 456\n")

    with pytest.raises(SystemExit):
        load_config(file_path)


@pytest.mark.asyncio
async def test_init_exists_no_force():
    with mock.patch.object(os.path, "isfile", return_value=True):
        assert await init(args=SimpleNamespace(force=False)) == 1


@pytest.mark.asyncio
async def test_init():
    with mock.patch.object(os.path, "isfile", return_value=True), mock.patch.object(
        yaml, "dump"
    ) as dump_mock, mock.patch("builtins.open"):
        assert await init(args=SimpleNamespace(force=True)) == 0
        dump_mock.assert_called_once()


class Parser:
    def __init__(self):
        self.error_called = False

    def error(self, msg: str):
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


@pytest.mark.parametrize("sub", ["init", "monitor", "sit", "height", "stand"])
def test_subcommand_to_callable(sub: str):
    global seen_it

    func = subcommand_to_callable(sub)
    assert callable(func)
    assert func not in seen_it
    seen_it.append(func)


def test_main_to_exit():
    mock_args = SimpleNamespace(sub="not_a_real_sub_command", verbose=0)

    async def do_nothing(args: argparse.Namespace):
        assert args == mock_args

    with mock.patch.object(
        argparse.ArgumentParser,
        "parse_args",
        return_value=mock_args,
    ), mock.patch.object(
        cli, "subcommand_to_callable", return_value=do_nothing
    ), mock.patch.object(
        sys, "exit"
    ) as sys_exit_mock:
        main()
        sys_exit_mock.assert_called_once_with(0)


def test_main_internal_error():
    with mock.patch.object(
        argparse.ArgumentParser,
        "parse_args",
        return_value=SimpleNamespace(sub="not_a_real_sub_command", verbose=0),
    ), pytest.raises(AssertionError):
        main()
