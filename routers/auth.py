from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.orm import Session
import random

from core.database import get_db
from core import models
from services.email_service import send_real_otp_email

# Router Setup (Tags help in API Docs)
router = APIRouter(tags=["Authentication"])

# Temporary OTP Storage
generated_otps = {}


# Pydantic Models for Auth
class AuthSyncRequest(BaseModel):
    firebase_uid: str
    email: str
    name: str
    role: str = "learner"


class EmailRequest(BaseModel):
    email: str


class VerifyRequest(BaseModel):
    email: str
    otp: str


# Endpoints
@router.post("/api/auth/sync")
def sync_user_with_postgres(req: AuthSyncRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == req.email).first()

    if not user:
        new_user = models.User(
            firebase_uid=req.firebase_uid,
            email=req.email,
            name=req.name,
            role=req.role,
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        user = new_user
    else:
        if not user.firebase_uid:
            user.firebase_uid = req.firebase_uid
            db.commit()
            db.refresh(user)

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is deactivated.")

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


@router.post("/api/send-otp")
async def send_otp_endpoint(req: EmailRequest, background_tasks: BackgroundTasks):
    otp_code = str(random.randint(100000, 999999))
    generated_otps[req.email] = otp_code
    print(f"OTP generated for {req.email}: {otp_code}")
    background_tasks.add_task(send_real_otp_email, req.email, otp_code)
    return {"status": "success", "message": "OTP sent successfully in the background!"}


@router.post("/api/verify-otp")
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
