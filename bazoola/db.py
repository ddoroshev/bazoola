from __future__ import annotations

from typing import Any

from .cond import BaseCond
from .join import BaseJoin, InverseJoin
from .row import Row
from .storage import TableStorage
from .table import Table


class DB:
    def __init__(self, cls_tables: list[type[Table]], base_dir: str = "data") -> None:
        assert cls_tables, "DB must have at least one table"

        self.storage = TableStorage(cls_tables, base_dir=base_dir)
        self.tables = self.storage.tables

    def insert(self, table_name: str, values: dict) -> Row:
        assert table_name in self.tables, "No such table"

        with self.storage.lock():
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

        with self.storage.lock():
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

        with self.storage.lock():
            row = self.tables[table_name].find_by_id(pk)
            if joins and row:
                for join in joins:
                    row = self.perform_join(row, join, self.tables[table_name])
        return row

    def delete_by_id(self, table_name: str, pk: int) -> None:
        assert table_name in self.tables, "No such table"

        with self.storage.lock():
            self.tables[table_name].delete_by_id(pk)

    def update_by_id(self, table_name: str, pk: int, values: dict) -> Row:
        assert table_name in self.tables, "No such table"

        with self.storage.lock():
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

        with self.storage.lock():
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

        with self.storage.lock():
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
        self.storage.close()

    def truncate(self, table_name: str, cascade: bool = False) -> None:
        assert table_name in self.tables, "No such table"

        with self.storage.lock():
            self.storage.truncate(table_name, cascade=cascade)
