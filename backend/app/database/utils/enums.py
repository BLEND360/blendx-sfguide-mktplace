import enum


class StatusEnum(enum.Enum):
    PENDING = enum.auto()
    COMPLETED = enum.auto()
    FAILED = enum.auto()
