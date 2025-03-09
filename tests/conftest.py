import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock
from jose import jwt
from datetime import datetime, timedelta, UTC
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from main import app, SECRET_KEY, ALGORITHM

@pytest.fixture
def test_client():
    """Return a TestClient instance for testing the FastAPI app."""
    with TestClient(app) as client:
        yield client

@pytest.fixture
def mock_httpx_client():
    """Mock the httpx AsyncClient to avoid making real HTTP calls."""
    with patch("httpx.AsyncClient") as mock_client:
        # Set up basic async methods
        mock_cm = AsyncMock()
        
        # Basic response for regular API calls
        mock_response = AsyncMock()
        mock_response.json.return_value = {}
        mock_response.status_code = 200
        
        # Configure the mock methods
        mock_cm.get.return_value = mock_response
        mock_cm.post.return_value = mock_response
        mock_cm.put.return_value = mock_response
        mock_cm.delete.return_value = mock_response
        
        # Set up the async context manager for the client itself
        mock_client.return_value.__aenter__.return_value = mock_cm
        
        yield mock_cm

@pytest.fixture
def auth_token():
    """Create a valid JWT token for testing authenticated endpoints."""
    payload = {
        "sub": "test@example.com",
        "exp": datetime.now(UTC) + timedelta(minutes=30)
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return token

@pytest.fixture
def auth_headers(auth_token):
    """Return headers with Authorization token for authenticated requests."""
    return {"Authorization": f"Bearer {auth_token}"}