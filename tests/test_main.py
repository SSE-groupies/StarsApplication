import pytest
from unittest.mock import MagicMock
import json
import sys
import os

# Add the parent directory to the path so we can import the main module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Test public endpoints

def test_get_stars(test_client, mock_httpx_client):
    """Test the GET /stars endpoint."""
    # Mock the response from the database service
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = [
        {"id": 1, "name": "Star 1", "message": "First star"},
        {"id": 2, "name": "Star 2", "message": "Second star"}
    ]
    mock_httpx_client.get.return_value = mock_response
    
    # Make request to the API
    response = test_client.get("/stars")
    
    # Verify the response
    assert response.status_code == 200
    assert len(response.json()) == 2
    assert response.json()[0]["name"] == "Star 1"
    
    # Verify the API called the database service
    mock_httpx_client.get.assert_called_once()

def test_get_star_by_id(test_client, mock_httpx_client):
    """Test the GET /stars/{star_id} endpoint."""
    # Mock the response from the database service
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"id": 1, "name": "Star 1", "message": "First star"}
    mock_httpx_client.get.return_value = mock_response
    
    # Make request to the API
    response = test_client.get("/stars/1")
    
    # Verify the response
    assert response.status_code == 200
    assert response.json()["id"] == 1
    assert response.json()["name"] == "Star 1"
    
    # Verify the API called the database service
    mock_httpx_client.get.assert_called_once()

def test_get_star_by_id_not_found(test_client, mock_httpx_client):
    """Test the GET /stars/{star_id} endpoint with a non-existent ID."""
    # Mock the response from the database service for a not found star
    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_response.text = "Star not found"
    mock_httpx_client.get.return_value = mock_response
    
    # Make request to the API
    response = test_client.get("/stars/999")
    
    # Verify the response
    assert response.status_code == 404
    assert "Star not found" in response.text

# Test authenticated endpoints

def test_create_star_authenticated(test_client, mock_httpx_client, auth_headers):
    """Test the POST /stars endpoint with authentication."""
    # Mock the filter service response (content is acceptable)
    filter_mock_response = MagicMock()
    filter_mock_response.status_code = 200
    filter_mock_response.json.return_value = {"status": True, "message": "Content is acceptable"}
    
    # Mock the database service response
    db_mock_response = MagicMock()
    db_mock_response.status_code = 200
    db_mock_response.json.return_value = {"id": 3, "name": "New Star", "message": "Test message"}
    
    # Set up the mock to return the appropriate responses
    mock_httpx_client.post.side_effect = [filter_mock_response, db_mock_response]
    
    # Test data
    star_data = {
        "name": "New Star",
        "message": "Test message"
    }
    
    # Make request to the API
    response = test_client.post("/stars", json=star_data, headers=auth_headers)
    
    # Verify the response
    assert response.status_code == 200
    assert response.json()["id"] == 3
    assert response.json()["name"] == "New Star"
    
    # Verify the calls to external services
    assert mock_httpx_client.post.call_count == 2  # One to filter, one to DB

def test_create_star_unauthenticated(test_client):
    """Test the POST /stars endpoint without authentication."""
    # Make request to the API without auth headers
    star_data = {"name": "New Star", "message": "Test message"}
    response = test_client.post("/stars", json=star_data)
    
    # Verify the response (should be unauthorized)
    assert response.status_code == 401

def test_create_star_filtered_content(test_client, mock_httpx_client, auth_headers):
    """Test the POST /stars endpoint with inappropriate content."""
    # Mock the filter service response (content is inappropriate)
    filter_mock_response = MagicMock()
    filter_mock_response.status_code = 200
    filter_mock_response.json.return_value = {"status": False, "message": "Content contains inappropriate language"}
    
    # Set up the mock to return the filter response
    mock_httpx_client.post.return_value = filter_mock_response
    
    # Test data with inappropriate content
    star_data = {
        "name": "Bad Star",
        "message": "Inappropriate content"
    }
    
    # Make request to the API
    response = test_client.post("/stars", json=star_data, headers=auth_headers)
    
    # Verify the response
    assert response.status_code == 200
    assert response.json()["status"] is False
    assert "inappropriate" in response.json()["message"].lower()
    
    # Verify only the filter service was called, not the DB service
    assert mock_httpx_client.post.call_count == 1

def test_delete_star(test_client, mock_httpx_client, auth_headers):
    """Test the DELETE /stars/{star_id} endpoint."""
    # Mock the response from the database service
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"message": "Star deleted successfully"}
    mock_httpx_client.delete.return_value = mock_response
    
    # Make request to the API
    response = test_client.delete("/stars/1", headers=auth_headers)
    
    # Verify the response
    assert response.status_code == 200
    assert "deleted successfully" in response.json()["message"].lower()
    
    # Verify the API called the database service
    mock_httpx_client.delete.assert_called_once()

def test_delete_star_unauthenticated(test_client):
    """Test the DELETE /stars/{star_id} endpoint without authentication."""
    # Make request to the API without auth headers
    response = test_client.delete("/stars/1")
    
    # Verify the response (should be unauthorized)
    assert response.status_code == 401

def test_like_star(test_client, mock_httpx_client, auth_headers):
    """Test the POST /stars/{star_id}/like endpoint."""
    # Mock the response from the database service
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"id": 1, "likes": 5, "dislikes": 2}
    mock_httpx_client.post.return_value = mock_response
    
    # Make request to the API
    response = test_client.post("/stars/1/like", headers=auth_headers)
    
    # Verify the response
    assert response.status_code == 200
    assert response.json()["likes"] == 5
    
    # Verify the API called the database service
    mock_httpx_client.post.assert_called_once()

def test_dislike_star(test_client, mock_httpx_client, auth_headers):
    """Test the POST /stars/{star_id}/dislike endpoint."""
    # Mock the response from the database service
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"id": 1, "likes": 5, "dislikes": 3}
    mock_httpx_client.post.return_value = mock_response
    
    # Make request to the API
    response = test_client.post("/stars/1/dislike", headers=auth_headers)
    
    # Verify the response
    assert response.status_code == 200
    assert response.json()["dislikes"] == 3
    
    # Verify the API called the database service
    mock_httpx_client.post.assert_called_once()

def test_delete_all_stars(test_client, mock_httpx_client, auth_headers):
    """Test the DELETE /stars endpoint."""
    # Mock the response from the database service
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"message": "All stars deleted successfully"}
    mock_httpx_client.delete.return_value = mock_response
    
    # Make request to the API
    response = test_client.delete("/stars", headers=auth_headers)
    
    # Verify the response
    assert response.status_code == 200
    assert "deleted successfully" in response.json()["message"].lower()
    
    # Verify the API called the database service
    mock_httpx_client.delete.assert_called_once() 