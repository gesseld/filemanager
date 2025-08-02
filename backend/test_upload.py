#!/usr/bin/env python3
"""Test script for file upload endpoint."""

import requests
import os
from pathlib import Path

def test_upload_endpoint():
    """Test the file upload endpoint."""
    
    # Create a test file
    test_file_path = Path("test_upload.txt")
    test_content = "This is a test file for upload endpoint testing."
    
    with open(test_file_path, "w") as f:
        f.write(test_content)
    
    try:
        # Test upload endpoint
        url = "http://localhost:8000/api/v1/files/upload"
        
        with open(test_file_path, "rb") as f:
            files = {"file": ("test_upload.txt", f, "text/plain")}
            data = {"title": "Test Upload", "description": "Test file upload"}
            
            response = requests.post(url, files=files, data=data)
            
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        
        # Test upload info endpoint
        info_url = "http://localhost:8000/api/v1/files/upload"
        info_response = requests.get(info_url)
        print(f"Upload Info: {info_response.json()}")
        
    except Exception as e:
        print(f"Error testing upload: {e}")
    finally:
        # Clean up test file
        if test_file_path.exists():
            test_file_path.unlink()

if __name__ == "__main__":
    test_upload_endpoint()