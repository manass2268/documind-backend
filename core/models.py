from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func
from core.database import Base


# ==========================================
# 🚀 1. CENTRAL USERS TABLE (Students & Trainers)
# ==========================================
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)

    # Firebase UID: Yeh Firebase aur Postgres ko link karega
    firebase_uid = Column(String, unique=True, index=True, nullable=True)

    email = Column(String, unique=True, index=True)
    name = Column(String)

    # Role decide karega ki yeh 'learner' hai ya 'trainer'
    role = Column(String, default="learner")

    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# ==========================================
# 🚀 2. BATCH / CLASSROOM TABLE (Trainer ki Classes)
# ==========================================
class Batch(Base):
    __tablename__ = "batches"

    id = Column(Integer, primary_key=True, index=True)
    batch_name = Column(String, index=True)  # e.g., "BCA 1st Year - C Programming"

    # Yeh batch kis trainer/user ka hai
    trainer_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
