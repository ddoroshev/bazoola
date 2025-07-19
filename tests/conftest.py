import glob
import os

import pytest

from bazoola import DB

from .common import *

TEST_BASE_DIR = "tests/tmp"

all_tables = {
    "a": TableA,
    "b": TableB,
    "b2": TableB_NullableFK,
    "c": TableC,
    "d": TableD,
    "e": TableE,
}


@pytest.fixture
def tables():
    return list(all_tables.keys())


@pytest.fixture
def db(tables):
    _db = DB([all_tables[x] for x in tables], base_dir=TEST_BASE_DIR)
    yield _db
    _db.close()


@pytest.fixture(autouse=True)
def cleanup():
    yield
    for f in glob.glob(f"{TEST_BASE_DIR}/*.dat"):
        os.remove(f)
    for f in glob.glob(f"{TEST_BASE_DIR}/.lock"):
        os.remove(f)


def pytest_make_parametrize_id(config, val):
    if isinstance(val, bytes):
        return repr(val).replace(r"\x00", r"⦰")
    return None
