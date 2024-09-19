from pydantic import BaseModel, conint

class Animal(BaseModel):
 name: str
 species: str
 age: conint(ge=0) # Age must be a non-negative integer