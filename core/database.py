import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

# 🚀 Force load environment variables
load_dotenv(override=True)

SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")

if not SQLALCHEMY_DATABASE_URL:
    raise ValueError("⚠️ DATABASE_URL is missing in .env file! Please check your .env")

# Create Database Engine
engine = create_engine(SQLALCHEMY_DATABASE_URL)

# Create Database Session
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create Base Class for Models
Base = declarative_base()


# Dependency: API endpoints iska use karke database se securely baat karenge
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
