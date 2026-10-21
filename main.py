from fastapi import (
    FastAPI,
    UploadFile,
    File,
    Form,
    HTTPException,
    BackgroundTasks,
    Depends,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from dotenv import load_dotenv
import uuid
import random
from typing import Optional

# 🚀 FORCE RELOAD ENV VARIABLES
load_dotenv(override=True)

# Import logic from ai_service.py
from services.ai_service import (
    stream_chat_response,
    extract_text_from_image,
    process_and_store_pdf,
)
from services.email_service import send_real_otp_email

# ==========================================
# 🗄️ DATABASE IMPORTS & SETUP 🗄️
# ==========================================
from core.database import engine, Base, get_db
from core import models

# 🚀 THIS LINE AUTOCREATES TABLES IN POSTGRESQL ON STARTUP
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="DocuMind API", version="2.5 RAG & Postgres")

# CORS Setup for React integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# 🚀 TEMPORARY OTP STORAGE 🚀
# ==========================================
# Format: {"student1@college.edu": "123456"}
generated_otps = {}


# --- Pydantic Models ---
class ChatRequest(BaseModel):
    query: str
    document_id: Optional[str] = None
    role: str = "learner"  # 🚀 Default is learner, can be 'admin' or 'trainer'


# Models OTP requests ke liye
class EmailRequest(BaseModel):
    email: str


class VerifyRequest(BaseModel):
    email: str
    otp: str


# Model Trainer Testing ke liye
class TrainerCreate(BaseModel):
    name: str
    email: str
    department: str


# Model Trainer Login ke liye
class TrainerLoginRequest(BaseModel):
    email: str


@app.get("/")
def health_check():
    return {"status": "DocuMind Backend Server is Running!"}


# ==========================================
# 🗄️ ENDPOINT: TEST POSTGRESQL TRAINER
# ==========================================
@app.post("/api/test-trainer")
def create_test_trainer(trainer: TrainerCreate, db: Session = Depends(get_db)):
    # Check if trainer already exists
    existing_trainer = (
        db.query(models.Trainer).filter(models.Trainer.email == trainer.email).first()
    )
    if existing_trainer:
        raise HTTPException(
            status_code=400, detail="Trainer with this email already exists"
        )

    # Create new trainer object
    new_trainer = models.Trainer(
        name=trainer.name, email=trainer.email, department=trainer.department
    )

    # Save to PostgreSQL
    db.add(new_trainer)
    db.commit()
    db.refresh(new_trainer)

    return {
        "status": "success",
        "message": "Trainer added to Postgres!",
        "data": new_trainer,
    }


# ==========================================
# 🔐 ENDPOINT: TRAINER LOGIN (PostgreSQL Check)
# ==========================================
@app.post("/api/trainer/login")
def trainer_login(req: TrainerLoginRequest, db: Session = Depends(get_db)):
    # 1. Check if email exists in PostgreSQL 'trainers' table
    trainer = db.query(models.Trainer).filter(models.Trainer.email == req.email).first()

    if not trainer:
        # Agar email DB mein nahi hai, toh access deny kar do
        raise HTTPException(
            status_code=404, detail="Trainer account not found. Access Denied."
        )

    if not trainer.is_active:
        # Agar account deactivate kar diya gaya hai
        raise HTTPException(
            status_code=403,
            detail="Your trainer account has been deactivated. Contact Admin.",
        )

    # 2. Return Success with Trainer Data
    return {
        "status": "success",
        "message": "Welcome back, Trainer!",
        "role": "trainer",
        "data": {
            "id": trainer.id,
            "name": trainer.name,
            "email": trainer.email,
            "department": trainer.department,
        },
    }


# ==========================================
# 🚀 ENDPOINT 1: Chat Stream
# ==========================================
@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    return StreamingResponse(
        stream_chat_response(request.query, request.document_id, request.role),
        media_type="text/event-stream",
    )


# ==========================================
# 🚀 ENDPOINT 2: Image Processing
# ==========================================
@app.post("/api/process-image")
async def process_image_endpoint(
    image: UploadFile = File(...),
    role: str = Form("learner"),
):
    if not image.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File provided is not an image.")
    image_bytes = await image.read()
    extracted_text = await extract_text_from_image(image_bytes, role)
    return {"extracted_text": extracted_text}


# ==========================================
# 🚀 ENDPOINT 3: PDF Upload (5MB Limit + RAG)
# ==========================================
@app.post("/api/upload-pdf")
async def upload_pdf_endpoint(
    file: UploadFile = File(...),
    role: str = Form("learner"),
):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed!")

    file_bytes = await file.read()

    MAX_SIZE = 5 * 1024 * 1024
    if len(file_bytes) > MAX_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File is too large! Max allowed is 5MB. Your file is {len(file_bytes) / (1024*1024):.2f}MB.",
        )

    document_id = str(uuid.uuid4())
    success, message = await process_and_store_pdf(file_bytes, document_id, role)

    if not success:
        raise HTTPException(status_code=400, detail=message)

    return {
        "status": "success",
        "filename": file.filename,
        "document_id": document_id,
        "message": message,
    }


# ==========================================
# 🚀 ENDPOINT 4: SEND REAL OTP EMAIL
# ==========================================
@app.post("/api/send-otp")
async def send_otp_endpoint(req: EmailRequest, background_tasks: BackgroundTasks):
    otp_code = str(random.randint(100000, 999999))
    generated_otps[req.email] = otp_code
    print(f"OTP generated for {req.email}: {otp_code}")
    background_tasks.add_task(send_real_otp_email, req.email, otp_code)
    return {"status": "success", "message": "OTP sent successfully in the background!"}


# ==========================================
# 🚀 ENDPOINT 5: VERIFY THE OTP
# ==========================================
@app.post("/api/verify-otp")
async def verify_otp_endpoint(req: VerifyRequest):
    if req.email not in generated_otps:
        raise HTTPException(
            status_code=400,
            detail="No OTP found for this email. Please request a new one.",
        )

    stored_otp = generated_otps[req.email]

    if req.otp == stored_otp:
        del generated_otps[req.email]
        return {"status": "success", "message": "OTP Verified Successfully!"}
    else:
        raise HTTPException(status_code=400, detail="Invalid Verification Code.")
