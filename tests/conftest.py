import pytest
from db import DB
from .common import *
import glob


all_tables = {
    "a": TableA,
    "b": TableB,
    "b2": TableB_NullableFK,
    "c": TableC,
    "d": TableD,
}


@pytest.fixture
def tables():
    return list(all_tables.keys())


@pytest.fixture
def db(tables):
    _db = DB([all_tables[x] for x in tables])
    yield _db
    _db.close()


@pytest.fixture(autouse=True)
def cleanup():
    yield
    for f in glob.glob("tests/tmp/*.dat"):
        os.remove(f)
    for f in glob.glob("tests/tmp/*.idx*"):
        os.remove(f)


def pytest_make_parametrize_id(config, val):
    if isinstance(val, bytes):
        return repr(val).replace(r"\x00", r"⦰")
    return None
