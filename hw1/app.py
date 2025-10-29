from typing import Any, Awaitable, Callable
from urllib.parse import parse_qs
import json


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
    async def j(status: int, data: dict[str, Any]):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        hdrs = [
            (b"content-type", b"application/json; charset=utf-8"),
            (b"content-length", str(len(body)).encode("ascii")),
        ]
        await send({"type": "http.response.start", "status": status, "headers": hdrs})
        await send({"type": "http.response.body", "body": body})

    async def grab_body() -> bytes:
        buf = b""
        more = True
        while more:
            m = await receive()
            if m.get("type") != "http.request":
                continue
            buf += m.get("body", b"")
            more = m.get("more_body", False)
        return buf

    if scope["type"] == "lifespan":
        while True:
            msg = await receive()
            if msg["type"] == "lifespan.startup":
                print("boot")
                await send({"type": "lifespan.startup.complete"})
            elif msg["type"] == "lifespan.shutdown":
                print("bye")
                await send({"type": "lifespan.shutdown.complete"})
                return
        return

    if scope["type"] != "http":
        return

    verb = scope.get("method", "GET").upper()
    pth = scope.get("path", "")
    qs = parse_qs(scope.get("query_string", b"").decode("latin-1"))

    known = (pth == "/factorial") or (pth == "/mean") or pth.startswith("/fibonacci")
    if verb != "GET":
        if known:
            print("405")
            await j(405, {"detail": "method not allowed. use GET."})
        else:
            print("404")
            await j(404, {"detail": "not found."})
        return

    if pth == "/factorial":
        print("hit /factorial")
        raw_n_list = qs.get("n") or qs.get("N")

        if not raw_n_list or raw_n_list[0] == "":
            print("bad n")
            await j(422, {"detail": "query param 'n' is required and must be integer."})
            return

        try:
            n = int(raw_n_list[0])
        except Exception:
            print("not int")
            await j(422, {"detail": "'n' must be an integer."})
            return

        if n < 0:
            print("neg n")
            await j(400, {"detail": "factorial is for non-negative integers only."})
            return

        # inplace kringe but sorry
        out = 1
        k = 2
        while k <= n:
            out *= k
            k += 1

        print("ok")
        await j(200, {"result": out})
        return

    if pth.startswith("/fibonacci"):
        print("hit /fibonacci")
        parts = pth.split("/", 2)
        raw_n = parts[2] if len(parts) > 2 and parts[1] == "fibonacci" else ""

        try:
            n = int(raw_n)
        except Exception:
            print("bad path n")
            await j(422, {"detail": "path param must be an integer."})
            return

        if n < 0:
            print("neg n")
            await j(400, {"detail": "fibonacci is for non-negative integers only."})
            return

        a, b = 0, 1
        i = 0
        while i < n:
            a, b = b, a + b
            i += 1

        print("ok")
        await j(200, {"result": a})
        return

    if pth == "/mean":
        print("hit /mean")
        raw = await grab_body()

        if not raw:
            print("no json")
            await j(422, {"detail": "json body is required."})
            return

        try:
            data = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            print("bad json")
            await j(422, {"detail": "body must be valid json."})
            return

        if isinstance(data, list):
            arr = data
        elif isinstance(data, dict) and ("numbers" in data):
            arr = data["numbers"]
        else:
            print("missing numbers")
            await j(422, {"detail": "expected array or object with numbers"})
            return

        try:
            nums = [float(x) for x in arr]
        except Exception:
            print("not floats")
            await j(422, {"detail": "numbers must be an array of numbers"})
            return

        if not nums:
            print("empty")
            await j(400, {"detail": "numbers list is empty"})
            return

        mean_val = sum(nums) / len(nums)
        print("ok")
        await j(200, {"result": mean_val})
        return

    print("404")
    await j(404, {"detail": "not found."})


if __name__ == "__main__":
    import uvicorn
    print("test app")
    uvicorn.run("app:application", host="0.0.0.0", port=8000, reload=True)