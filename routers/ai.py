from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
import uuid

from services.ai_service import (
    stream_chat_response,
    extract_text_from_image,
    process_and_store_pdf,
)

# Router Setup
router = APIRouter(prefix="/api", tags=["AI Services & Documents"])


class ChatRequest(BaseModel):
    query: str
    document_id: Optional[str] = None
    role: str = "learner"


@router.post("/chat")
async def chat_endpoint(request: ChatRequest):
    return StreamingResponse(
        stream_chat_response(request.query, request.document_id, request.role),
        media_type="text/event-stream",
    )


@router.post("/process-image")
async def process_image_endpoint(
    image: UploadFile = File(...),
    role: str = Form("learner"),
):
    if not image.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File provided is not an image.")
    image_bytes = await image.read()
    extracted_text = await extract_text_from_image(image_bytes, role)
    return {"extracted_text": extracted_text}


@router.post("/upload-pdf")
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
