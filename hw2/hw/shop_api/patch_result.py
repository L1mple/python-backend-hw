from enum import Enum


class PatchResult(Enum):
    NotFound = 0
    NotModified = 1
    Unprocessable = 2
