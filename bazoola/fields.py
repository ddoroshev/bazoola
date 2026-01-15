from abc import ABC, abstractmethod
from typing import Any, NamedTuple

from .const import INT_SIZE
from .errors import ValidationError


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
    def __init__(self, size: int = INT_SIZE, null: bool = False) -> None:
        super().__init__(size, null)

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
        super().__init__(null=False)


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


class TEXT(INT):
    pass


class Field(NamedTuple):
    name: str
    type: FieldType

    def validate(self, val: Any) -> None:
        try:
            self.type.validate(val)
        except ValidationError as e:
            raise ValidationError(f"'{self.name}': {e.message}")
