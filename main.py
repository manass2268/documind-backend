from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# 🚀 FORCE RELOAD ENV VARIABLES
load_dotenv(override=True)

# 🗄️ DATABASE SETUP
from core.database import engine
from core import models

# 🚀 IMPORT MODULAR ROUTERS
from routers import auth, ai

# Autocreate Tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="DocuMind API", version="3.0 Modular RAG Architecture")

# CORS Setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# 🔌 PLUG IN THE ROUTERS
# ==========================================
app.include_router(auth.router)
app.include_router(ai.router)


# Health Check
@app.get("/")
def health_check():
    return {"status": "success", "message": "DocuMind Minimal Backend is Running! 🚀"}
