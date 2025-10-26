class ItemNotFoundError(Exception):
    """Исключение при отсутствии товара."""


class ItemDeletedError(Exception):
    """Исключение для удалённого товара."""