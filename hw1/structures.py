from typing import TypedDict

class HTTPResponse(TypedDict):
    """Типизированный ответ обработчика"""
    status: int
    body: dict

class HTTPError(Exception):
    """Кастомное исключение для HTTP ошибок"""

    def __init__(self, status: int, error: str, message: str):
        self.status = status
        self.error = error
        self.message = message
        super().__init__(f"{error}: {message}")