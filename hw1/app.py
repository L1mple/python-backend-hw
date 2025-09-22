from typing import Any, Awaitable, Callable
import json
import math
from urllib.parse import parse_qs

async def json_response(send, status: int, payload: dict[str, Any]) -> None:
    await send(
        {
            "type": "http.response.start",
            "status": status,
            "headers": [(b"content-type", b"application/json")],
        }
    )
    await send(
        {
            "type": "http.response.body",
            "body": json.dumps(payload).encode(),
        }
    )

async def read_body(receive) -> bytes:
    """Считывает всё тело (даже если придёт несколькими чанками)."""
    chunks: list[bytes] = []
    more = True
    while more:
        msg = await receive()
        if msg["type"] != "http.request":
            continue
        chunks.append(msg.get("body", b""))
        more = msg.get("more_body", False)
    return b"".join(chunks)

def as_query(scope: dict[str, Any]) -> dict[str, list[str]]:
    return parse_qs(scope.get("query_string", b"").decode())


class RouteMatch:
    __slots__ = ("handler", "params")
    def __init__(self, handler, params: dict[str, str] | None = None):
        self.handler = handler
        self.params = params or {}

class Router:

    def __init__(self):
        self._static: dict[tuple[str, str], Callable] = {}
        self._dynamic: list[tuple[str, Callable]] = []  

    def add(self, method: str, path: str, handler: Callable) -> None:
        if path.endswith("/{n}") and path.startswith("/fibonacci"):
            self._dynamic.append(("/fibonacci/", handler))
        else:
            self._static[(method.upper(), path)] = handler

    def match(self, method: str, path: str) -> RouteMatch | None:
        key = (method.upper(), path)
        if key in self._static:
            return RouteMatch(self._static[key])

        for prefix, handler in self._dynamic:
            if path.startswith(prefix):
                param = path[len(prefix):]
                if param != "":
                    return RouteMatch(handler, {"n": param})
        return None

router = Router()

async def view_fibonacci(
    scope: dict[str, Any],
    receive: Callable[[], Awaitable[dict[str, Any]]],
    send: Callable[[dict[str, Any]], Awaitable[None]],
    *,
    n: str,
) -> None:
    if scope["method"] != "GET":
        return await json_response(send, 422, {"error": "Unsupported method"})

    try:
        ni = int(n)
    except ValueError:
        return await json_response(send, 422, {"error": "Invalid n"})
    if ni < 0:
        return await json_response(send, 400, {"error": "n must be non-negative"})

    a, b = 0, 1
    for _ in range(ni):
        a, b = b, a + b
    return await json_response(send, 200, {"result": a})

async def view_factorial(
    scope: dict[str, Any],
    receive: Callable[[], Awaitable[dict[str, Any]]],
    send: Callable[[dict[str, Any]], Awaitable[None]],
) -> None:
    if scope["method"] != "GET":
        return await json_response(send, 422, {"error": "Unsupported method"})

    query = as_query(scope)
    raw = query.get("n")
    if not raw or raw[0] == "":
        return await json_response(send, 422, {"error": "Invalid n"})
    try:
        n = int(raw[0])
    except ValueError:
        return await json_response(send, 422, {"error": "Invalid n"})
    if n < 0:
        return await json_response(send, 400, {"error": "n must be non-negative"})

    return await json_response(send, 200, {"result": math.factorial(n)})

async def view_mean(
    scope: dict[str, Any],
    receive: Callable[[], Awaitable[dict[str, Any]]],
    send: Callable[[dict[str, Any]], Awaitable[None]],
) -> None:
    if scope["method"] != "GET":
        return await json_response(send, 422, {"error": "Unsupported method"})

    body = await read_body(receive)
    if body:
        try:
            data = json.loads(body.decode() or "null")
        except json.JSONDecodeError:
            return await json_response(send, 422, {"error": "Invalid JSON body"})
        if not isinstance(data, list):
            return await json_response(send, 422, {"error": "Invalid JSON body"})
        if len(data) == 0:
            return await json_response(send, 400, {"error": "numbers must be non-empty list"})
        nums: list[float] = []
        for v in data:
            if isinstance(v, (int, float)):
                nums.append(float(v))
            else:
                return await json_response(send, 422, {"error": "All items must be numbers"})
        return await json_response(send, 200, {"result": sum(nums) / len(nums)})
    
    query = as_query(scope)
    param = (query.get("numbers") or [None])[0]
    if param is None:
        return await json_response(send, 422, {"error": "Invalid JSON body"})
    parts = [p.strip() for p in param.split(",") if p.strip()]
    if not parts:
        return await json_response(send, 400, {"error": "numbers must be non-empty list"})
    try:
        nums = [float(p) for p in parts]
    except ValueError:
        return await json_response(send, 422, {"error": "All items must be numbers"})
    return await json_response(send, 200, {"result": sum(nums) / len(nums)})


router.add("GET", "/factorial", view_factorial)
router.add("GET", "/mean",      view_mean)
router.add("GET", "/fibonacci/{n}", view_fibonacci)  

async def lifespan_app(
    receive: Callable[[], Awaitable[dict[str, Any]]],
    send: Callable[[dict[str, Any]], Awaitable[None]],
) -> None:
    while True:
        msg = await receive()
        t = msg.get("type")
        if t == "lifespan.startup":
            await send({"type": "lifespan.startup.complete"})
        elif t == "lifespan.shutdown":
            await send({"type": "lifespan.shutdown.complete"})
            return


async def application(
    scope: dict[str, Any],
    receive: Callable[[], Awaitable[dict[str, Any]]],
    send: Callable[[dict[str, Any]], Awaitable[None]],
):
    """
    Args:
        scope: Словарь с информацией о запросе
        receive: Корутина для получения сообщений от клиента
        send: Корутина для отправки сообщений клиенту
    """
    stype = scope.get("type")
    if stype == "lifespan":
        return await lifespan_app(receive, send)

    if stype != "http":
        return

    method = scope["method"]
    path = scope["path"]

    match = router.match(method, path)
    if match is None:
        return await json_response(send, 404, {"error": "Not found"})

    if match.params:
        return await match.handler(scope, receive, send, **match.params)
    else:
        return await match.handler(scope, receive, send)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:application", host="0.0.0.0", port=8000, reload=True)
