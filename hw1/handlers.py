import json
from functools import lru_cache
from typing import Callable, Any
from urllib.parse import parse_qs


class BaseHandler:
    @staticmethod
    async def read_body(receive: Callable[[], Any]) -> bytes:
        body = b""
        while True:
            message = await receive()
            if message.get("type") != "http.request":
                break
            body += message.get("body", b"") or b""
            if not message.get("more_body"):
                break
        return body

    @classmethod
    async def send_response(cls, send: Callable[[dict], Any], status: int, data: dict) -> None:
        await send({
            "type": "http.response.start",
            "status": status,
            "headers": [[b"content-type", b"application/json"]],
        })
        await send({
            "type": "http.response.body",
            "body": json.dumps(data).encode("utf-8"),
        })


@lru_cache()
def _fib(n: int) -> int:
    if n < 2:
        return n
    return _fib(n - 1) + _fib(n - 2)


class FibonacciHandler(BaseHandler):
    @classmethod
    async def handle(cls, path: str, send: Callable[[dict], Any]) -> None:
        try:
            # Expect path like /fibonacci/<n>
            parts = path.rstrip("/").split("/")
            if len(parts) < 3 or parts[-1] == "fibonacci":
                await cls.send_response(send, 422, {"error": "Invalid data"})
                return

            n_str = parts[-1]
            n = int(n_str)
            if n < 0:
                await cls.send_response(send, 400, {"error": 'Parameter "n" must be non-negative'})
                return

            result = _fib(n)
            await cls.send_response(send, 200, {"result": result})
        except ValueError:
            await cls.send_response(send, 422, {"error": "Invalid data"})
        except Exception as exc:  # pragma: no cover - unexpected
            await cls.send_response(send, 500, {"error": f"Internal server error: {exc}"})


class FactorialHandler(BaseHandler):
    @lru_cache()
    @staticmethod
    def _factorial(n: int) -> int:
        r = 1
        for i in range(2, n + 1):
            r *= i
        return r

    @classmethod
    async def handle(cls, query_string: bytes, send: Callable[[dict], Any]) -> None:
        try:
            qs = parse_qs(query_string.decode("utf-8")) if query_string else {}
            values = qs.get("n")
            if not values:
                await cls.send_response(send, 422, {"error": "Invalid data"})
                return

            n_str = values[0]
            if n_str == "":
                await cls.send_response(send, 422, {"error": "Invalid data"})
                return

            n = int(n_str)
            if n < 0:
                await cls.send_response(send, 400, {"error": 'Parameter "n" must be non-negative'})
                return

            result = cls._factorial(n)
            await cls.send_response(send, 200, {"result": result})
        except ValueError:
            await cls.send_response(send, 422, {"error": "Invalid data"})
        except Exception as exc:  
            await cls.send_response(send, 500, {"error": f"Internal server error: {exc}"})


class MeanHandler(BaseHandler):
    @classmethod
    async def handle(cls, receive: Callable[[], Any], send: Callable[[dict], Any]) -> None:
        body = await cls.read_body(receive)
        if not body:
            await cls.send_response(send, 422, {"error": "Invalid data"})
            return

        try:
            data = json.loads(body)
        except Exception:
            await cls.send_response(send, 422, {"error": "Invalid data"})
            return

        if not isinstance(data, list):
            await cls.send_response(send, 422, {"error": "Invalid data"})
            return

        if len(data) == 0:
            await cls.send_response(send, 400, {"error": "List must not be empty"})
            return

        if not all(isinstance(x, (int, float)) for x in data):
            await cls.send_response(send, 422, {"error": "Invalid data"})
            return

        result = sum(data) / len(data)
        await cls.send_response(send, 200, {"result": result})
