import pytest

from .conftest import TEST_BASE_DIR

p = pytest.mark.parametrize


def use_tables(*tables):
    return p("tables", [[*tables]])


def assert_file_contents(fname, expected):
    with open(f"{TEST_BASE_DIR}/{fname}", "rb") as f:
        actual = f.read()
        assert actual == expected, f"{actual=}, {expected=}"


def set_file_contents(fname, contents):
    with open(f"{TEST_BASE_DIR}/{fname}", "wb") as f:
        f.write(contents)
