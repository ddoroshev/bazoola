from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .table import Table


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
