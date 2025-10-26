import pytest
from shop_api.main import _rooms, _bcast, _uname

class _BadWS:
    async def send_text(self, txt):
        raise RuntimeError("boom")

class _SenderWS:
    async def send_text(self, txt):
        return None

def test_uname_prefix():
    assert _uname().startswith("u")

@pytest.mark.asyncio
async def test_bcast_removes_dead_ws():
    room = "r1"
    bad = _BadWS()
    sender = _SenderWS()
    _rooms[room].add(bad)
    await _bcast(room, sender, "x")
    assert bad not in _rooms[room]