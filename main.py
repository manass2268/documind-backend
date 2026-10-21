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

# Import logic from custom services
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

app = FastAPI(title="DocuMind API", version="3.0 RAG & Firebase-Postgres Sync")

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
generated_otps = {}


# ==========================================
# 📝 PYDANTIC MODELS
# ==========================================
class ChatRequest(BaseModel):
    query: str
    document_id: Optional[str] = None
    role: str = "learner"


class EmailRequest(BaseModel):
    email: str


class VerifyRequest(BaseModel):
    email: str
    otp: str


# 🚀 NEW: Model for Firebase to Postgres Sync
class AuthSyncRequest(BaseModel):
    firebase_uid: str
    email: str
    name: str
    role: str = "learner"  # Default fallback


@app.get("/")
def health_check():
    return {"status": "DocuMind Backend Server is Running!"}


# ==========================================
# 🔐 ENDPOINT 1: SYNC FIREBASE AUTH WITH POSTGRES
# ==========================================
@app.post("/api/auth/sync")
def sync_user_with_postgres(req: AuthSyncRequest, db: Session = Depends(get_db)):
    # 1. Check if user already exists via email
    user = db.query(models.User).filter(models.User.email == req.email).first()

    if not user:
        # 2. If new user, create record in PostgreSQL
        new_user = models.User(
            firebase_uid=req.firebase_uid,
            email=req.email,
            name=req.name,
            role=req.role,  # By default this will be 'learner'
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        user = new_user
    else:
        # 3. If old user but missing firebase_uid (First time login via Firebase)
        if not user.firebase_uid:
            user.firebase_uid = req.firebase_uid
            db.commit()
            db.refresh(user)

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is deactivated.")

    # 4. Return complete PostgreSQL User Data (This tells frontend what dashboard to show)
    return {
        "status": "success",
        "message": "User synchronized successfully",
        "data": {
            "id": user.id,
            "firebase_uid": user.firebase_uid,
            "name": user.name,
            "email": user.email,
            "role": user.role,
        },
    }


# ==========================================
# 🚀 ENDPOINT 2: Chat Stream
# ==========================================
@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    return StreamingResponse(
        stream_chat_response(request.query, request.document_id, request.role),
        media_type="text/event-stream",
    )


# ==========================================
# 🚀 ENDPOINT 3: Image Processing
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
# 🚀 ENDPOINT 4: PDF Upload (5MB Limit + RAG)
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
# 🚀 ENDPOINT 5: SEND REAL OTP EMAIL
# ==========================================
@app.post("/api/send-otp")
async def send_otp_endpoint(req: EmailRequest, background_tasks: BackgroundTasks):
    otp_code = str(random.randint(100000, 999999))
    generated_otps[req.email] = otp_code
    print(f"OTP generated for {req.email}: {otp_code}")
    background_tasks.add_task(send_real_otp_email, req.email, otp_code)
    return {"status": "success", "message": "OTP sent successfully in the background!"}


# ==========================================
# 🚀 ENDPOINT 6: VERIFY THE OTP
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
