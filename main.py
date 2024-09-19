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

load_dotenv()


DATABASE_URL = os.getenv("DATABASE_URL")
SECRET_KEY = os.getenv("FASTAPI_SIMPLE_SECURITY_SECRET")
SECRET_KEY = os.getenv("SECRET_KEY")

app = FastAPI(title="My Awesome API", description="API for managing jungle animals.")

templates = Jinja2Templates(directory="templates")
app.include_router(api_key_router, prefix="/auth", tags=["auth"])

def get_db():
 db = SessionLocal()
 try:
    yield db
 finally:
    db.close()

def preload_animals(db: Session):
    # Check if the database is empty
    if not db.query(AnimalDB).first():
        # Preload some animals
        animals = [
            AnimalDB(name="Larry", species="Leopard", age=5),
            AnimalDB(name="Sammy", species="Snake", age=3),
            AnimalDB(name="Bella", species="Bear", age=7)
        ]
        db.add_all(animals)
        db.commit()

SECRET_KEY = "justletmein" # Use environment variables in production
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30 # Tokens expire after 30 minutes

class Token(BaseModel):
   access_token: str
   token_type: str

@app.post("/token/", response_model=Token)
def login_for_access_token(username: str, password: str):
   if username != "admin" or password != "password":
      raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail="Incorrect username or password")
   access_token = create_access_token(data={"sub": username})
   return {"access_token": access_token, "token_type": "bearer"}

def create_access_token(data: dict):
 to_encode = data.copy()
 expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
 to_encode.update({"exp": expire})
 encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
 return encoded_jwt

@app.get("/secure-data/", dependencies=[Depends(api_key_security)])
def read_secure_data():
   return {"message": "This is protected data!"}

@app.get("/")
def index(request: Request, db: Session = Depends(get_db)):
 animals = db.query(AnimalDB).all()
 return templates.TemplateResponse("index.html", {"request": request, "title":
"Our Jungle Residents", "animals": animals})

@app.post("/upsert/")
def upsert_animal(name: str = Form(...), species: str = Form(...), age: int =
Form(...), db: Session = Depends(get_db)):
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
 return {"message": f"Saved {animal.name} the {animal.species} (Age: {animal.age}) to the database."}

@app.put("/animals/{animal_id}")
def update_animal(animal_id: int, animal: Animal, db: Session = Depends(get_db)):
   animal_db = db.query(AnimalDB).filter(AnimalDB.id == animal_id).first()
   if not animal_db:
      raise HTTPException(status_code=404, detail="Animal not found")
   
   animal_db.name = animal.name
   animal_db.species = animal.species
   animal_db.age = animal.age
   db.commit()
   return {"message": f"Updated {animal.name} in the database."}

@app.post("/animals/")
def create_animal(animal: Animal, db: Session = Depends(get_db)):
 animal_db = AnimalDB(name=animal.name, species=animal.species, age=animal.age)
 db.add(animal_db)
 db.commit()
 db.refresh(animal_db)
 return {"message": f"Added {animal.name} the {animal.species} to the database.", "id": animal_db.id}

@app.delete("/animals/{animal_id}")
def delete_animal(animal_id: int, db: Session = Depends(get_db)):
 animal_db = db.query(AnimalDB).filter(AnimalDB.id == animal_id).first()
 if not animal_db:
   raise HTTPException(status_code=404, detail="Animal not found")
 
 db.delete(animal_db)
 db.commit()
 return {"message": f"Deleted animal with id {animal_id} from the database."}

if __name__ == "__main__":
    db = next(get_db())
    preload_animals(db)
    uvicorn.run("main:app", port=8080, reload=True)
