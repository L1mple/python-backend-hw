from typing import Any, Callable, Optional, Dict, TypedDict
import re
from http import HTTPStatus
from structures import HTTPResponse, HTTPError

def build_error_response(status: int, error: str, message: str) -> HTTPResponse:
    response: HTTPResponse = {
        'status': status,
        'body': {
            'error': error,
            'message': message
        }
    }
    return response

class Router:

    def __init__(self):
        self.routes = []
        self.handlers: Dict[str, Callable] = {}

    def add_route(self, method: str, path: str, handler: Callable):
        """Добавляет маршрут"""
        pattern = self._path_to_pattern(path)
        self.routes.append({
            'method': method.upper(),
            'pattern': pattern,
            'handler': handler
        })

    @staticmethod
    def _path_to_pattern(path: str) -> re.Pattern:
        """Конвертирует путь с параметрами в regex паттерн"""
        pattern = re.sub(r'\{(\w+)}', r'(?P<\1>[^/]+)', path)
        return re.compile(f'^{pattern}$')

    async def route(self, method: str, path: str, query_string: str, body: Optional[Any]) -> tuple[Callable, dict]:
        method = method.upper()

        route_match = self._match_route(method, path)
        if not route_match:
            raise HTTPError(HTTPStatus.NOT_FOUND, "Not Found", "Endpoint not found")

        handler, path_params = route_match

        query_params = self._parse_query_string(query_string)

        request_context = {
            'path_params': path_params,
            'query_params': query_params,
            'body': body
        }

        return handler, request_context

    def _match_route(self, method: str, path: str) -> Optional[tuple[Callable, dict]]:
        """Ищет подходящий маршрут и возвращает handler"""
        for route in self.routes:
            if route['method'] != method:
                continue

            match = route['pattern'].match(path)
            if match:
                return route['handler'], match.groupdict()

        return None

    @staticmethod
    def _parse_query_string(query_string: str) -> dict:
        """Парсит query string в словарь"""
        params = {}
        if query_string:
            for pair in query_string.split('&'):
                if '=' in pair:
                    key, value = pair.split('=', 1)
                    params[key] = value
        return params