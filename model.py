from pydantic import BaseModel, conint


class Animal(BaseModel):
    """
    Pydantic model representing an animal.
    
    Attributes:
        name (str): The name of the animal.
        species (str): The species of the animal.
        age (int): The age of the animal, constrained to be a non-negative integer.
    """
    name: str
    species: str
    age: conint(ge=0)  # Age must be a non-negative integer