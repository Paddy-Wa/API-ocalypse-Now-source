import sys
import os
from fastapi.testclient import TestClient

# Add the parent directory to the sys.path so Python can find main.py
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app  # Import the FastAPI app

# Create a test client instance for interacting with the FastAPI app.
client = TestClient(app)


def test_index():
    """
    Test the root endpoint of the API.
    
    Verifies:
        - The status code should be 200 (OK).
        - The response content should contain the welcome message.
    """
    response = client.get("/")
    assert response.status_code == 200
    assert b"Welcome to the API Jungle!" in response.content