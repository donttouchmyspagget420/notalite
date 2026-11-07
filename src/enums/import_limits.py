from enum import IntEnum


class ImportLimit(IntEnum):
    FILES = 10
    BYTES = 25 * 1024 * 1024
