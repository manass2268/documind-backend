from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
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

app = FastAPI(title="DocuMind API", version="2.5 RAG")

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


@app.get("/")
def health_check():
    return {"status": "DocuMind Backend Server is Running!"}


# ==========================================
# 🚀 ENDPOINT 1: Chat Stream
# ==========================================
@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    # 'text/event-stream' ensures the response is not buffered and streams instantly
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
    role: str = Form("learner"),  # 🚀 Accept role from frontend form-data
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
    role: str = Form("learner"),  # 🚀 Accept role from frontend form-data
):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed!")

    file_bytes = await file.read()

    # Check 5MB Limit
    MAX_SIZE = 5 * 1024 * 1024
    if len(file_bytes) > MAX_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File is too large! Max allowed is 5MB. Your file is {len(file_bytes) / (1024*1024):.2f}MB.",
        )

    # Generate unique ID for Vector DB storage
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
    # 1. Generate random 6 digit OTP
    otp_code = str(random.randint(100000, 999999))

    # 2. Store it temporarily in dictionary
    generated_otps[req.email] = otp_code
    print(f"OTP generated for {req.email}: {otp_code}")  # Backend terminal me dikhega

    # 3. 🚀 SEND EMAIL IN BACKGROUND 🚀
    background_tasks.add_task(send_real_otp_email, req.email, otp_code)

    # 4. Return success response IMMEDIATELY
    return {"status": "success", "message": "OTP sent successfully in the background!"}


# ==========================================
# 🚀 ENDPOINT 5: VERIFY THE OTP
# ==========================================
@app.post("/api/verify-otp")
async def verify_otp_endpoint(req: VerifyRequest):
    # 1. Check if email exists in our temporary storage
    if req.email not in generated_otps:
        raise HTTPException(
            status_code=400,
            detail="No OTP found for this email. Please request a new one.",
        )

    # 2. Check if the OTP matches
    stored_otp = generated_otps[req.email]

    if req.otp == stored_otp:
        # OTP is correct! Delete it so it can't be used twice.
        del generated_otps[req.email]
        return {"status": "success", "message": "OTP Verified Successfully!"}
    else:
        raise HTTPException(status_code=400, detail="Invalid Verification Code.")
