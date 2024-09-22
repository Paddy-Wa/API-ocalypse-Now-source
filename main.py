from dotenv import load_dotenv
from sqlalchemy.orm import Session
from fastapi import FastAPI, Depends, Request, Form, HTTPException, status
from db import SessionLocal, AnimalDB
from fastapi.templating import Jinja2Templates
from fastapi_simple_security import api_key_router, api_key_security
from datetime import datetime, timedelta
from jose import JWTError, jwt
from pydantic import BaseModel
import uvicorn
import os
from model import Animal

# Load environment variables from a .env file
load_dotenv()

# Retrieve environment variables
DATABASE_URL = os.getenv("DATABASE_URL")
SECRET_KEY = os.getenv("FASTAPI_SIMPLE_SECURITY_SECRET")
FASTAPI_SIMPLE_SECURITY_SECRET = os.getenv("FASTAPI_SIMPLE_SECURITY_SECRET")
ACCESS_TOKEN_EXPIRE_MINUTES = os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES")
ALGORITHM = os.getenv("ALGORITHM")

# Initialize FastAPI app
app = FastAPI(title="API-ocalypse API",
              description="API for managing jungle animals.")

# Set up Jinja2 templates
templates = Jinja2Templates(directory="templates")

# Include API key router for authentication
app.include_router(api_key_router, prefix="/auth", tags=["auth"])


def get_db():
    """
    Dependency to get a database session.

    Yields:
        db (Session): SQLAlchemy database session.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def preload_animals(db: Session):
    """
    Preload some animals into the database if it's empty.

    Args:
        db (Session): SQLAlchemy database session.
    """
    if not db.query(AnimalDB).first():
        animals = [
            AnimalDB(name="Larry", species="Leopard", age=5),
            AnimalDB(name="Sammy", species="Snake", age=3),
            AnimalDB(name="Bob", species="Bear", age=7),
            AnimalDB(name="Nutty", species="Squirell", age=4),
        ]
        db.add_all(animals)
        db.commit()


class Token(BaseModel):
    """
    Model for the token response.

    Attributes:
        access_token (str): The access token.
        token_type (str): The type of the token.
    """

    access_token: str
    token_type: str


@app.on_event("startup")
def startup_event():
    """
    Function that runs on app startup. Ensures the database is preloaded with animals if empty.
    """
    db = next(get_db())  # Get a database session # pragma: no cover
    preload_animals(db)  # pragma: no cover


@app.post("/token/", response_model=Token)
async def login_for_access_token(username: str, password: str):
    """
    Endpoint to generate an access token.

    Args:
        username (str): The username.
        password (str): The password.

    Returns:
        dict: A dictionary containing the access token and token type.
    """
    if username != "admin" or password != "password":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
    access_token = create_access_token(data={"sub": username})
    return {"access_token": access_token, "token_type": "bearer"}


def create_access_token(data: dict):
    """
    Create a JWT access token.

    Args:
        data (dict): The data to encode in the token.

    Returns:
        str: The encoded JWT token.
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(
        minutes=int(ACCESS_TOKEN_EXPIRE_MINUTES)
    )  # Ensure UTC and proper int casting
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


@app.get("/")
async def index(request: Request, db: Session = Depends(get_db)):
    """
    Render the index page with a list of animals.

    Args:
        request (Request): The request object.
        db (Session): SQLAlchemy database session.

    Returns:
        TemplateResponse: The rendered template response.
    """
    animals = db.query(AnimalDB).all()
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "title": "Our Jungle Residents", "animals": animals},
    )


@app.get("/secure-data/", dependencies=[Depends(api_key_security)])
async def read_secure_data():
    """
    Endpoint to read secure data.

    Returns:
        dict: A dictionary containing a message.
    """
    return {"message": "This is protected data!"}


@app.post("/upsert/")
async def upsert_animal(
    name: str = Form(...),
    species: str = Form(...),
    age: int = Form(...),
    db: Session = Depends(get_db),
):
    """
    Endpoint to insert or update an animal.

    Args:
        name (str): The name of the animal.
        species (str): The species of the animal.
        age (int): The age of the animal.
        db (Session): SQLAlchemy database session.

    Returns:
        dict: A dictionary containing a message.
    """
    animal = db.query(AnimalDB).filter_by(name=name).first()
    if animal:
        # Update existing animal
        animal.species = species
        animal.age = age
    else:
        # Insert new animal
        animal = AnimalDB(name=name, species=species, age=age)
        db.add(animal)
    db.commit()
    return {
        "message": f"Saved {animal.name} the {animal.species} (Age: {animal.age}) to the database."
    }


@app.post("/animals/")
async def create_animal(animal: Animal, db: Session = Depends(get_db)):
    """
    Endpoint to create a new animal.

    Args:
        animal (Animal): The animal data.
        db (Session): SQLAlchemy database session.

    Returns:
        dict: A dictionary containing a message and the animal ID.
    """
    animal_db = AnimalDB(
        name=animal.name, species=animal.species, age=animal.age)
    db.add(animal_db)
    db.commit()
    db.refresh(animal_db)
    return {
        "message": f"Added {animal.name} the {animal.species} to the database.",
        "id": animal_db.id,
    }


@app.put("/animals/{animal_id}")
async def update_animal(animal_id: int, animal: Animal, db: Session = Depends(get_db)):
    """
    Endpoint to update an existing animal.

    Args:
        animal_id (int): The ID of the animal.
        animal (Animal): The updated animal data.
        db (Session): SQLAlchemy database session.

    Returns:
        dict: A dictionary containing a message.
    """
    animal_db = db.query(AnimalDB).filter(AnimalDB.id == animal_id).first()
    if not animal_db:
        raise HTTPException(status_code=404, detail="Animal not found")
    animal_db.name = animal.name
    animal_db.species = animal.species
    animal_db.age = animal.age
    db.commit()
    return {"message": f"Updated {animal.name} in the database."}


@app.delete("/animals/{animal_id}")
async def delete_animal(animal_id: int, db: Session = Depends(get_db)):
    """
    Endpoint to delete an animal.

    Args:
        animal_id (int): The ID of the animal.
        db (Session): SQLAlchemy database session.

    Returns:
        dict: A dictionary containing a message.
    """
    animal_db = db.query(AnimalDB).filter(AnimalDB.id == animal_id).first()
    if not animal_db:
        raise HTTPException(status_code=404, detail="Animal not found")
    db.delete(animal_db)
    db.commit()
    return {"message": f"Deleted animal with id {animal_id} from the database."}


if __name__ == "__main__":
    uvicorn.run("main:app", port=8080, reload=True) # pragma: no cover
