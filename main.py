import os
import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
import logging

# 🚀 1. SETUP LOGGING (Production Debugging ke liye zaroori)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 🚀 2. LOAD ENVIRONMENT VARIABLES
load_dotenv(override=True)

# 🗄️ 3. DATABASE SETUP
from core.database import engine
from core import models

# 🚀 4. IMPORT MODULAR ROUTERS
from routers import auth, ai

try:
    models.Base.metadata.create_all(bind=engine)
    logger.info("Database tables verified/created successfully.")
except Exception as e:
    logger.error(f"Error creating database tables: {e}")

# 🚀 5. INITIALIZE FASTAPI APP
app = FastAPI(
    title="DocuMind API",
    version="3.0 Modular RAG Architecture",
    description="Backend API for DocuMind - An AI-powered educational document learning platform.",
)

# 🚀 6. CORS SETUP (Security First)
# TODO: Jab Frontend live ho jaye (eg. Vercel par), toh "*" ko hata kar apna live URL daal dena.
origins = [
    "https://documind-frontend.vercel.app",  # Tumhara live frontend
    "http://localhost:5173",  # Local testing ke liye (Vite default)
    "http://localhost:3000",  # Local testing ke liye (React default)
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 🚀 7. GLOBAL EXCEPTION HANDLER (Frontend ko white screen se bachane ke liye)
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled Exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "message": "An internal server error occurred.",
            "details": str(exc),
        },
    )


# ==========================================
# 🔌 8. PLUG IN THE ROUTERS
# ==========================================
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(ai.router, prefix="/api/ai", tags=["AI Engine"])


# ==========================================
# 🌍 9. HEALTH CHECK ENDPOINT
# ==========================================
@app.get("/", tags=["Health"])
async def health_check():
    return {
        "status": "success",
        "message": "DocuMind Backend is Live and Running! 🚀",
        "environment": os.getenv("ENVIRONMENT", "development"),
    }


# ==========================================
# ⚙️ 10. RUNNER COMMAND (For local testing & Render.com compatibility)
# ==========================================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    # Render.com hamesha apna port dynamically deta hai "PORT" env variable ke through
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
