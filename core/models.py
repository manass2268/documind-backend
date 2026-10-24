
from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    ForeignKey,
    UniqueConstraint,
    PrimaryKeyConstraint,
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from core.database import Base


# ==================================================
# 1. USERS
# Central account table
# ==================================================
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)

    # Firebase authentication identity
    firebase_uid = Column(
        String(128), unique=True, index=True, nullable=True
    )

    email = Column(String(255), unique=True, index=True, nullable=False)
    name = Column(String(150), nullable=False)
    role = Column(String(30), nullable=False, default="learner")
    is_active = Column(Boolean, nullable=False, default=True)

    created_at = Column(
        DateTime(timezone=True), server_default=func.now()
    )

    # One account can have a student or trainer profile
    student_profile = relationship(
        "Student", back_populates="user", uselist=False
    )

    trainer_profile = relationship(
        "Trainer", back_populates="user", uselist=False
    )


# ==================================================
# 2. DEPARTMENTS
# Example: CSD
# ==================================================
class Department(Base):
    __tablename__ = "departments"

    department_id = Column(Integer, primary_key=True, index=True)
    department_name = Column(String(150), unique=True, nullable=False)

    courses = relationship("Course", back_populates="department")
    trainers = relationship("Trainer", back_populates="department")


# ==================================================
# 3. COURSES
# Example: BCA
# ==================================================
class Course(Base):
    __tablename__ = "courses"

    course_id = Column(Integer, primary_key=True, index=True)
    course_name = Column(String(100), unique=True, nullable=False)
    duration_years = Column(Integer, nullable=True)

    department_id = Column(
        Integer,
        ForeignKey("departments.department_id"),
        nullable=False,
    )

    department = relationship("Department", back_populates="courses")
    batches = relationship("Batch", back_populates="course")


# ==================================================
# 4. TRAINERS
# trainer user_id is BOTH PK and FK to users.id
# ==================================================
class Trainer(Base):
    __tablename__ = "trainers"

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        primary_key=True,
    )

    phone = Column(String(25), nullable=True)

    department_id = Column(
        Integer,
        ForeignKey("departments.department_id"),
        nullable=False,
    )

    designation = Column(String(100), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)

    user = relationship("User", back_populates="trainer_profile")

    department = relationship("Department", back_populates="trainers")

    teaching_assignments = relationship(
        "TeachingAssignment",
        back_populates="trainer",
    )


# ==================================================
# 5. BATCHES
# Example: BCA 2nd Year, 2025-2028
# ==================================================
class Batch(Base):
    __tablename__ = "batches"

    batch_id = Column(Integer, primary_key=True, index=True)

    course_id = Column(
        Integer,
        ForeignKey("courses.course_id"),
        nullable=False,
    )

    batch_name = Column(String(100), nullable=False)
    academic_session = Column(String(30), nullable=True)

    is_active = Column(Boolean, nullable=False, default=True)

    course = relationship("Course", back_populates="batches")

    sections = relationship("Section", back_populates="batch")


# ==================================================
# 6. SECTIONS
# Example: BCA 2nd Year - Section A
# ==================================================
class Section(Base):
    __tablename__ = "sections"

    section_id = Column(Integer, primary_key=True, index=True)

    batch_id = Column(
        Integer,
        ForeignKey("batches.batch_id"),
        nullable=False,
    )

    section_name = Column(String(30), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)

    __table_args__ = (
        UniqueConstraint(
            "batch_id",
            "section_name",
            name="uq_batch_section",
        ),
    )

    batch = relationship("Batch", back_populates="sections")

    student_enrollments = relationship(
        "StudentEnrollment",
        back_populates="section",
    )

    teaching_assignments = relationship(
        "TeachingAssignment",
        back_populates="section",
    )


# ==================================================
# 7. STUDENTS
# roll_no is the PRIMARY KEY
# ==================================================
class Student(Base):
    __tablename__ = "students"

    roll_no = Column(String(50), primary_key=True, index=True)

    # Connect student profile to central account
    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        unique=True,
        nullable=False,
    )

    admission_status = Column(
        String(30), nullable=False, default="active"
    )

    user = relationship("User", back_populates="student_profile")

    enrollments = relationship(
        "StudentEnrollment",
        back_populates="student",
    )


# ==================================================
# 8. STUDENT ENROLLMENTS
# Student mapped by roll_no
# Composite PK: roll_no + section_id
# ==================================================
class StudentEnrollment(Base):
    __tablename__ = "student_enrollments"

    roll_no = Column(
        String(50),
        ForeignKey("students.roll_no"),
        nullable=False,
    )

    section_id = Column(
        Integer,
        ForeignKey("sections.section_id"),
        nullable=False,
    )

    enrolled_at = Column(
        DateTime(timezone=True), server_default=func.now()
    )

    status = Column(String(30), nullable=False, default="active")

    __table_args__ = (
        PrimaryKeyConstraint(
            "roll_no",
            "section_id",
            name="pk_student_enrollment",
        ),
    )

    student = relationship("Student", back_populates="enrollments")

    section = relationship("Section", back_populates="student_enrollments")


# ==================================================
# 9. SUBJECTS
# Example: Python, DBMS
# ==================================================
class Subject(Base):
    __tablename__ = "subjects"

    subject_id = Column(Integer, primary_key=True, index=True)
    subject_name = Column(String(150), unique=True, nullable=False)
    subject_code = Column(String(50), unique=True, nullable=True)

    teaching_assignments = relationship(
        "TeachingAssignment",
        back_populates="subject",
    )


# ==================================================
# 10. TEACHING ASSIGNMENTS
# Trainer mapped by trainer_user_id
# Composite PK: trainer + section + subject
# ==================================================
class TeachingAssignment(Base):
    __tablename__ = "teaching_assignments"

    trainer_user_id = Column(
        Integer,
        ForeignKey("trainers.user_id"),
        nullable=False,
    )

    section_id = Column(
        Integer,
        ForeignKey("sections.section_id"),
        nullable=False,
    )

    subject_id = Column(
        Integer,
        ForeignKey("subjects.subject_id"),
        nullable=False,
    )

    assigned_at = Column(
        DateTime(timezone=True), server_default=func.now()
    )

    is_active = Column(Boolean, nullable=False, default=True)

    __table_args__ = (
        PrimaryKeyConstraint(
            "trainer_user_id",
            "section_id",
            "subject_id",
            name="pk_teaching_assignment",
        ),
    )

    trainer = relationship(
        "Trainer", back_populates="teaching_assignments"
    )

    section = relationship(
        "Section", back_populates="teaching_assignments"
    )

    subject = relationship(
        "Subject", back_populates="teaching_assignments"
    )
