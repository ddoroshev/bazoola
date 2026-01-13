# ignore: F405
import pytest

from bazoola import *

from .common import *
from .conftest import TEST_BASE_DIR
from .util import *


def test_table_open_first():
    db = DB([TableA], base_dir=TEST_BASE_DIR)

    assert_file_contents("a.dat", b"")

    db.close()


def test_table_open_second():
    db1 = DB([TableA], base_dir=TEST_BASE_DIR)
    db1.close()

    db2 = DB([TableA], base_dir=TEST_BASE_DIR)

    assert_file_contents("a.dat", b"")

    db2.close()


def test_db_open_close():
    db = DB([TableA, TableB], base_dir=TEST_BASE_DIR)
    db.close()

    assert_file_contents("a.dat", b"")
    assert_file_contents("b.dat", b"")


@use_tables("a")
@p("text", [b"foo", "foo"])
def test_db_insert_assign_id(db, text):
    a = db.insert("a", {"text": text})

    assert a["id"] == 1
    assert_file_contents("a.dat", b"1     foo  \n")


@use_tables("a")
def test_db_insert_with_id(db):
    a = db.insert("a", {"id": 10, "text": "a"})

    assert a["id"] == 10
    assert_file_contents("a.dat", b"10    a    \n")


@use_tables("a")
def test_db_insert_with_id_twice(db):
    db.insert("a", {"id": 10, "text": "a"})

    with pytest.raises(ValidationError, match="'id': row with id 10 already exists"):
        db.insert("a", {"id": 10, "text": "a"})

    assert_file_contents("a.dat", b"10    a    \n")


@use_tables("a")
def test_db_insert_with_id_then_without(db):
    db.insert("a", {"id": 10, "text": "a"})

    res = db.insert("a", {"text": "b"})

    assert res["id"] == 1
    assert_file_contents("a.dat", b"10    a    \n1     b    \n")


@use_tables("c")
def test_db_insert_not_none_error(db):
    with pytest.raises(ValidationError, match="'varchar': The value can't be None"):
        db.insert("c", {"varchar": None, "int": None})

    assert_file_contents("c.dat", b"")


@use_tables("c")
def test_db_insert_varchar_size_error(db):
    with pytest.raises(ValidationError, match="'varchar': The value is too long"):
        db.insert("c", {"varchar": "a" * 11, "int": 1})

    assert_file_contents("c.dat", b"")


@use_tables("c")
def test_db_insert_varchar_type_error(db):
    with pytest.raises(ValidationError, match="'varchar': Type mismatch"):
        db.insert("c", {"varchar": 11, "int": 1})

    assert_file_contents("c.dat", b"")


@use_tables("c")
def test_db_insert_int_size_error(db):
    with pytest.raises(ValidationError, match="'int': The value is too big"):
        db.insert("c", {"varchar": "a", "int": 9999999})

    assert_file_contents("c.dat", b"")


@use_tables("c")
def test_db_insert_int_type_error(db):
    with pytest.raises(ValidationError, match="'int': Type mismatch"):
        db.insert("c", {"varchar": "a", "int": "abc"})

    assert_file_contents("c.dat", b"")


@use_tables("d")
@p(
    ("values", "expected", "expected_contents"),
    [
        (
            {},
            {"id": 1, "varchar": None, "int": None},
            b"1     \x00\x00\x00\x00\x00######\n",
        ),
        (
            {"varchar": None},
            {"id": 1, "varchar": None, "int": None},
            b"1     \x00\x00\x00\x00\x00######\n",
        ),
        (
            {"int": None},
            {"id": 1, "varchar": None, "int": None},
            b"1     \x00\x00\x00\x00\x00######\n",
        ),
        (
            {"varchar": "ab"},
            {"id": 1, "varchar": "ab", "int": None},
            b"1     ab   ######\n",
        ),
        (
            {"int": 4567},
            {"id": 1, "varchar": None, "int": 4567},
            b"1     \x00\x00\x00\x00\x004567  \n",
        ),
    ],
)
def test_db_insert_none(db, values, expected, expected_contents):
    res = db.insert("d", values)

    assert res == expected
    assert_file_contents("d.dat", expected_contents)


@use_tables("a", "b")
def test_db_insert_fk(db):
    a = db.insert("a", {"text": "foo"})

    b = db.insert("b", {"text": "baz", "a_id": a["id"]})

    assert b["id"] == 1
    assert_file_contents("a.dat", b"1     foo  \n")
    assert_file_contents("b.dat", b"1     baz  1     \n")


@use_tables("a", "b")
def test_db_insert_bad_fk(db):
    db.insert("a", {"text": "foo"})

    with pytest.raises(ValueError):
        db.insert("b", {"text": "baz", "a_id": 2})

    assert_file_contents("a.dat", b"1     foo  \n")
    assert_file_contents("b.dat", b"")


@use_tables("d")
@p(
    ["pk", "values", "expected", "expected_contents"],
    [
        (
            1,
            {"varchar": "foo_1", "int": 100},
            {"id": 1, "varchar": "foo_1", "int": 100},
            (b"1     foo_1100   \n2     bar  2     \n3     baz  3     \n"),
        ),
        (
            2,
            {"varchar": "bar_2", "int": 200},
            {"id": 2, "varchar": "bar_2", "int": 200},
            (b"1     foo  1     \n2     bar_2200   \n3     baz  3     \n"),
        ),
        (
            3,
            {"varchar": "baz_3", "int": 300},
            {"id": 3, "varchar": "baz_3", "int": 300},
            (b"1     foo  1     \n2     bar  2     \n3     baz_3300   \n"),
        ),
    ],
)
def test_db_update_by_id(db, pk, values, expected, expected_contents):
    db.insert("d", {"varchar": "foo", "int": 1})
    db.insert("d", {"varchar": "bar", "int": 2})
    db.insert("d", {"varchar": "baz", "int": 3})

    res = db.update_by_id("d", pk, values)

    assert res == expected
    assert_file_contents("d.dat", expected_contents)


@use_tables("a")
def test_db_update_by_id_not_found(db):
    db.insert("a", {"text": "foo"})

    with pytest.raises(NotFoundError):
        db.update_by_id("a", 2, {"text": "bar"})

    assert_file_contents("a.dat", b"1     foo  \n")


@use_tables("a", "b")
def test_db_update_by_id_fk(db):
    db.insert("a", {"text": "foo"})
    db.insert("a", {"text": "bar"})
    db.insert("b", {"text": "baz", "a_id": 1})

    res = db.update_by_id("b", 1, {"a_id": 2})

    assert res == {"id": 1, "text": "baz", "a_id": 2}


@use_tables("a", "b")
def test_db_update_by_id_fk_skipped(db):
    db.insert("a", {"text": "foo"})
    db.insert("b", {"text": "bar", "a_id": 1})

    res = db.update_by_id("b", 1, {"text": "baz"})

    assert res == {"id": 1, "text": "baz", "a_id": 1}


@use_tables("a", "b")
def test_db_update_by_id_bad_fk(db):
    db.insert("a", {"text": "foo"})
    db.insert("b", {"text": "baz", "a_id": 1})

    with pytest.raises(ValueError):
        db.update_by_id("b", 1, {"a_id": 2})


@use_tables("a")
def test_db_update_by_id_deleted(db):
    db.insert("a", {"text": "foo"})
    db.delete_by_id("a", 1)

    with pytest.raises(NotFoundError):
        db.update_by_id("a", 1, {"text": "bar"})

    assert_file_contents("a.dat", b"***********\n")


@use_tables("a")
@p(
    ["pk", "expected_lst", "expected_contents"],
    [
        (
            1,
            [
                {"id": 2, "text": "bar"},
                {"id": 3, "text": "baz"},
            ],
            (b"***********\n2     bar  \n3     baz  \n"),
        ),
        (
            2,
            [
                {"id": 1, "text": "foo"},
                {"id": 3, "text": "baz"},
            ],
            (b"1     foo  \n***********\n3     baz  \n"),
        ),
        (
            3,
            [
                {"id": 1, "text": "foo"},
                {"id": 2, "text": "bar"},
            ],
            (b"1     foo  \n2     bar  \n***********\n"),
        ),
    ],
)
def test_db_delete_by_id_1(db, pk, expected_lst, expected_contents):
    db.insert("a", {"text": "foo"})
    db.insert("a", {"text": "bar"})
    db.insert("a", {"text": "baz"})

    db.delete_by_id("a", pk)

    assert db.find_all("a") == expected_lst
    assert_file_contents("a.dat", expected_contents)


@use_tables("a")
@p(
    ["substr", "expected_lst"],
    [
        ("oo", [{"id": 1, "text": "foo"}]),
        ("ba", [{"id": 3, "text": "baz"}]),
    ],
)
def test_db_delete_by_id_2(db, substr, expected_lst):
    db.insert("a", {"text": "foo"})
    db.insert("a", {"text": "bar"})
    db.insert("a", {"text": "baz"})

    db.delete_by_id("a", 2)

    assert db.find_by_cond("a", SUBSTR(text=substr)) == expected_lst


@use_tables("a")
@p(
    ["pk", "expected"],
    [
        (1, {"id": 2, "text": "bar"}),
        (2, None),
        (3, {"id": 2, "text": "bar"}),
    ],
)
def test_db_delete_by_id_3(db, pk, expected):
    db.insert("a", {"text": "foo"})
    db.insert("a", {"text": "bar"})
    db.insert("a", {"text": "baz"})

    db.delete_by_id("a", pk)

    assert db.find_by_id("a", 2) == expected


@use_tables("a")
@p(
    ["pk", "expected_lst", "expected_contents"],
    [
        (
            1,
            [
                {"id": 4, "text": "new"},
                {"id": 2, "text": "bar"},
                {"id": 3, "text": "baz"},
            ],
            (b"4     new  \n2     bar  \n3     baz  \n"),
        ),
        (
            2,
            [
                {"id": 1, "text": "foo"},
                {"id": 4, "text": "new"},
                {"id": 3, "text": "baz"},
            ],
            (b"1     foo  \n4     new  \n3     baz  \n"),
        ),
        (
            3,
            [
                {"id": 1, "text": "foo"},
                {"id": 2, "text": "bar"},
                {"id": 4, "text": "new"},
            ],
            (b"1     foo  \n2     bar  \n4     new  \n"),
        ),
    ],
)
def test_db_delete_one_then_insert(db, pk, expected_lst, expected_contents):
    db.insert("a", {"text": "foo"})
    db.insert("a", {"text": "bar"})
    db.insert("a", {"text": "baz"})
    db.delete_by_id("a", pk)

    res = db.insert("a", {"text": "new"})

    assert res["id"] == 4
    assert db.find_all("a") == expected_lst
    assert_file_contents("a.dat", expected_contents)


@use_tables("a")
@p(
    ["pks", "n", "expected_ids", "expected_lst", "expected_contents"],
    [
        (
            [1, 2],
            1,
            [4],
            [
                {"id": 4, "text": "new_1"},
                {"id": 3, "text": "baz"},
            ],
            (b"***********\n4     new_1\n3     baz  \n"),
        ),
        (
            [1, 2],
            2,
            [4, 5],
            [
                {"id": 5, "text": "new_2"},
                {"id": 4, "text": "new_1"},
                {"id": 3, "text": "baz"},
            ],
            (b"5     new_2\n4     new_1\n3     baz  \n"),
        ),
        (
            [1, 2],
            3,
            [4, 5, 6],
            [
                {"id": 5, "text": "new_2"},
                {"id": 4, "text": "new_1"},
                {"id": 3, "text": "baz"},
                {"id": 6, "text": "new_3"},
            ],
            (b"5     new_2\n4     new_1\n3     baz  \n6     new_3\n"),
        ),
    ],
)
def test_db_delete_many_then_insert(db, pks, n, expected_ids, expected_lst, expected_contents):
    db.insert("a", {"text": "foo"})
    db.insert("a", {"text": "bar"})
    db.insert("a", {"text": "baz"})

    for pk in pks:
        db.delete_by_id("a", pk)

    inserted_ids = []
    for i in range(n):
        res = db.insert("a", {"text": f"new_{i + 1}"})
        inserted_ids.append(res["id"])

    assert inserted_ids == expected_ids
    assert db.find_all("a") == expected_lst
    assert_file_contents("a.dat", expected_contents)


@use_tables("a")
def test_db_delete_insert_delete_reopen_insert(db):
    res = db.insert("a", {"text": "foo"})
    db.delete_by_id("a", res["id"])
    res = db.insert("a", {"text": "bar"})
    db.delete_by_id("a", res["id"])
    db.close()
    db2 = DB([TableA], base_dir=TEST_BASE_DIR)

    res = db2.insert("a", {"text": "new"})

    assert res["id"] == 3
    assert db2.find_all("a") == [{"id": 3, "text": "new"}]
    assert_file_contents("a.dat", b"3     new  \n")


@use_tables("a")
def test_db_delete_by_id_twice(db):
    db.insert("a", {"text": "foo"})
    db.insert("a", {"text": "bar"})
    db.insert("a", {"text": "baz"})

    db.delete_by_id("a", 2)
    with pytest.raises(NotFoundError):
        db.delete_by_id("a", 2)

    assert db.find_all("a") == [
        {"id": 1, "text": "foo"},
        {"id": 3, "text": "baz"},
    ]


@use_tables("a")
def test_db_find_by_id(db):
    db.insert("a", {"text": "foo"})
    db.insert("a", {"text": "bar"})
    db.insert("a", {"text": "baz"})

    a = db.find_by_id("a", 3)

    assert a == {"id": 3, "text": "baz"}


@use_tables("a")
def test_db_find_by_id_inconsistent_varchar(db):
    db.insert("a", {"text": ""})
    set_file_contents("a.dat", b"1     \0\0\0\0\0\n")

    with pytest.raises(ValueError, match="Inconsistent data"):
        db.find_by_id("a", 1)


@use_tables("c")
def test_db_find_by_id_inconsistent_int(db):
    db.insert("c", {"varchar": "abc", "int": 1})
    set_file_contents("c.dat", b"1     abc  ######\n")

    with pytest.raises(ValueError, match="Inconsistent data"):
        db.find_by_id("c", 1)


@use_tables("a")
def test_db_find_all(db):
    db.insert("a", {"text": "foo"})
    db.insert("a", {"text": "bar"})
    db.insert("a", {"text": "baz"})

    lst = db.find_all("a")

    assert lst == [
        {"id": 1, "text": "foo"},
        {"id": 2, "text": "bar"},
        {"id": 3, "text": "baz"},
    ]


@use_tables("a", "b")
def test_db_find_all_join(db):
    db.insert("a", {"text": "foo"})
    db.insert("b", {"text": "bar", "a_id": 1})
    db.insert("b", {"text": "baz", "a_id": 1})

    lst = db.find_all("b", joins=[Join("a_id", "a_row", "a")])

    assert lst == [
        {"id": 1, "text": "bar", "a_id": 1, "a_row": {"id": 1, "text": "foo"}},
        {"id": 2, "text": "baz", "a_id": 1, "a_row": {"id": 1, "text": "foo"}},
    ]


@use_tables("a")
def test_db_find_all_empty(db):
    lst = db.find_all("a")

    assert lst == []


@use_tables("a", "b")
def test_db_find_by_id_join(db):
    db.insert("a", {"text": "foo"})
    db.insert("b", {"text": "baz", "a_id": 1})

    b = db.find_by_id("b", 1, joins=[Join("a_id", "a_row", "a")])

    assert b == {"id": 1, "text": "baz", "a_id": 1, "a_row": {"id": 1, "text": "foo"}}


@use_tables("a", "b")
def test_db_find_by_id_inverse_join(db):
    db.insert("a", {"text": "foo"})
    db.insert("b", {"text": "bar", "a_id": 1})
    db.insert("b", {"text": "baz", "a_id": 1})

    a = db.find_by_id("a", 1, joins=[InverseJoin("a_id", "b_rows", "b")])

    assert a == {
        "id": 1,
        "text": "foo",
        "b_rows": [
            {"id": 1, "text": "bar", "a_id": 1},
            {"id": 2, "text": "baz", "a_id": 1},
        ],
    }


@use_tables("a", "b")
def test_db_find_by_id_inverse_join_nonexistent(db):
    db.insert("a", {"text": "foo"})
    db.insert("a", {"text": "bar"})
    db.insert("b", {"text": "baz", "a_id": 1})

    a = db.find_by_id("a", 2, joins=[InverseJoin("a_id", "b_rows", "b")])

    assert a == {"id": 2, "text": "bar", "b_rows": []}


@use_tables("a", "b2")
def test_db_find_by_id_inverse_join_none(db):
    db.insert("a", {"text": "foo"})
    db.insert("b2", {"text": "bar", "a_id": None})

    a = db.find_by_id("a", 1, joins=[InverseJoin("a_id", "b2_rows", "b2")])

    assert a == {"id": 1, "text": "foo", "b2_rows": []}


@use_tables("a", "b2")
def test_db_find_by_id_join_none(db):
    db.insert("a", {"text": "foo"})
    db.insert("b2", {"text": "baz", "a_id": None})
    db.insert("b2", {"text": "eggs", "a_id": 1})

    b = db.find_by_id("b2", 1, joins=[Join("a_id", "a_row", "a")])
    assert b == {"id": 1, "text": "baz", "a_id": None, "a_row": None}

    b = db.find_by_id("b2", 2, joins=[Join("a_id", "a_row", "a")])
    assert b == {"id": 2, "text": "eggs", "a_id": 1, "a_row": {"id": 1, "text": "foo"}}


@use_tables("a", "b")
def test_db_find_by_join(db):
    db.insert("a", {"text": "foo"})
    db.insert("a", {"text": "bar"})
    db.insert("a", {"text": "baz"})
    db.insert("b", {"text": "foo1", "a_id": 2})
    db.insert("b", {"text": "foo2", "a_id": 3})
    db.insert("b", {"text": "foo22", "a_id": 1})

    lst = db.find_by_cond("b", EQ(text="foo2"), joins=[Join("a_id", "a_row", "a")])

    assert lst == [
        {"id": 2, "text": "foo2", "a_id": 3, "a_row": {"id": 3, "text": "baz"}},
    ]


@use_tables("a")
def test_truncate_simple_table(db):
    db.insert("a", {"text": "foo"})
    db.insert("a", {"text": "bar"})
    assert len(db.find_all("a")) == 2

    db.truncate("a")

    assert len(db.find_all("a")) == 0
    assert_file_contents("a.dat", b"")
    assert_file_contents("a__seqnum.dat", b"0")


@use_tables("a", "b")
def test_truncate_with_dependent_tables(db):
    a1 = db.insert("a", {"text": "foo"})
    a2 = db.insert("a", {"text": "bar"})
    db.insert("b", {"text": "baz1", "a_id": a1["id"]})
    db.insert("b", {"text": "baz2", "a_id": a2["id"]})

    with pytest.raises(ValueError, match="has referring rows"):
        db.truncate("a")

    assert len(db.find_all("a")) == 2
    assert len(db.find_all("b")) == 2


@use_tables("a", "b")
def test_truncate_cascade(db):
    a1 = db.insert("a", {"text": "foo"})
    a2 = db.insert("a", {"text": "bar"})
    db.insert("b", {"text": "baz1", "a_id": a1["id"]})
    db.insert("b", {"text": "baz2", "a_id": a2["id"]})

    db.truncate("a", cascade=True)

    assert len(db.find_all("a")) == 0
    assert len(db.find_all("b")) == 0
    assert_file_contents("a.dat", b"")
    assert_file_contents("b.dat", b"")


@use_tables("a", "b")
def test_truncate_then_insert(db):
    a1 = db.insert("a", {"text": "foo"})
    db.insert("b", {"text": "baz", "a_id": a1["id"]})

    db.truncate("a", cascade=True)

    new_a = db.insert("a", {"text": "bar"})
    new_b = db.insert("b", {"text": "baz", "a_id": new_a["id"]})
    assert new_a["id"] == 1
    assert new_b["id"] == 1


@use_tables("c")
@p(
    ("cond", "expected"),
    [
        (LT(int=0), []),
        (
            LT(int=3),
            [
                {"id": 1, "varchar": "row 0", "int": 0},
                {"id": 2, "varchar": "row 1", "int": 1},
                {"id": 3, "varchar": "row 2", "int": 2},
            ],
        ),
        (GT(int=5), []),
        (
            GT(int=3),
            [
                {"id": 5, "varchar": "row 4", "int": 4},
                {"id": 6, "varchar": "row 5", "int": 5},
            ],
        ),
    ],
)
def test_find_by_cond_int(db, cond, expected):
    for i in range(6):
        db.insert("c", {"varchar": f"row {i}", "int": i})

    res = db.find_by_cond("c", cond)

    assert res == expected


@use_tables("d")
@p(
    ("cond", "expected"),
    [
        (LT(int=1), []),
        (
            LT(int=3),
            [
                {"id": 1, "varchar": "foo", "int": 1},
                {"id": 3, "varchar": "baz", "int": 2},
            ],
        ),
        (GT(int=3), []),
        (GT(int=1), [{"id": 3, "varchar": "baz", "int": 2}]),
    ],
)
def test_find_by_cond_int_nullable(db, cond, expected):
    db.insert("d", {"varchar": "foo", "int": 1})
    db.insert("d", {"varchar": "bar", "int": None})
    db.insert("d", {"varchar": "baz", "int": 2})

    res = db.find_by_cond("d", cond)

    assert res == expected


@use_tables("a")
def test_db_find_by_cond_substr(db):
    db.insert("a", {"text": "foo1"})
    db.insert("a", {"text": "foo2"})
    db.insert("a", {"text": "foo22"})

    lst = db.find_by_cond("a", SUBSTR(text="oo2"))

    assert lst == [
        {"id": 2, "text": "foo2"},
        {"id": 3, "text": "foo22"},
    ]


@use_tables("a", "b")
def test_db_find_by_cond_substr_join(db):
    db.insert("a", {"text": "foo"})
    db.insert("a", {"text": "bar"})
    db.insert("a", {"text": "baz"})
    db.insert("b", {"text": "foo1", "a_id": 2})
    db.insert("b", {"text": "foo2", "a_id": 3})
    db.insert("b", {"text": "foo22", "a_id": 1})

    lst = db.find_by_cond("b", SUBSTR(text="oo2"), joins=[Join("a_id", "a_row", "a")])

    assert lst == [
        {"id": 2, "text": "foo2", "a_id": 3, "a_row": {"id": 3, "text": "baz"}},
        {"id": 3, "text": "foo22", "a_id": 1, "a_row": {"id": 1, "text": "foo"}},
    ]


@use_tables("a")
def test_db_find_by_cond_isubstr(db):
    db.insert("a", {"text": "foo1"})
    db.insert("a", {"text": "FOO2"})
    db.insert("a", {"text": "foO22"})

    lst = db.find_by_cond("a", ISUBSTR(text="oo2"))

    assert lst == [
        {"id": 2, "text": "FOO2"},
        {"id": 3, "text": "foO22"},
    ]


@use_tables("a")
def test_db_find_by_cond_eq(db):
    db.insert("a", {"text": "foo1"})
    db.insert("a", {"text": "foo2"})
    db.insert("a", {"text": "foo22"})

    lst = db.find_by_cond("a", EQ(text="foo2"))

    assert lst == [{"id": 2, "text": "foo2"}]


@use_tables("f")
@p(
    ["text", "expected_row", "expected_table_contents", "expected_text_contents"],
    [
        ("foo", {"id": 1, "text": "foo"}, b"1     0     \n", b"3     foo"),
        ("", {"id": 1, "text": ""}, b"1     0     \n", b"0     "),
        ("café", {"id": 1, "text": "café"}, b"1     0     \n", b"5     caf\xc3\xa9"),
        (
            "some\nthing\treally\0weird",
            {"id": 1, "text": "some\nthing\treally\0weird"},
            b"1     0     \n",
            b"23    some\nthing\treally\0weird",
        ),
    ],
)
def test_db_insert_single_text(
    db, text, expected_row, expected_table_contents, expected_text_contents
):
    f = db.insert("f", {"text": text})

    assert f == expected_row
    assert_file_contents("f.dat", expected_table_contents)
    assert_file_contents("f.text.dat", expected_text_contents)


@use_tables("f")
@p("text", ["foo", "", "café", "some\nthing\treally\0weird"])
def test_db_read_back_text(db, text):
    db.insert("f", {"text": text})

    res = db.find_by_id("f", 1)
    assert res["text"] == text


@use_tables("f")
def test_db_insert_text_not_null_error(db):
    with pytest.raises(ValidationError, match="'text': The value can't be None"):
        db.insert("f", {"text": None})

    assert_file_contents("f.dat", b"")
    assert_file_contents("f.text.dat", b"")


@use_tables("f")
def test_db_insert_text_type_error(db):
    with pytest.raises(ValidationError, match="'text': Type mismatch"):
        db.insert("f", {"text": 1})

    assert_file_contents("f.dat", b"")
    assert_file_contents("f.text.dat", b"")


@use_tables("f")
def test_db_insert_multiple_texts(db):
    f1 = db.insert("f", {"text": "foo"})
    f2 = db.insert("f", {"text": "eggs"})
    f3 = db.insert("f", {"text": "multiple"})

    assert f1["id"] == 1
    assert f1["text"] == "foo"
    assert f2["id"] == 2
    assert f2["text"] == "eggs"
    assert f3["id"] == 3
    assert f3["text"] == "multiple"
    assert_file_contents(
        "f.dat",
        (
            b"1     0     \n"  # fmt: skip
            b"2     9     \n"
            b"3     19    \n"
        ),
    )
    assert_file_contents(
        "f.text.dat",
        (
            b"3     foo"  # fmt: skip
            b"4     eggs"
            b"8     multiple"
        ),
    )


@use_tables("f")
@p(
    ["pk", "values", "expected", "expected_table_contents", "expected_text_contents"],
    [
        (
            1,
            {"text": "foo_1"},
            {"id": 1, "text": "foo_1"},
            (
                b"1     18    \n"  # fmt: skip
                b"2     9     \n"
            ),
            (
                b"#########"  # fmt: skip
                b"3     bar"
                b"5     foo_1"
            ),
        ),
        (
            2,
            {"text": "bar_1"},
            {"id": 2, "text": "bar_1"},
            (
                b"1     0     \n"  # fmt: skip
                b"2     18    \n"
            ),
            (
                b"3     foo"  # fmt: skip
                b"#########"
                b"5     bar_1"
            ),
        ),
    ],
)
def test_db_update_texts_by_id(
    db, pk, values, expected, expected_table_contents, expected_text_contents
):
    db.insert("f", {"text": "foo"})
    db.insert("f", {"text": "bar"})

    res = db.update_by_id("f", pk, values)

    assert res == expected
    assert_file_contents("f.dat", expected_table_contents)
    assert_file_contents("f.text.dat", expected_text_contents)


@use_tables("f")
@p(
    ["pk", "expected_table_contents", "expected_text_contents"],
    [
        (
            1,
            (
                b"************\n"  # fmt: skip
                b"2     9     \n"
                b"3     18    \n"
            ),
            (
                b"#########"  # fmt: skip
                b"3     bar"
                b"3     baz"
            ),
        ),
        (
            2,
            (
                b"1     0     \n"  # fmt: skip
                b"************\n"
                b"3     18    \n"
            ),
            (
                b"3     foo"  # fmt: skip
                b"#########"
                b"3     baz"
            ),
        ),
        (
            3,
            (
                b"1     0     \n"  # fmt: skip
                b"2     9     \n"
                b"************\n"
            ),
            (
                b"3     foo"  # fmt: skip
                b"3     bar"
                b"#########"
            ),
        ),
    ],
)
def test_db_delete_texts_by_id(db, pk, expected_table_contents, expected_text_contents):
    db.insert("f", {"text": "foo"})
    db.insert("f", {"text": "bar"})
    db.insert("f", {"text": "baz"})

    db.delete_by_id("f", pk)

    assert_file_contents("f.dat", expected_table_contents)
    assert_file_contents("f.text.dat", expected_text_contents)


@use_tables("f")
@p(
    [
        "pks",
        "n",
        "expected_rows",
        "expected_fetched_rows",
        "expected_table_contents",
        "expected_text_contents",
    ],
    [
        (
            [1, 2],
            1,
            [{"id": 4, "text": "new_1"}],
            [
                {"id": 3, "text": "baz"},
                {"id": 4, "text": "new_1"},
            ],
            (
                b"************\n"  # fmt: skip
                b"************\n"
                b"3     18    \n"
                b"4     27    \n"
            ),
            (
                b"#########"  # fmt: skip
                b"#########"
                b"3     baz"
                b"5     new_1"
            ),
        ),
        (
            [1, 2],
            2,
            [
                {"id": 4, "text": "new_1"},
                {"id": 5, "text": "new_2"},
            ],
            [
                {"id": 3, "text": "baz"},
                {"id": 4, "text": "new_1"},
                {"id": 5, "text": "new_2"},
            ],
            (
                b"************\n"  # fmt: skip
                b"************\n"
                b"3     18    \n"
                b"4     27    \n"
                b"5     38    \n"
            ),
            (
                b"#########"  # fmt: skip
                b"#########"
                b"3     baz"
                b"5     new_1"
                b"5     new_2"
            ),
        ),
        (
            [1, 3],
            1,
            [{"id": 4, "text": "new_1"}],
            [
                {"id": 2, "text": "bar"},
                {"id": 4, "text": "new_1"},
            ],
            (
                b"************\n"  # fmt: skip
                b"2     9     \n"
                b"************\n"
                b"4     27    \n"
            ),
            (
                b"#########"  # fmt: skip
                b"3     bar"
                b"#########"
                b"5     new_1"
            ),
        ),
    ],
)
def test_db_delete_texts_then_insert(
    db,
    pks,
    n,
    expected_rows,
    expected_fetched_rows,
    expected_table_contents,
    expected_text_contents,
):
    db.insert("f", {"text": "foo"})
    db.insert("f", {"text": "bar"})
    db.insert("f", {"text": "baz"})

    for pk in pks:
        db.delete_by_id("f", pk)

    inserted_rows = []
    for i in range(n):
        res = db.insert("f", {"text": f"new_{i + 1}"})
        inserted_rows.append(res)

    assert inserted_rows == expected_rows
    assert db.find_all("f") == expected_fetched_rows

    assert_file_contents("f.dat", expected_table_contents)
    assert_file_contents("f.text.dat", expected_text_contents)


@use_tables("f")
def test_db_truncate_with_texts(db):
    db.insert("f", {"text": "foo"})
    db.insert("f", {"text": "bar"})
    db.insert("f", {"text": "baz"})

    db.truncate("f")

    assert_file_contents("f.dat", b"")
    assert_file_contents("f.text.dat", b"")


@use_tables("f2")
def test_db_insert_single_nullable_text(db):
    f2 = db.insert("f2", {"text": None})

    assert f2["id"] == 1
    assert f2["text"] is None
    assert_file_contents("f2.dat", b"1     \0\0\0\0\0\0\n")
    assert_file_contents("f2.text.dat", b"")


@use_tables("f2")
def test_db_insert_empty_nullable_text(db):
    f2 = db.insert("f2", {"text": ""})

    assert f2["id"] == 1
    assert f2["text"] == ""
    assert_file_contents("f2.dat", b"1     0     \n")
    assert_file_contents("f2.text.dat", b"0     ")


@use_tables("f2")
def test_db_insert_multiple_nullable_texts(db):
    f1 = db.insert("f2", {"text": "foo"})
    f2 = db.insert("f2", {"text": None})
    f3 = db.insert("f2", {"text": "bar"})

    assert f1["id"] == 1
    assert f1["text"] == "foo"
    assert f2["id"] == 2
    assert f2["text"] is None
    assert f3["id"] == 3
    assert f3["text"] == "bar"
    assert_file_contents(
        "f2.dat",
        (
            b"1     0     \n"  # fmt: skip
            b"2     \0\0\0\0\0\0\n"
            b"3     9     \n"
        ),
    )
    assert_file_contents(
        "f2.text.dat",
        (
            b"3     foo"  # fmt: skip
            b"3     bar"
        ),
    )


@use_tables("f2")
@p(
    ["pk", "values", "expected", "expected_table_contents", "expected_text_contents"],
    [
        (
            1,
            {"text": None},
            {"id": 1, "text": None},
            (
                b"1     \0\0\0\0\0\0\n"  # fmt: skip
                b"2     \0\0\0\0\0\0\n"
                b"3     9     \n"
            ),
            (
                b"#########"  # fmt: skip
                b"3     bar"
            ),
        ),
        (
            3,
            {"text": None},
            {"id": 3, "text": None},
            (
                b"1     0     \n"  # fmt: skip
                b"2     \0\0\0\0\0\0\n"
                b"3     \0\0\0\0\0\0\n"
            ),
            (
                b"3     foo"  # fmt: skip
                b"#########"
                b"#########"
            ),
        ),
        (
            2,
            {"text": "baz"},
            {"id": 2, "text": "baz"},
            (
                b"1     0     \n"  # fmt: skip
                b"2     18    \n"
                b"3     9     \n"
            ),
            (
                b"3     foo"  # fmt: skip
                b"3     bar"
                b"3     baz"
            ),
        ),
    ],
)
def test_db_update_nullable_texts_by_id(
    db, pk, values, expected, expected_table_contents, expected_text_contents
):
    db.insert("f2", {"text": "foo"})
    db.insert("f2", {"text": None})
    db.insert("f2", {"text": "bar"})

    res = db.update_by_id("f2", pk, values)

    assert res == expected
    assert_file_contents("f2.dat", expected_table_contents)
    assert_file_contents("f2.text.dat", expected_text_contents)


@use_tables("g")
def test_db_insert_multiple_text_fields(db):
    g = db.insert("g", {"text1": "foo", "text2": None, "text3": "bar"})

    assert g == {"id": 1, "text1": "foo", "text2": None, "text3": "bar"}
    assert_file_contents("g.dat", b"1     0     \0\0\0\0\0\09     \n")
    assert_file_contents(
        "g.text.dat",
        (
            b"3     foo"  # fmt: skip
            b"3     bar"
        ),
    )
