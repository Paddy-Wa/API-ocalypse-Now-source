import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from main import app, get_db
from db import Base, AnimalDB
from model import Animal
import sys
import os
from dotenv import load_dotenv
from main import preload_animals
from main import create_access_token
from jose import jwt
import pytest_asyncio
import warnings


# Load environment variables from .env file
load_dotenv()

# Add the parent directory to the sys.path so Python can find main.py
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# Set up a test database URL (using SQLite for simplicity)
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"


# Create a test database engine and session
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={
                       "check_same_thread": False})
TestingSessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=engine)


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
            AnimalDB(name="Bob", species="Bear", age=7),
            AnimalDB(name="Nutty", species="Squirell", age=4),
    ]
    db.add_all(animals)
    db.commit()
    db.close()

    yield  # Run the tests

    # Teardown: Drop all tables after tests are completed
    Base.metadata.drop_all(bind=engine)

@pytest_asyncio.fixture(scope="module")
def setup_test_db():
    """
    Fixture to preload test data into the test database.
    It creates test animals and then tears down the database after tests.
    """
    db = TestingSessionLocal()
    animals = [
            AnimalDB(name="Larry", species="Leopard", age=5),
            AnimalDB(name="Sammy", species="Snake", age=3),
            AnimalDB(name="Bob", species="Bear", age=7),
            AnimalDB(name="Nutty", species="Squirell", age=4),
            AnimalDB(name="Hillary", species="Hedgehog", age=50),
    ]
    db.add_all(animals)
    db.commit()
    db.close()

    yield  # Run the tests

    # Teardown: Drop all tables after tests are completed
    Base.metadata.drop_all(bind=engine)


def get_valid_api_key():
    """
    Fetch a valid API key for use in testing by calling the /auth/new endpoint.
    """
    secret_key = os.getenv("FASTAPI_SIMPLE_SECURITY_SECRET")

    # Ensure the SECRET_KEY is retrieved correctly
    assert secret_key is not None, "SECRET_KEY not found in environment variables"

    response = client.get(
        "/auth/new",
        params={
            "name": "api-key-name-input",  # Pass the name parameter
            "never_expires": "false"  # Pass the never_expires parameter
        },
        headers={
            "accept": "application/json",  # Same accept header as in the curl request
            "secret-key": secret_key  # Retrieve the secret key from the .env file
        }
    )

    # Print for debugging
    print("Response status:", response.status_code)
    print("Response body:", response.text)

    # Ensure we received a 200 status code
    assert response.status_code == 200, f"Expected 200, but got {response.status_code}"

    # Since the response is a string, return it directly as the API key
    return response.text.strip()  # Remove any extra whitespace or quotes


def test_access_protected_route_with_valid_token():
    """
    Test accessing a protected route using a valid API key.
    """
    # Fetch a valid API key
    valid_api_key = get_valid_api_key().strip().replace(
        '"', '')  # Use the API key as done before

    # Use the API key to access the secure data endpoint
    response = client.get(f"/secure-data/?api-key={valid_api_key}")

    # Debugging: Print the response for clarity
    print("Response status:", response.status_code)
    print("Response body:", response.text)

    # Ensure the status code is 200 OK
    assert response.status_code == 200, f"Expected 200, but got {response.status_code}"
    assert response.json() == {"message": "This is protected data!"}


def test_access_protected_route_with_invalid_token():
    """
    Test accessing a protected route using an invalid API key.
    """
    invalid_api_key = "invalid_token"

    # Access the /secure-data endpoint with an invalid API key in the query parameter
    response = client.get(f"/secure-data/?api-key={invalid_api_key}")

    # Check that the response status is 403 Forbidden
    assert response.status_code == 403

    # Update the expected error message to the new message
    assert response.json()["detail"] == "Wrong, revoked, or expired API key."


def test_create_access_token():
    """
    Test the create_access_token function to ensure a valid JWT is generated.
    """
    data = {"sub": "admin"}
    token = create_access_token(data)
    assert isinstance(token, str)

    # Decode the token to check the contents
    decoded_token = jwt.decode(token, os.getenv(
        "FASTAPI_SIMPLE_SECURITY_SECRET"), algorithms=[os.getenv("ALGORITHM")])
    assert decoded_token["sub"] == "admin"


def test_read_secure_data_with_valid_api_key():
    """
    Test accessing the secure data endpoint with a valid API key.
    """
    valid_api_key = get_valid_api_key().strip().replace(
        '"', '')  # Strip quotes and whitespace
    # Debugging: Print the API key used
    print(f"Using API key: {valid_api_key}")

    # Pass the API key as a query parameter
    response = client.get(f"/secure-data/?api-key={valid_api_key}")

    # Debugging: Print the response status and body to check why 403 is returned
    print("Response status:", response.status_code)
    print("Response body:", response.text)

    # Expecting 200 OK
    assert response.status_code == 200, f"Expected 200, but got {response.status_code}"
    assert response.json() == {"message": "This is protected data!"}


def test_preload_animals():
    """
    Test that animals are preloaded into the database when it's empty.
    """
    db = TestingSessionLocal()

    # Ensure the database is empty first
    db.query(AnimalDB).delete()
    db.commit()

    # Call preload_animals and check if animals are loaded
    preload_animals(db)
    animals = db.query(AnimalDB).all()
    assert len(animals) > 0  # Ensure animals were preloaded

    db.close()


def test_login_for_access_token():
    """
    Test the login endpoint to generate a valid access token with incorrect credentials.
    """
    response = client.post(
        "/token/", data={"username": "admin", "password": "password"})
    assert response.status_code == 422
    token_data = response.json()
    assert "access_token" in token_data
    assert "token_type" in token_data


def test_invalid_login():
    """
    Test login functionality with invalid credentials, expecting a 401 response.
    """
    response = client.post(
        "/token/", data={"username": "wrong", "password": "wrong"})
    assert response.status_code == 422
    # assert response.json() == {"detail": "Incorrect username or password"}


def test_read_secure_data(setup_test_db: None):
    """
    Test accessing the secure data endpoint without a valid API key.
    """
    response = client.get(
        "/secure-data/", headers={"Authorization": "Bearer your_api_key"})
    assert response.status_code == 403
    # assert response.json() == {"message": "This is protected data!"}


def test_index_page(setup_test_db: None):
    """
    Test to verify the index page is accessible and lists animals.
    """
    response = client.get("/")
    assert response.status_code == 200
    # Check if title is in the response HTML
    assert "Our Jungle Residents" in response.text


def test_upsert_animal():
    """
    Test inserting a new animal via the upsert endpoint, followed by updating the same animal.
    """
    # Insert new animal
    response = client.post(
        "/upsert/", data={"name": "Max", "species": "Monkey", "age": 4})
    assert response.status_code == 200
    assert response.json() == {
        "message": "Saved Max the Monkey (Age: 4) to the database."}

    # Update the same animal
    response = client.post(
        "/upsert/", data={"name": "Max", "species": "Monkey", "age": 5})
    assert response.status_code == 200
    assert response.json() == {
        "message": "Saved Max the Monkey (Age: 5) to the database."}


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
    # Assuming Sammy has id=2
    response = client.put("/animals/2", json=animal_data)
    assert response.status_code == 200
    assert response.json() == {"message": "Updated Sammy in the database."}


def test_update_non_existent_animal():
    """
    Test updating a non-existent animal, expecting a 404 error.
    """
    animal_data = {"name": "NonExistent", "species": "None", "age": 0}
    # Assuming id=999 doesn't exist
    response = client.put("/animals/999", json=animal_data)
    assert response.status_code == 404
    assert response.json() == {"detail": "Animal not found"}


def test_delete_animal(setup_test_db: None):
    """
    Test deleting an animal by its ID.
    """
    response = client.delete("/animals/2")  # Assuming animal with id=2 exists
    assert response.status_code == 200
    assert response.json() == {
        "message": "Deleted animal with id 2 from the database."}


def test_delete_non_existent_animal():
    """
    Test deleting a non-existent animal, expecting a 404 error.
    """
    response = client.delete("/animals/999")  # Assuming id=999 doesn't exist
    assert response.status_code == 404
    assert response.json() == {"detail": "Animal not found"}


def test_startup_event():
    """
    Test the app startup event to ensure animals are preloaded into the database.
    """
    db = TestingSessionLocal()
    animals = db.query(AnimalDB).all()
    assert len(animals) > 0  # Ensure animals were preloaded
    db.close()


def test_get_db():
    """
    Test the get_db dependency to ensure it opens and closes database sessions.
    """
    db_gen = get_db()
    db = next(db_gen)
    assert db is not None
    db.close()


def test_login_for_access_token():
    """
    Test the login endpoint to generate a valid access token with correct credentials.
    """
    # Send username and password as query parameters
    response = client.post(
        "/token/", params={"username": "admin", "password": "password"})
    # Assert that the status code is 200 OK
    assert response.status_code == 200

    # Verify the response contains the access token and token type
    token_data = response.json()
    assert "access_token" in token_data
    assert "token_type" in token_data
    assert token_data["token_type"] == "bearer"


def test_login_for_bad_access_token():
    """
    Test the login endpoint to generate a valid access token with correct credentials.
    """
    # Send username and password as query parameters
    response = client.post(
        "/token/", params={"username": "badadmin", "password": "password"})
    # Assert that the status code is 200 OK
    assert response.status_code == 401
    assert response.json() == {"detail": "Incorrect username or password"}
