import sys
import os
from fastapi.testclient import TestClient

# Add the parent directory to the sys.path so Python can find main.py
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app  # Now this should work

client = TestClient(app)

def test_index():
    response = client.get("/")
    assert response.status_code == 200
    assert b"Welcome to the API Jungle!" in response.content
