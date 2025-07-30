from __future__ import annotations

import fcntl
import os
from contextlib import contextmanager
from typing import BinaryIO, Generator

from .errors import DBError


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
