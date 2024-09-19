from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Define the database URL. In this case, it's a local SQLite database named 'animals.db'.
DATABASE_URL = "sqlite:///./animals.db"

# Create a new SQLAlchemy engine that will interact with the SQLite database.
engine = create_engine(DATABASE_URL)

# SessionLocal is a factory for creating new sessions with the database.
# autocommit and autoflush are set to False to maintain control over transactions.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class that all ORM models will inherit from.
Base = declarative_base()


class AnimalDB(Base):
    """
    ORM model for the 'animals' table.
    
    Attributes:
        id (int): Primary key, unique ID for each animal.
        name (str): Name of the animal.
        species (str): Species of the animal.
        age (int): Age of the animal.
    """
    __tablename__ = "animals"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    species = Column(String, index=True)
    age = Column(Integer)


# Create all tables in the database. This will create the 'animals' table if it doesn't exist.
Base.metadata.create_all(bind=engine)