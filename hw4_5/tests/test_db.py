import pytest
from src.db.deps import get_db



@pytest.mark.asyncio
async def test_get_db():
    async for session in get_db():
        assert session is not None
        break