from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from core.database import Base


# 🚀 1. TRAINER TABLE
class Trainer(Base):
    __tablename__ = "trainers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    email = Column(String, unique=True, index=True)
    department = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationship: Ek Trainer ke paas multiple batches ho sakte hain
    batches = relationship("Batch", back_populates="trainer")


# 🚀 2. BATCH / CLASSROOM TABLE
class Batch(Base):
    __tablename__ = "batches"

    id = Column(Integer, primary_key=True, index=True)
    batch_name = Column(String, index=True)  # e.g., "BCA 1st Year - C Programming"
    course_name = Column(String)  # e.g., "BCA"

    # ForeignKey: Yeh batch kis trainer ka hai?
    trainer_id = Column(Integer, ForeignKey("trainers.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationship: Reverse link back to Trainer
    trainer = relationship("Trainer", back_populates="batches")
