from __future__ import annotations

import os
from typing import Generator

from .cond import BaseCond
from .errors import NotFoundError, ValidationError
from .fields import FK, TEXT, Field
from .row import Row
from .storage import Array, File, FreeRownums, PersistentInt, TextStorage


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

    def text_fields(self) -> list[str]:
        return [x.name for x in self.schema if isinstance(x.type, TEXT)]


class Table:
    name: str
    schema: Schema

    def __init__(self, base_dir: str) -> None:
        assert self.name and self.schema

        self.row_size = self.schema.row_size()
        self.f = File.open(f"{self.name}.dat", base_dir=base_dir)
        self.f_seqnum = PersistentInt(f"{self.name}__seqnum.dat", 0, base_dir=base_dir)

        self.free_rownums = FreeRownums(self.name, base_dir=base_dir)
        self.rownum_index = Array(f"{self.name}__id.idx.dat", 6, base_dir=base_dir)
        self.text_storage = None
        if self.schema.text_fields():
            self.text_storage = TextStorage(self.name, base_dir=base_dir)

    def close(self) -> None:
        if self.text_storage:
            self.text_storage.close()
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

        # handle text fields separately
        text_values: dict[str, str | bytes] = {}
        text_fields = self.schema.text_fields()
        if text_fields:
            assert self.text_storage
            for text_field in text_fields:
                text = values.get(text_field)
                if text is None:
                    values[text_field] = None
                    continue
                if not isinstance(text, (str, bytes)):
                    raise ValidationError(f"'{text_field}': Type mismatch")
                values[text_field] = self.text_storage.add(text)
                text_values[text_field] = text

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
        return Row(parsed | text_values)

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

        # handle text fields separately
        text_fields = self.schema.text_fields()
        if text_fields:
            assert self.text_storage
            for text_field in text_fields:
                ref = values.get(text_field)
                if ref is None:
                    continue
                self.text_storage.delete(ref)

        self.f.seek(rownum * self.row_size)
        self.rownum_index.set(pk - 1, None)
        self.f.write(b"*" * (self.row_size - 1) + b"\n")
        self.free_rownums.push(rownum)

    def iterate(self) -> Generator[Row]:
        self.f.seek(0)
        text_fields = self.schema.text_fields()
        while row := self.f.read(self.row_size):
            if parsed := self.schema.parse(row):
                # handle text fields separately
                text_values: dict[str, str | None] = {}
                if text_fields:
                    assert self.text_storage
                    for text_field in text_fields:
                        text_ref = parsed[text_field]
                        if text_ref is not None:
                            text = self.text_storage.get(text_ref)
                            text_values[text_field] = text.decode()
                yield Row(parsed | text_values)

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
        parsed_row = self.schema.parse(row)
        if not parsed_row:
            return parsed_row

        # handle text fields separately
        text_values: dict[str, str | None] = {}
        text_fields = self.schema.text_fields()
        if text_fields:
            assert self.text_storage
            for text_field in text_fields:
                text_ref = parsed_row[text_field]
                if text_ref is not None:
                    text = self.text_storage.get(text_ref)
                    text_values[text_field] = text.decode()
        return Row(parsed_row | text_values)

    def find_by_cond(self, cond: BaseCond) -> list[Row]:
        res = []
        for row in self.iterate():
            if cond.eval(row):
                res.append(row)
        return res
