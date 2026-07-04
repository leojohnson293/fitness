"""
tests/conftest.py
──────────────────
Shared pytest fixtures — database mock applied automatically to all tests.
"""

import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

# Set dummy DATABASE_URL before anything imports database.py
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost/test")


@pytest.fixture(autouse=True)
def mock_db_pool():
    """
    Automatically mock get_pool() for every test.
    
    autouse=True means this runs for every test without needing to
    explicitly request the fixture — no changes needed in test files.
    """
    mock_pool = MagicMock()
    mock_conn = AsyncMock()

    mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)
 
    # transaction() must be a sync MagicMock returning an async context manager —
    # NOT an AsyncMock, otherwise calling it returns a coroutine instead of
    # something with __aenter__/__aexit__
    mock_transaction_cm = MagicMock()
    mock_transaction_cm.__aenter__ = AsyncMock(return_value=None)
    mock_transaction_cm.__aexit__ = AsyncMock(return_value=False)
    mock_conn.transaction = MagicMock(return_value=mock_transaction_cm)
    
    # Patch get_pool in each router that imports it directly
    with patch("routers.meals.get_pool", return_value=mock_pool), \
         patch("routers.weight.get_pool", return_value=mock_pool), \
         patch("routers.foods.get_pool", return_value=mock_pool), \
         patch("routers.workouts.get_pool", return_value=mock_pool), \
         patch("routers.templates.get_pool", return_value=mock_pool):
        yield mock_conn

