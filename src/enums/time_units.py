from enum import IntEnum


class TimeUnit(IntEnum):
    MINUTE = 60
    HOUR = 60 * 60
    DAY = 24 * 60 * 60
    TWO_DAYS = 2 * 24 * 60 * 60
