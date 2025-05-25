from abc import ABC, abstractmethod
from mmap import mmap
from pathlib import Path
import os
import time
import uuid
import random
from typing import List, Tuple

from smbprotocol.connection import Connection
from smbprotocol.open import Open, CreateDisposition, FilePipePrinterAccessMask, ImpersonationLevel
from smbprotocol.session import Session
from smbprotocol.tree import TreeConnect

from benchmark.config import BLOCK_SIZE


class FileHandler(ABC):
    @abstractmethod
    def create(self):
        """Создает файл, если он не еще не был создан."""

    @abstractmethod
    def initialize(self):
        """Заполняет файл случайными данными."""

    @abstractmethod
    def delete(self): pass

    @abstractmethod
    def read_blocks(self, n=None, time_end=None, random_access=False):
        """Читает n блоков из файла не более time_end секунд."""

    @abstractmethod
    def write_blocks(self, n=None, time_end=None, random_access=False):
        """Пишет n блоков в файл не более time_end секунд."""

    @abstractmethod
    def file_name(self): pass

    @abstractmethod
    def file_size(self): pass


class FileHandlerException(Exception):
    """Исключение для ошибок при работе с файлами."""

    def __init__(self, message: str, filepath: str = None):
        self.message = message
        self.filepath = filepath
        super().__init__(message)

    def __str__(self):
        details = []
        if self.filepath:
            details.append(f"file: {self.filepath}")
        return f"{self.message} ({', '.join(details)})" if details else self.message


class FSFileHandler(FileHandler):
    def __init__(self, basepath=".", filename=None, size=1024 ** 2, block_size=BLOCK_SIZE, binary=True):
        self.filename = filename or f"{uuid.uuid4()}"
        self.size = size
        self.block_size = block_size
        self.binary = binary
        self.mode = 'b' if binary else ''
        self.path = Path(basepath) / self.filename
        self.created = False
        self.initialized = False

    def create(self):
        if self.created:
            return
        if not self.path.exists():
            # os.close(os.open(str(self.path), os.O_CREAT | os.O_WRONLY, 0o644))
            # self.path.touch()
            with open(str(self.path), 'wb') as f:
                f.write(b'\0' * self.size)
        self.created = True

    def initialize(self):
        if self.initialized:
            return

        self.create()
        mode = f'w{self.mode}+'
        try:
            with open(str(self.path), mode) as f:
                for _ in range(self.size // self.block_size):
                    data = self._random_block()
                    f.write(data if self.binary else data.encode())
            self.initialized = True
        except (IOError, OSError) as e:
            raise FileHandlerException(str(e), self.filename)

    def delete(self):
        if not self.created:
            return
        try:
            if self.path.exists():
                self.path.unlink()
            self.created = False
            self.initialized = False
        except (IOError, OSError) as e:
            raise FileHandlerException(str(e), self.filename)

    def _do_io(self, mode, op_count=None, time_end=None, random_access=False) -> Tuple[List[Tuple[float, float]], bool]:
        access_mode = f'{mode}{self.mode}'

        try:
            start_time = time.time()
            fd = os.open(str(self.path), os.O_RDWR | getattr(os, "O_DIRECT", 0))
            if fd == 0:
                print("zero fd", self.path)
            with os.fdopen(fd, access_mode, buffering=0) as f:
                file_size = self.file_size()
                block = self._random_block()
                positions = list(range(0, file_size, self.block_size))
                ops = 0
                units = []
                prev_time = time.time()
                while (op_count and ops < op_count) and (not time_end or time.time() < time_end):
                    pos = random.choice(positions) if random_access else positions[ops % len(positions)]
                    try:
                        if random_access:
                            os.lseek(fd, pos, os.SEEK_SET)
                        if mode == 'r':
                            os.read(fd, self.block_size)
                        elif mode == 'r+':
                            os.write(fd, block)
                    except (IOError, OSError) as e:
                        print("io_operation_error_2", e, self.path)
                        return units, True
                    now_time = time.time()
                    units.append((now_time - start_time, now_time - prev_time))
                    prev_time = now_time
                    ops += 1
                return units, False
        except (IOError, OSError) as e:
            print("io_operation_error", e, self.path)
            raise FileHandlerException(str(e), self.filename)

    def read_blocks(self, n=None, time_end=None, random_access=False):
        return self._do_io('r', op_count=n, time_end=time_end, random_access=random_access)

    def write_blocks(self, n=None, time_end=None, random_access=False):
        return self._do_io('r+', op_count=n, time_end=time_end, random_access=random_access)

    def _aligned_buffer(self, size):
        buf = mmap(-1, size + BLOCK_SIZE)
        offset = 0
        return buf[offset:offset + size]

    def _random_block(self):
        if self.binary:
            return os.urandom(self.block_size) # self._aligned_buffer(self.block_size)  #
        return ''.join(random.choices('abcdefghijklmnopqrstuvwxyz', k=self.block_size))

    def file_name(self):
        return self.filename

    def file_size(self):
        return self.size


class SMBFileHandler(FileHandler):
    def __init__(self, server, share, username, password, filename=None, size=1024 ** 2, block_size=4096, binary=True):
        self.server = server
        self.share = share
        self.username = username
        self.password = password
        self.filename = filename or f"{uuid.uuid4()}"
        self.size = size
        self.block_size = block_size
        self.binary = binary
        self.created = False
        self.initialized = False

        # SMB connection objects
        self.connection = None
        self.session = None
        self.tree = None

    def _ensure_connected(self):
        if not self.connection:
            self.connection = Connection(uuid.uuid4(), self.server)
            self.connection.connect()

            self.session = Session(self.connection, self.username, self.password)
            self.session.connect()

            self.tree = TreeConnect(self.session, f"\\\\{self.server}\\{self.share}")
            self.tree.connect()

    def create(self):
        if self.created:
            return

        self._ensure_connected()

        try:
            create_disposition = CreateDisposition.FILE_OPEN_IF
            desired_access = FilePipePrinterAccessMask.GENERIC_READ | FilePipePrinterAccessMask.GENERIC_WRITE

            with Open(self.tree, self.filename,
                      desired_access=desired_access,
                      create_disposition=create_disposition,
                      impersonation_level=ImpersonationLevel.Impersonation) as f:
                pass

            self.created = True
        except Exception as e:
            raise FileHandlerException(str(e), self.filename)

    def initialize(self):
        if self.initialized:
            return

        self._ensure_connected()
        self.create()

        try:
            create_disposition = CreateDisposition.FILE_OVERWRITE_IF
            desired_access = FilePipePrinterAccessMask.GENERIC_READ | FilePipePrinterAccessMask.GENERIC_WRITE

            with Open(self.tree, self.filename,
                      desired_access=desired_access,
                      create_disposition=create_disposition,
                      impersonation_level=ImpersonationLevel.Impersonation) as f:

                # Write all blocks to initialize the file
                for _ in range(self.size // self.block_size):
                    data = self._random_block()
                    if not self.binary:
                        data = data.encode()
                    f.write(data)

            self.initialized = True
        except Exception as e:
            raise FileHandlerException(str(e), self.filename)

    def delete(self):
        if not self.created:
            return

        self._ensure_connected()

        try:
            create_disposition = CreateDisposition.FILE_OPEN
            desired_access = FilePipePrinterAccessMask.DELETE

            with Open(self.tree, self.filename,
                      desired_access=desired_access,
                      create_disposition=create_disposition,
                      impersonation_level=ImpersonationLevel.Impersonation) as f:
                f.delete()

            self.created = False
            self.initialized = False
        except Exception as e:
            raise FileHandlerException(str(e), self.filename)

    def _do_io(self, mode, op_count=None, time_end=None, random_access=False):
        self._ensure_connected()

        try:
            create_disposition = CreateDisposition.FILE_OPEN
            desired_access = FilePipePrinterAccessMask.GENERIC_READ
            if mode == 'r+':
                desired_access |= FilePipePrinterAccessMask.GENERIC_WRITE

            with Open(self.tree, self.filename,
                      desired_access=desired_access,
                      create_disposition=create_disposition,
                      impersonation_level=ImpersonationLevel.Impersonation) as f:

                file_size = self.file_size()
                positions = list(range(0, file_size, self.block_size))
                ops = 0

                while (op_count and ops < op_count) and (not time_end or time.time() < time_end):
                    pos = random.choice(positions) if random_access else positions[ops % len(positions)]
                    f.seek(pos)

                    if mode == 'r':
                        f.read(self.block_size)
                    elif mode == 'r+':
                        data = self._random_block()
                        if not self.binary:
                            data = data.encode()
                        f.write(data)

                    ops += 1

                return ops
        except Exception as e:
            raise FileHandlerException(str(e), self.filename)

    def read_blocks(self, n=None, time_end=None, random_access=False):
        return self._do_io('r', op_count=n, time_end=time_end, random_access=random_access)

    def write_blocks(self, n=None, time_end=None, random_access=False):
        return self._do_io('r+', op_count=n, time_end=time_end, random_access=random_access)

    def _random_block(self):
        if self.binary:
            return os.urandom(self.block_size)
        return ''.join(random.choices('abcdefghijklmnopqrstuvwxyz', k=self.block_size))

    def file_name(self):
        return self.filename

    def file_size(self):
        return self.size

    def __del__(self):
        if self.tree:
            try:
                self.tree.disconnect()
            except:
                pass
        if self.session:
            try:
                self.session.disconnect()
            except:
                pass
        if self.connection:
            try:
                self.connection.disconnect()
            except:
                pass


if __name__ == '__main__':
    h = FSFileHandler(basepath="_test", size=1024 ** 2)
    h.create()
    h.write_blocks(n=10)
