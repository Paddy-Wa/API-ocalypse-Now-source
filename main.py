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

# Load environment variables from the .env file.
load_dotenv()

# Retrieve database and security configurations from environment variables.
DATABASE_URL = os.getenv("DATABASE_URL")
SECRET_KEY = os.getenv("FASTAPI_SIMPLE_SECURITY_SECRET")
SECRET_KEY = os.getenv("SECRET_KEY")

# Initialize the FastAPI application with a title and description.
app = FastAPI(title="API-ocolypse Now API",
              description="API for managing jungle animals.")

# Set up Jinja2 templates for rendering HTML templates.
templates = Jinja2Templates(directory="templates")

# Include the API key security router for authentication endpoints.
app.include_router(api_key_router, prefix="/auth", tags=["auth"])


class Token(BaseModel):
    """
    Pydantic model for representing a JWT Token.
    
    Attributes:
        access_token (str): The JWT access token.
        token_type (str): Type of the token, usually "bearer".
    """
    access_token: str
    token_type: str


class TokenData(BaseModel):
    """
    Pydantic model for storing decoded JWT token data.
    
    Attributes:
        username (str): The username extracted from the token.
    """
    username: str | None = None


class User(BaseModel):
    """
    Pydantic model for representing a user.
    
    Attributes:
        username (str): The username of the user.
        full_name (str): The full name of the user.
        email (str): The email address of the user.
    """
    username: str
    full_name: str
    email: str


def get_db():
    """
    Dependency that provides a database session.
    Yields:
        db: SQLAlchemy session instance.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def preload_animals(db: Session):
    """
    Preloads the animals table with data if the database is empty.
    
    Args:
        db (Session): SQLAlchemy session.
        
    Returns:
        None
    """
    # Check if the animals table is empty.
    if db.query(AnimalDB).count() == 0:
        # Preload some example animals into the database.
        animals = [
            AnimalDB(name="Lion", species="Panthera leo", age=5),
            AnimalDB(name="Elephant", species="Loxodonta africana", age=25),
            AnimalDB(name="Giraffe", species="Giraffa camelopardalis", age=10)
        ]
        db.add_all(animals)
        db.commit()


@app.get("/")
def read_root(request: Request):
    """
    Root endpoint that returns a welcome message.
    
    Args:
        request (Request): FastAPI request object.
        
    Returns:
        HTMLResponse: A rendered HTML template with the welcome message.
    """
    return templates.TemplateResponse("index.html", {"request": request, "message": "Welcome to the API Jungle!"})


@app.post("/animals/")
def create_animal(name: str = Form(...), species: str = Form(...), age: int = Form(...), db: Session = Depends(get_db)):
    """
    Endpoint to create a new animal entry in the database.
    
    Args:
        name (str): Name of the animal.
        species (str): Species of the animal.
        age (int): Age of the animal.
        db (Session): SQLAlchemy session dependency.
        
    Returns:
        dict: Dictionary containing the details of the newly created animal.
    """
    animal = AnimalDB(name=name, species=species, age=age)
    db.add(animal)
    db.commit()
    db.refresh(animal)
    return {"name": animal.name, "species": animal.species, "age": animal.age}


@app.get("/animals/")
def read_animals(db: Session = Depends(get_db)):
    """
    Endpoint to retrieve all animals from the database.
    
    Args:
        db (Session): SQLAlchemy session dependency.
        
    Returns:
        list[dict]: List of dictionaries containing details of all animals.
    """
    animals = db.query(AnimalDB).all()
    return animals


@app.delete("/animals/{animal_id}")
def delete_animal(animal_id: int, db: Session = Depends(get_db)):
    """
    Endpoint to delete an animal by ID from the database.
    
    Args:
        animal_id (int): ID of the animal to be deleted.
        db (Session): SQLAlchemy session dependency.
        
    Raises:
        HTTPException: If the animal with the given ID is not found.
        
    Returns:
        dict: Confirmation message of successful deletion.
    """
    animal = db.query(AnimalDB).filter(AnimalDB.id == animal_id).first()
    if not animal:
        raise HTTPException(status_code=404, detail="Animal not found")
    db.delete(animal)
    db.commit()
    return {"detail": f"Animal {animal_id} deleted successfully"}


if __name__ == "__main__":
    """
    Entry point for running the FastAPI application with Uvicorn.
    """
    uvicorn.run(app, host="0.0.0.0", port=8000)
