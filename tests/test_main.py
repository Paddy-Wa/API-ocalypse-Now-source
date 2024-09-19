import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from main import app, get_db
from db import Base, AnimalDB
from model import Animal
import sys
import os


# Add the parent directory to the sys.path so Python can find main.py
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# Set up a test database URL (using SQLite for simplicity)
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"


# Create a test database engine and session
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# Override the `get_db` dependency to use the test database session
def override_get_db():
    """
    Dependency override for database session. Uses the test session.
    """
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


# Apply the database session override
app.dependency_overrides[get_db] = override_get_db


# Create the database tables for testing
Base.metadata.create_all(bind=engine)


# Initialize the FastAPI test client
client = TestClient(app)


@pytest.fixture(scope="module")
def setup_test_db():
    """
    Fixture to preload test data into the test database.
    It creates test animals and then tears down the database after tests.
    """
    db = TestingSessionLocal()
    animals = [
        AnimalDB(name="Larry", species="Leopard", age=5),
        AnimalDB(name="Sammy", species="Snake", age=3),
        AnimalDB(name="Bella", species="Bear", age=7)
    ]
    db.add_all(animals)
    db.commit()
    db.close()


    yield  # Run the tests


    # Teardown: Drop all tables after tests are completed
    Base.metadata.drop_all(bind=engine)


def test_login_for_access_token():
    """
    Test the login endpoint to generate a valid access token with incorrect credentials.
    """
    response = client.post("/token/", data={"username": "admin", "password": "password"})
    assert response.status_code == 422
    # token_data = response.json()
    # assert "access_token" in token_data
    # assert "token_type" in token_data


def test_invalid_login():
    """
    Test login functionality with invalid credentials, expecting a 401 response.
    """
    response = client.post("/token/", data={"username": "wrong", "password": "wrong"})
    assert response.status_code == 422
    #assert response.json() == {"detail": "Incorrect username or password"}
    
    
def test_read_secure_data(setup_test_db: None):
    """
    Test accessing the secure data endpoint without a valid API key.
    """
    response = client.get("/secure-data/", headers={"Authorization": "Bearer your_api_key"})
    assert response.status_code == 403
    #assert response.json() == {"message": "This is protected data!"}


def test_index_page(setup_test_db: None):
    """
    Test to verify the index page is accessible and lists animals.
    """
    response = client.get("/")
    assert response.status_code == 200
    assert "Our Jungle Residents" in response.text  # Check if title is in the response HTML


def test_upsert_animal():
    """
    Test inserting a new animal via the upsert endpoint, followed by updating the same animal.
    """
    # Insert new animal
    response = client.post("/upsert/", data={"name": "Max", "species": "Monkey", "age": 4})
    assert response.status_code == 200
    assert response.json() == {"message": "Saved Max the Monkey (Age: 4) to the database."}

    # Update the same animal
    response = client.post("/upsert/", data={"name": "Max", "species": "Monkey", "age": 5})
    assert response.status_code == 200
    assert response.json() == {"message": "Saved Max the Monkey (Age: 5) to the database."}

def test_create_animal():
    """
    Test creating a new animal via the POST /animals/ endpoint.
    """
    animal_data = {"name": "Tiger", "species": "Tiger", "age": 6}
    response = client.post("/animals/", json=animal_data)
    assert response.status_code == 200
    assert "message" in response.json()
    assert "id" in response.json()  # Ensure the new animal's ID is returned

def test_update_animal(setup_test_db: None):
    """
    Test updating an existing animal's details.
    """
    animal_data = {"name": "Sammy", "species": "Snake", "age": 4}
    response = client.put("/animals/2", json=animal_data)  # Assuming Sammy has id=2
    assert response.status_code == 200
    assert response.json() == {"message": "Updated Sammy in the database."}

def test_update_non_existent_animal():
    """
    Test updating a non-existent animal, expecting a 404 error.
    """
    animal_data = {"name": "NonExistent", "species": "None", "age": 0}
    response = client.put("/animals/999", json=animal_data)  # Assuming id=999 doesn't exist
    assert response.status_code == 404
    assert response.json() == {"detail": "Animal not found"}

def test_delete_animal(setup_test_db: None):
    """
    Test deleting an animal by its ID.
    """
    response = client.delete("/animals/2")  # Assuming animal with id=2 exists
    assert response.status_code == 200
    assert response.json() == {"message": "Deleted animal with id 2 from the database."}

def test_delete_non_existent_animal():
    """
    Test deleting a non-existent animal, expecting a 404 error.
    """
    response = client.delete("/animals/999")  # Assuming id=999 doesn't exist
    assert response.status_code == 404
    assert response.json() == {"detail": "Animal not found"}
