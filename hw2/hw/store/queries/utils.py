from typing import Iterable



def id_generator() -> Iterable[int]:
    i = 0
    while True:
        yield i
        i += 1