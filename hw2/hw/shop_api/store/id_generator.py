from typing import Iterable


def int_id_generator() -> Iterable[int]:
    i = 0
    while True:
        yield i
        i += 1

id_generator = int_id_generator()