from abc import ABC, abstractmethod

from .row import Row


class BaseCond(ABC):
    def __init__(self, **params) -> None:
        assert params

        self.params = params

    @abstractmethod
    def eval(self, row: Row) -> bool: ...


class EQ(BaseCond):
    def eval(self, row: Row) -> bool:
        for field_name, value in self.params.items():
            if row.get(field_name) != value:
                return False
        return True


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
