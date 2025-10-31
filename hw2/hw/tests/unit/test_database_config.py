"""Unit tests for database configuration

Tests the database configuration and setup in shop_api/database.py
"""
import pytest
from unittest.mock import AsyncMock, patch
from sqlalchemy.orm import DeclarativeBase


class TestDatabaseConfiguration:
    """Tests for database configuration"""

    def test_database_url_from_env(self, monkeypatch):
        """Test DATABASE_URL can be set from environment variable"""
        from shop_api import database

        test_url = "postgresql+asyncpg://test:test@testhost:5432/testdb"
        monkeypatch.setenv("DATABASE_URL", test_url)

        # Reimport to get new DATABASE_URL
        import importlib
        importlib.reload(database)

        assert database.DATABASE_URL == test_url

    def test_database_url_default(self):
        """Test DATABASE_URL has a default value"""
        from shop_api import database

        # This test just verifies the module loads and has DATABASE_URL
        assert hasattr(database, 'DATABASE_URL')
        assert isinstance(database.DATABASE_URL, str)
        assert 'postgresql+asyncpg://' in database.DATABASE_URL

    def test_engine_exists(self):
        """Test that engine is created"""
        from shop_api import database

        assert hasattr(database, 'engine')
        assert database.engine is not None

    def test_async_session_local_exists(self):
        """Test that AsyncSessionLocal is created"""
        from shop_api import database

        assert hasattr(database, 'AsyncSessionLocal')
        assert database.AsyncSessionLocal is not None

    def test_base_declarative_exists(self):
        """Test that Base DeclarativeBase exists"""
        from shop_api import database

        assert hasattr(database, 'Base')
        assert issubclass(database.Base, DeclarativeBase)


class TestGetDbWithMocks:
    """Tests for get_db() function with mocks"""

    async def test_get_db_success(self):
        """Test that commit and close are called on success"""
        from shop_api import database

        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_session.rollback = AsyncMock()
        mock_session.close = AsyncMock()

        # Create a mock context manager
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.return_value = mock_session
        mock_context_manager.__aexit__.return_value = None

        with patch("shop_api.database.AsyncSessionLocal", return_value=mock_context_manager):
            async for session in database.get_db():
                # Session is yielded successfully
                assert session == mock_session

        # Verify correct methods were called
        mock_session.commit.assert_awaited_once()
        mock_session.close.assert_awaited_once()
        assert mock_session.rollback.await_count == 0

    async def test_get_db_exception_during_commit(self):
        """Test exception handling when commit fails"""
        from shop_api import database

        mock_session = AsyncMock()
        mock_session.commit = AsyncMock(side_effect=RuntimeError("Commit failed"))
        mock_session.rollback = AsyncMock()
        mock_session.close = AsyncMock()

        # Create a mock context manager
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.return_value = mock_session
        mock_context_manager.__aexit__.return_value = None

        with patch("shop_api.database.AsyncSessionLocal", return_value=mock_context_manager):
            with pytest.raises(RuntimeError, match="Commit failed"):
                async for _session in database.get_db():
                    pass  # Normal work, commit happens in finally

        # Verify rollback and close were called after commit failure
        mock_session.commit.assert_awaited_once()
        mock_session.rollback.assert_awaited_once()
        mock_session.close.assert_awaited_once()
