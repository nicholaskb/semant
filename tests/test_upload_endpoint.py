"""Test the /api/upload-image endpoint thoroughly"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
from io import BytesIO

import main as main_mod

@pytest.fixture
def client():
    """Create a test client for the FastAPI app"""
    return TestClient(main_mod.app)


def test_upload_image_endpoint_missing_file(client):
    """Test upload without a file"""
    response = client.post("/api/upload-image")
    assert response.status_code == 422  # Validation error


@patch("main.upload_to_gcs_and_get_public_url")
@patch("main._kg_logger_uploads")
async def test_upload_image_endpoint_success(mock_kg_logger, mock_upload_gcs, client):
    """Test successful image upload"""
    # Mock GCS upload function
    mock_upload_gcs.return_value = "https://storage.googleapis.com/test-bucket/test-image.png"
    
    # Mock KG logger
    mock_kg_logger.log_tool_call = AsyncMock()
    
    # Create a test image file
    test_file_content = b"fake image content"
    test_file = BytesIO(test_file_content)
    
    # Send POST request with file
    response = client.post(
        "/api/upload-image",
        files={"image_file": ("test_image.png", test_file, "image/png")}
    )
    
    # Check response
    assert response.status_code == 200
    data = response.json()
    assert "url" in data
    assert data["url"] == "https://storage.googleapis.com/test-bucket/test-image.png"
    
    # Verify GCS upload was called
    assert mock_upload_gcs.called
    
    # Check that the file content and metadata were passed correctly
    call_args = mock_upload_gcs.call_args
    assert len(call_args[0]) == 3  # file_content, unique_filename, content_type
    assert call_args[0][0] == test_file_content
    assert call_args[0][2] == "image/png"


@patch("main.upload_to_gcs_and_get_public_url")
async def test_upload_image_endpoint_gcs_failure(mock_upload_gcs, client):
    """Test upload when GCS fails"""
    # Mock GCS upload to raise an exception
    mock_upload_gcs.side_effect = Exception("GCS upload failed")
    
    # Create a test image file
    test_file = BytesIO(b"fake image content")
    
    # Send POST request with file
    response = client.post(
        "/api/upload-image",
        files={"image_file": ("test_image.png", test_file, "image/png")}
    )
    
    # Check error response
    assert response.status_code == 500
    assert "GCS upload failed" in response.json()["detail"]


def test_upload_image_endpoint_no_filename(client):
    """Test upload with file but no filename"""
    # Create a test image file without filename
    test_file = BytesIO(b"fake image content")
    
    # Send POST request with file without filename
    response = client.post(
        "/api/upload-image",
        files={"image_file": (None, test_file, "image/png")}
    )
    
    # Should reject due to validation error (FastAPI returns 422 for validation errors)
    assert response.status_code in [400, 422]  # Accept either validation error or bad request
    # FastAPI may reject this at validation level before our code runs


@patch("main.upload_to_gcs_and_get_public_url")
@patch("main._kg_logger_uploads")
async def test_upload_image_kg_logging_failure_continues(mock_kg_logger, mock_upload_gcs, client):
    """Test that KG logging failure doesn't break the upload"""
    # Mock GCS upload function
    mock_upload_gcs.return_value = "https://storage.googleapis.com/test-bucket/test-image.png"
    
    # Mock KG logger to fail
    mock_kg_logger.log_tool_call = AsyncMock(side_effect=Exception("KG logging failed"))
    
    # Create a test image file
    test_file = BytesIO(b"fake image content")
    
    # Send POST request with file
    response = client.post(
        "/api/upload-image",
        files={"image_file": ("test_image.png", test_file, "image/png")}
    )
    
    # Should still succeed despite KG logging failure
    assert response.status_code == 200
    data = response.json()
    assert "url" in data
    assert data["url"] == "https://storage.googleapis.com/test-bucket/test-image.png"


@patch("main.upload_to_gcs_and_get_public_url")
async def test_upload_multiple_file_types(mock_upload_gcs, client):
    """Test uploading different file types"""
    mock_upload_gcs.return_value = "https://storage.googleapis.com/test-bucket/test-file"
    
    file_types = [
        ("test.jpg", "image/jpeg"),
        ("test.png", "image/png"),
        ("test.gif", "image/gif"),
        ("test.webp", "image/webp")
    ]
    
    for filename, content_type in file_types:
        test_file = BytesIO(b"fake content")
        response = client.post(
            "/api/upload-image",
            files={"image_file": (filename, test_file, content_type)}
        )
        
        assert response.status_code == 200
        assert "url" in response.json()
        
        # Verify the content type was passed correctly
        call_args = mock_upload_gcs.call_args
        assert call_args[0][2] == content_type

