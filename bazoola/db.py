from __future__ import annotations

import fcntl
import os
import threading
from abc import ABC, abstractmethod
from contextlib import contextmanager
from typing import Any, BinaryIO, Generator, NamedTuple


class DBError(Exception):
    def __init__(self, message: str):
        self.message = message


class ValidationError(DBError):
    pass


class NotFoundError(DBError):
    pass


class FieldType(ABC):
    def __init__(self, size: int, null: bool = False) -> None:
        assert size > 0, "Size of the field should be greater than 0"

        self.size = size
        self.null = null
        self.params: dict[str, Any] = {}

    @abstractmethod
    def serialize(self, val) -> bytes: ...

    @abstractmethod
    def deserialize(self, row: bytes, start: int): ...

    def validate(self, val: Any) -> None:
        if not self.null and val is None:
            raise ValidationError("The value can't be None")
        self.validate_type(val)

    @abstractmethod
    def validate_type(self, val: Any) -> None: ...


class INT(FieldType):
    def __init__(self, null: bool = False) -> None:
        super().__init__(6, null)

    def serialize(self, val: int | None) -> bytes:
        if val is None:
            return b"#" * self.size
        fmt = f"%-{self.size}s".encode()
        return fmt % str(val).encode()

    def deserialize(self, row: bytes, start: int) -> tuple[int | None, int]:
        assert start >= 0, "`start` can't be negative"
        assert row, "`row` can't be empty"

        end = start + self.size
        v = row[start:end]
        if v[0] == ord("#"):
            if not self.null:
                raise ValueError("Inconsistent data")
            return None, end
        return int(v), end

    def validate_type(self, val: int | None) -> None:
        if val is None:
            return
        if not isinstance(val, int):
            raise ValidationError(f"Type mismatch: `{val!r}` is not `int`")
        if len(str(val)) > self.size:
            raise ValidationError("The value is too big")


class PK(INT):
    def __init__(self) -> None:
        super().__init__(False)


class FK(INT):
    def __init__(self, rel_name: str, null: bool = False) -> None:
        super().__init__(null=null)
        self.params["rel_name"] = rel_name


class CHAR(FieldType):
    def serialize(self, val: str | bytes | None) -> bytes:
        if val is None:
            return b"\0" * self.size

        if isinstance(val, str):
            val = val.encode()
        fmt = f"%-{self.size}s"
        return fmt.encode() % val

    def deserialize(self, row: bytes, start: int) -> tuple[str | None, int]:
        assert start >= 0
        assert row, "`row` can't be empty"

        end = start + self.size
        v = row[start:end]
        if v[0] == 0:
            if not self.null:
                raise ValueError("Inconsistent data")
            return None, end
        return v.rstrip().decode(), end

    def validate_type(self, val: str | bytes | None) -> None:
        if val is None:
            return
        if not isinstance(val, (str, bytes)):
            raise ValidationError("Type mismatch")
        if isinstance(val, str):
            val = val.encode()
        if len(val) > self.size:
            raise ValidationError("The value is too long")


class Field(NamedTuple):
    name: str
    type: FieldType

    def validate(self, val: Any) -> None:
        try:
            self.type.validate(val)
        except ValidationError as e:
            raise ValidationError(f"'{self.name}': {e.message}")


class Schema:
    def __init__(self, schema: list[Field]):
        assert schema, "Schema must not be empty"

        self.schema = schema

    def row_size(self) -> int:
        return sum(x.type.size for x in self.schema) + 1

    def to_row(self, values: dict) -> bytes:
        values_lst = []
        for field in self.schema:
            val = values.get(field.name)
            field.validate(val)
            col = field.type.serialize(val)
            values_lst.append(col)
        return b"".join(values_lst) + b"\n"

    def parse(self, row: bytes) -> Row | None:
        assert (l := len(row)) == (size := self.row_size()), f"{l=} != {size=}"

        if row[0] == ord("*"):
            return None
        values = Row()
        start = 0
        for field in self.schema:
            value, end = field.type.deserialize(row, start)
            values[field.name] = value
            start = end
        return values

    def relations(self) -> list[tuple[str, str]]:
        return [(x.name, x.type.params["rel_name"]) for x in self.schema if isinstance(x.type, FK)]


class File:
    def __init__(self, file: BinaryIO) -> None:
        self.f = file

    @classmethod
    def open(
        cls, path: str, default_body: bytes | None = None, base_dir: str | None = None
    ) -> File:
        assert path

        if base_dir:
            path = os.path.join(base_dir, path)

        try:
            f = open(path, "rb+", buffering=0)
        except FileNotFoundError:
            # Ensure directory exists before creating file
            dir_path = os.path.dirname(path)
            if dir_path and not os.path.exists(dir_path):
                os.makedirs(dir_path)
            with open(path, "wb") as fnew:
                if default_body is not None:
                    fnew.write(default_body)
            f = open(path, "rb+", buffering=0)
        return File(f)

    def read(self, n: int = -1) -> bytes:
        try:
            return self.f.read(n)
        except OSError as e:
            raise DBError(f"Failed to read from file {self.f.name}: {e!s}")

    def seek(self, offset: int, whence: int = 0) -> None:
        try:
            self.f.seek(offset, whence)
        except (OSError, ValueError) as e:
            raise DBError(
                f"Failed to seek in file {self.f.name} (offset={offset}, whence={whence}): {e!s}"
            )

    def tell(self) -> int:
        try:
            return self.f.tell()
        except OSError as e:
            raise DBError(f"Failed to get file position in {self.f.name}: {e!s}")

    def close(self) -> None:
        try:
            self.f.close()
        except OSError:
            # Just log the error, don't raise since close is often called in finally blocks
            print("Warning: Failed to close file properly")

    def write(self, s: bytes | bytearray) -> int:
        try:
            return self.f.write(s)
        except OSError as e:
            raise DBError(f"Failed to write to file {self.f.name}: {e!s}")

    def truncate(self, size: int | None = None) -> int:
        try:
            return self.f.truncate(size)
        except OSError as e:
            raise DBError(f"Failed to truncate file {self.f.name}: {e!s}")

    def size(self) -> int:
        try:
            return os.fstat(self.f.fileno()).st_size
        except OSError as e:
            raise DBError(f"Failed to get file size {self.f.name}: {e!s}")

    @contextmanager
    def lock(self) -> Generator[None, None, None]:
        try:
            fcntl.flock(self.f.fileno(), fcntl.LOCK_EX)
            yield
        finally:
            fcntl.flock(self.f.fileno(), fcntl.LOCK_UN)


class PersistentInt:
    def __init__(self, fname: str, default: int, base_dir: str | None = None) -> None:
        self.f = File.open(fname, str(default).encode(), base_dir=base_dir)

    def get(self) -> int:
        self.f.seek(0)
        return int(self.f.read())

    def set(self, i: int) -> None:
        self.f.seek(0)
        self.f.write(str(i).encode())

    def close(self) -> None:
        self.f.close()


class Array:
    def __init__(self, fname: str, item_size: int, base_dir: str | None = None) -> None:
        self.f = File.open(fname, base_dir=base_dir)
        self.item_size = item_size
        self.fmt = f"%-{item_size}s"

    def close(self) -> None:
        self.f.close()

    def get(self, index: int) -> int | None:
        self.f.seek(index * self.item_size)
        rownum = self.f.read(self.item_size)
        if not rownum or rownum == b"######":
            return None
        return int(rownum)

    def set(self, index: int, value: int | None) -> None:
        offset = index * self.item_size
        file_size = self.f.size()
        if offset > file_size:
            gap = offset - file_size
            self.f.seek(0, os.SEEK_END)
            self.f.write(b"#" * gap)
        self.f.seek(offset)
        if value is not None:
            self.f.write((self.fmt % value).encode())
        else:
            self.f.write(b"#" * self.item_size)


class Stack:
    def __init__(self, file: File, item_size: int) -> None:
        self.f = file
        self.item_size = item_size
        self.fmt = f"%-{item_size}s"

    @classmethod
    def from_file_path(cls, path: str, item_size: int, base_dir: str | None = None) -> Stack:
        return cls(File.open(path, base_dir=base_dir), item_size)

    def close(self) -> None:
        self.f.close()

    def push(self, item: int) -> None:
        with self.f.lock():
            self.f.seek(0, os.SEEK_END)
            self.f.write((self.fmt % item).encode())

    def pop(self) -> int | None:
        with self.f.lock():
            self.f.seek(0, os.SEEK_END)
            file_size = self.f.tell()
            if file_size == 0:
                return None
            if file_size < self.item_size:
                print(f"File corrupted: size {file_size} < item_size {self.item_size}")
                return None
            self.f.seek(-self.item_size, os.SEEK_END)
            rownum = self.f.read(self.item_size)
            new_size = self.f.tell() - self.item_size
            self.f.truncate(new_size)
            return int(rownum)


class FreeRownums:
    def __init__(self, table_name: str, base_dir: str | None = None) -> None:
        self.stack = Stack.from_file_path(f"{table_name}__free.dat", 6, base_dir=base_dir)

    def close(self) -> None:
        self.stack.close()

    def push(self, item: int) -> None:
        self.stack.push(item)

    def pop(self) -> int | None:
        return self.stack.pop()


class Table:
    name: str
    schema: Schema

    def __init__(self, db: DB | None = None) -> None:
        assert self.name and self.schema

        self.db = db
        base_dir = self.db.base_dir if self.db else None

        self.row_size = self.schema.row_size()
        self.f = File.open(f"{self.name}.dat", base_dir=base_dir)
        self.f_seqnum = PersistentInt(f"{self.name}__seqnum.dat", 0, base_dir=base_dir)

        self.free_rownums = FreeRownums(self.name, base_dir=base_dir)
        self.rownum_index = Array(f"{self.name}__id.idx.dat", 6, base_dir=base_dir)

    def close(self) -> None:
        self.rownum_index.close()
        self.f_seqnum.close()
        self.free_rownums.close()
        self.f.close()

    def next_seqnum(self) -> int:
        seqnum = self.f_seqnum.get() + 1
        self.f_seqnum.set(seqnum)
        return seqnum

    def insert(self, values: dict) -> Row:
        if "id" in values:
            assert values["id"] is not None
            assert values["id"] > 0
            new_id = values["id"]
        else:
            new_id = self.next_seqnum()
            values = values | {"id": new_id}

        existing_rownum = self.rownum_index.get(new_id - 1)
        if existing_rownum is not None:
            raise ValidationError(f"'id': row with id {new_id} already exists")

        row = self.schema.to_row(values)
        self.seek_insert()
        chosen_rownum = self.f.tell() // self.row_size
        self.f.write(row)
        self.rownum_index.set(new_id - 1, chosen_rownum)
        parsed = self.schema.parse(row)
        assert parsed is not None, "The inserted row doesn't match its parsed representation"
        return Row(parsed)

    def seek_insert(self) -> None:
        rownum = self.free_rownums.pop()
        if rownum is not None:
            self.f.seek(rownum * self.row_size)
            return
        self.f.seek(0, os.SEEK_END)

    def update_by_id(self, pk: int, values: dict) -> Row:
        assert pk > 0, "IDs must be greater than 0"
        existing_values = self.find_by_id(pk)
        if existing_values is None:
            raise NotFoundError(f"Row with ID={pk} does not exist")
        self.delete_by_id(pk)
        return self.insert(existing_values | values)

    def delete_by_id(self, pk: int) -> None:
        assert pk > 0, "IDs must be greater than 0"

        rownum = self.rownum_index.get(pk - 1)
        if rownum is None:
            raise NotFoundError(f"Row with ID={pk} does not exist")

        self.f.seek(rownum * self.row_size)
        row = self.f.read(self.row_size)
        values = self.schema.parse(row)
        if values is None:
            # already deleted
            raise NotFoundError(f"Row with ID={pk} does not exist")

        self.f.seek(rownum * self.row_size)
        self.rownum_index.set(pk - 1, None)
        self.f.write(b"*" * (self.row_size - 1) + b"\n")
        self.free_rownums.push(rownum)

    def iterate(self) -> Generator[Row]:
        self.f.seek(0)
        while row := self.f.read(self.row_size):
            if parsed := self.schema.parse(row):
                yield parsed

    def find_all(self) -> list[Row]:
        return list(self.iterate())

    def find_by_id(self, pk: int) -> Row | None:
        assert pk > 0, "IDs must be greater than 0"

        rownum = self.rownum_index.get(pk - 1)
        if rownum is None:
            return None
        self.f.seek(rownum * self.row_size)
        row = self.f.read(self.row_size)
        if not row:
            return None
        return self.schema.parse(row)

    def find_by(self, field_name: str, value: Any) -> list[Row]:
        res = []
        for row in self.iterate():
            if row.get(field_name) == value:
                res.append(row)
        return res

    def find_by_cond(self, cond: BaseCond) -> list[Row]:
        res = []
        for row in self.iterate():
            if cond.eval(row):
                res.append(row)
        return res

    def truncate(self, cascade: bool = False) -> None:
        assert self.db is not None
        dependent_tables = []
        for table_name, table in self.db.tables.items():
            if table_name == self.name:
                continue
            for field, rel_table in table.schema.relations():
                if rel_table == self.name:
                    dependent_tables.append(table_name)
                    break

        if not cascade:
            for dep_table_name in dependent_tables:
                dep_table = self.db.tables[dep_table_name]
                for field, rel_table in dep_table.schema.relations():
                    if rel_table == self.name:
                        for row in dep_table.iterate():
                            if row[field] is not None:
                                raise ValueError(
                                    f"Cannot truncate table '{self.name}': "
                                    f"table '{dep_table_name}' has referring rows. "
                                    f"Use `cascade` option to truncate dependent tables."
                                )

        if cascade:
            for dep_table_name in dependent_tables:
                self.db.tables[dep_table_name].truncate(cascade=True)

        self.f.seek(0)
        self.f.truncate()

        self.f_seqnum.set(0)

        self.rownum_index.f.seek(0)
        self.rownum_index.f.truncate()

        self.free_rownums.stack.f.truncate()


class BaseJoin(ABC):
    fk_attr: str
    foreign_table_name: str

    @abstractmethod
    def join(self, fk: int | None, foreign_table: Table) -> dict: ...


class Join(BaseJoin):
    def __init__(self, fk_attr: str, key: str, foreign_table_name: str):
        assert fk_attr and key and foreign_table_name

        self.fk_attr = fk_attr
        self.key = key
        self.foreign_table_name = foreign_table_name

    def join(self, fk: int | None, foreign_table: Table) -> dict:
        if fk is None:
            return {self.key: None}
        values = foreign_table.find_by_id(fk)
        assert values
        return {self.key: values}


class InverseJoin(Join):
    def join(self, pk: int | None, foreign_table: Table) -> dict:
        assert pk is not None

        foreign_rows = foreign_table.find_by(self.fk_attr, pk)
        return {self.key: foreign_rows}


class BaseCond(ABC):
    def __init__(self, **params) -> None:
        assert params

        self.params = params

    @abstractmethod
    def eval(self, row: Row) -> bool: ...


class LT(BaseCond):
    def eval(self, row: Row) -> bool:
        for field_name, value in self.params.items():
            row_value = row.get(field_name)
            if row_value is None or row_value >= value:
                return False
        return True


class GT(BaseCond):
    def eval(self, row: Row) -> bool:
        for field_name, value in self.params.items():
            row_value = row.get(field_name)
            if row_value is None or row_value <= value:
                return False
        return True


class SUBSTR(BaseCond):
    def eval(self, row: Row) -> bool:
        for field_name, value in self.params.items():
            row_value = row.get(field_name)
            if row_value is None or value not in str(row_value):
                return False
        return True


class ISUBSTR(BaseCond):
    def eval(self, row: Row) -> bool:
        for field_name, value in self.params.items():
            assert isinstance(value, str)

            row_value = row.get(field_name)
            if row_value is None:
                return False

            lowercased_value = value.lower()
            lowercased_row_value = str(row_value).lower()
            if lowercased_value not in lowercased_row_value:
                return False
        return True


class Row(dict):
    pass


class DB:
    def __init__(self, cls_tables: list[type[Table]], base_dir: str = "data") -> None:
        assert cls_tables, "DB must have at least one table"

        self.cls_tables = cls_tables
        self.base_dir = base_dir
        os.makedirs(self.base_dir, exist_ok=True)

        self.open_tables()

        self._threadlock = threading.RLock()
        self._lockfile = File.open(".lock", base_dir=base_dir)

    @contextmanager
    def lock(self) -> Generator[None, None, None]:
        with self._threadlock, self._lockfile.lock():
            yield

    def open_tables(self) -> None:
        self.tables: dict[str, Table] = {x.name: x(self) for x in self.cls_tables}

    def insert(self, table_name: str, values: dict) -> Row:
        assert table_name in self.tables, "No such table"

        with self.lock():
            tbl = self.tables[table_name]
            for fk_field, fk_table in tbl.schema.relations():
                fk_val = values.get(fk_field)
                if not fk_val:
                    continue
                rel_obj = self.tables[fk_table].find_by_id(fk_val)
                if not rel_obj:
                    raise ValueError(f"Item id={fk_val} does not exist in '{fk_table}'")
            return tbl.insert(values)

    def find_all(self, table_name: str, *, joins: list[BaseJoin] | None = None) -> list[Row]:
        assert table_name in self.tables, "No such table"
        if joins is None:
            joins = []

        with self.lock():
            rows = self.tables[table_name].find_all()
            for join in joins:
                for i in range(len(rows)):
                    rows[i] = self.perform_join(rows[i], join, self.tables[table_name])
        return rows

    def find_by_id(
        self, table_name: str, pk: int, *, joins: list[BaseJoin] | None = None
    ) -> Row | None:
        assert table_name in self.tables, "No such table"
        if joins is None:
            joins = []

        with self.lock():
            row = self.tables[table_name].find_by_id(pk)
            if joins and row:
                for join in joins:
                    row = self.perform_join(row, join, self.tables[table_name])
        return row

    def delete_by_id(self, table_name: str, pk: int) -> None:
        assert table_name in self.tables, "No such table"

        with self.lock():
            self.tables[table_name].delete_by_id(pk)

    def update_by_id(self, table_name: str, pk: int, values: dict) -> Row:
        assert table_name in self.tables, "No such table"

        with self.lock():
            tbl = self.tables[table_name]
            for fk_field, fk_table in tbl.schema.relations():
                fk_val = values.get(fk_field)
                if not fk_val:
                    continue
                rel_obj = self.tables[fk_table].find_by_id(fk_val)
                if not rel_obj:
                    raise ValueError(f"Item id={fk_val} does not exist in '{fk_table}'")

            return self.tables[table_name].update_by_id(pk, values)

    def find_by(
        self,
        table_name: str,
        field_name: str,
        value: Any,
        *,
        joins: list[BaseJoin] | None = None,
    ) -> list[Row]:
        assert table_name in self.tables, "No such table"
        assert field_name
        if joins is None:
            joins = []

        with self.lock():
            res = self.tables[table_name].find_by(field_name, value)
            for join in joins:
                for i in range(len(res)):
                    res[i] = self.perform_join(res[i], join, self.tables[table_name])
        return res

    def find_by_cond(
        self, table_name: str, cond: BaseCond, joins: list[BaseJoin] | None = None
    ) -> list[Row]:
        assert table_name in self.tables, "No such table"
        if joins is None:
            joins = []

        with self.lock():
            res = self.tables[table_name].find_by_cond(cond)
            for join in joins:
                for i in range(len(res)):
                    res[i] = self.perform_join(res[i], join, self.tables[table_name])
        return res

    def perform_join(self, row: Row, join: BaseJoin, table: Table) -> Row:
        assert join.fk_attr in row or isinstance(join, InverseJoin)
        if isinstance(join, InverseJoin):
            joined_values = join.join(row["id"], self.tables[join.foreign_table_name])
        else:
            joined_values = join.join(row[join.fk_attr], self.tables[join.foreign_table_name])

        return Row(row | joined_values)

    def close(self) -> None:
        for t in self.tables.values():
            t.close()
        self.tables = {}

    def reopen(self) -> None:
        self.close()
        self.open_tables()

    def truncate(self, table_name: str, cascade: bool = False) -> None:
        assert table_name in self.tables, "No such table"

        with self.lock():
            self.tables[table_name].truncate(cascade=cascade)
