from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from core.database import get_db
from core import models

router = APIRouter(prefix="/api/trainer", tags=["Trainer Dashboard"])


@router.get("/dashboard/{firebase_uid}")
def get_trainer_dashboard(firebase_uid: str, db: Session = Depends(get_db)):
    # 1. User dhundo Firebase UID se
    user = (
        db.query(models.User).filter(models.User.firebase_uid == firebase_uid).first()
    )
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # 2. Check karo ki user ki Trainer profile hai ya nahi
    trainer = db.query(models.Trainer).filter(models.Trainer.user_id == user.id).first()
    if not trainer:
        raise HTTPException(status_code=404, detail="Trainer profile not found")

    # 3. Trainer ki saari classes (BatchTrainer) nikalo
    assignments = (
        db.query(models.BatchTrainer)
        .filter(models.BatchTrainer.trainer_id == trainer.id)
        .all()
    )

    total_students = 0
    classes_data = []

    # 4. Har class ke andar kitne bache hain wo count karo
    for assign in assignments:
        batch = assign.batch
        # Is batch mein kitne students hain wo direct nikal lo
        student_count = (
            db.query(models.Student).filter(models.Student.batch_id == batch.id).count()
        )
        total_students += student_count

        classes_data.append(
            {
                "title": assign.subject_name,
                "sub": f"{batch.course} • {batch.batch_name}",
                "count": student_count,
            }
        )

    return {
        "status": "success",
        "data": {
            "stats": {
                "students": total_students,
                "subjects": len(assignments),
                "docs": 12,
                "pending": 5,  # Dummy for now
            },
            "classes": classes_data,
        },
    }
