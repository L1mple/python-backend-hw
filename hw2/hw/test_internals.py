import importlib
import os

import pytest

from shop_api import db as db_mod
from shop_api.main import app, chat_manager, on_startup


def test_on_startup_creates_schema() -> None:
    on_startup()


def test_session_scope_commit_and_rollback() -> None:
    from shop_api.models import Item

    with db_mod.session_scope() as s:
        s.add(Item(name="committed", price=1.0, deleted=False))

    with db_mod.session_scope() as s:
        items = list(s.query(Item).filter_by(name="committed"))
        assert any(i.name == "committed" for i in items)

    with pytest.raises(RuntimeError):
        with db_mod.session_scope() as s:
            s.add(Item(name="rolled", price=2.0, deleted=False))
            raise RuntimeError("force rollback")

    with db_mod.session_scope() as s:
        items = list(s.query(Item).filter_by(name="rolled"))
        assert not any(i.name == "rolled" for i in items)


def test_build_database_url_respects_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://user:pass@localhost:5432/db")
    importlib.reload(db_mod)
    assert db_mod.DATABASE_URL.startswith("postgresql")


def test_make_engine_sqlite_and_non_sqlite(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "sqlite:///./tmp_test.db")
    mod = importlib.reload(db_mod)
    engine_sqlite = mod._make_engine()
    assert engine_sqlite.url.get_backend_name() == "sqlite"

    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u:p@localhost:5432/d")
    mod = importlib.reload(db_mod)
    engine_pg = mod._make_engine()
    assert engine_pg.url.get_backend_name().startswith("postgresql")


class DummyWS:
    def __init__(self) -> None:
        self.sent: list[str] = []

    async def accept(self):
        return None

    async def send_text(self, message: str):
        raise RuntimeError("send failed")


def test_chat_username_for_unknown() -> None:
    dummy = DummyWS()
    assert chat_manager.username_for(dummy) == "unknown"


@pytest.mark.asyncio
async def test_broadcast_handles_exception_and_cleans_room() -> None:
    room = "r1"
    ws = DummyWS()
    chat_manager.rooms[room] = {ws}
    await chat_manager.broadcast(room, "msg")
    assert room not in chat_manager.rooms or ws not in chat_manager.rooms.get(room, set())


