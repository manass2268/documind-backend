import os
from dotenv import load_dotenv

# 🚀 FORCE OVERRIDE: Yeh ensure karega ki purani cached keys ignore hon aur nayi .env force-load ho
load_dotenv(override=True)


class APIKeyManager:
    def __init__(self):
        # .env se keys read karo, empty spaces/blank keys aur quotes ("") ko filter kardo
        student_keys_raw = os.getenv("STUDENT_API_KEYS", "")
        self.student_keys = [
            k.strip().strip('"').strip("'")
            for k in student_keys_raw.split(",")
            if k.strip()
        ]

        teacher_keys_raw = os.getenv("TEACHER_API_KEYS", "")
        self.teacher_keys = [
            k.strip().strip('"').strip("'")
            for k in teacher_keys_raw.split(",")
            if k.strip()
        ]

        admin_keys_raw = os.getenv("ADMIN_API_KEYS", "")
        self.admin_keys = [
            k.strip().strip('"').strip("'")
            for k in admin_keys_raw.split(",")
            if k.strip()
        ]

        # Tracking variables (Current active index)
        self.current_student_idx = 0
        self.current_teacher_idx = 0
        self.current_admin_idx = 0

        print(
            f"🔑 API Keys Loaded: {len(self.student_keys)} Student, {len(self.teacher_keys)} Teacher, {len(self.admin_keys)} Admin"
        )

        # 🚀 DEBUG CHECK: Server start hote hi terminal mein dikhayega ki asali key aayi ya nahi
        if self.student_keys:
            print(f"✅ Active Student Key starts with: {self.student_keys[0][:6]}...")

    def get_key(self, role: str) -> str:

        if role == "learner":
            if self.student_keys and self.current_student_idx < len(self.student_keys):
                return self.student_keys[self.current_student_idx]
            else:
                print("⚠️ All Student Keys exhausted! Trying fallback...")
                return self.get_fallback_key()

        elif role == "trainer":
            if self.teacher_keys and self.current_teacher_idx < len(self.teacher_keys):
                return self.teacher_keys[self.current_teacher_idx]
            else:
                print("⚠️ No/All Teacher Keys exhausted! Trying fallback...")
                return self.get_fallback_key()

        elif role == "admin":
            if self.admin_keys and self.current_admin_idx < len(self.admin_keys):
                return self.admin_keys[self.current_admin_idx]
            else:
                return self.get_fallback_key()

        return self.get_fallback_key()

    def get_fallback_key(self) -> str:

        if self.admin_keys and self.current_admin_idx < len(self.admin_keys):
            return self.admin_keys[self.current_admin_idx]

        elif self.student_keys:
            fallback_idx = self.current_student_idx % len(self.student_keys)
            return self.student_keys[fallback_idx]

        else:
            raise Exception("CRITICAL: No API Keys available in the system!")

    def mark_key_exhausted(self, role: str):

        if role == "learner" and self.student_keys:
            self.current_student_idx += 1
            if self.current_student_idx < len(self.student_keys):
                print(f"🔄 Switched to Student Key #{self.current_student_idx + 1}")
            else:
                print("❌ All Student Keys are now exhausted.")

        elif role == "trainer" and self.teacher_keys:
            self.current_teacher_idx += 1
            if self.current_teacher_idx < len(self.teacher_keys):
                print(f"🔄 Switched to Teacher Key #{self.current_teacher_idx + 1}")

        elif role == "admin" and self.admin_keys:
            self.current_admin_idx += 1
            if self.current_admin_idx < len(self.admin_keys):
                print(f"🔄 Switched to Admin Key #{self.current_admin_idx + 1}")


# Create a Global Singleton Instance
key_manager = APIKeyManager()
