from dotenv import load_dotenv
import os
from pathlib import Path

load_dotenv()


class Settings:
    
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
    VOYAGE_API_KEY = os.getenv("VOYAGE_API_KEY", "")
        
    EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS", "")
    EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "")
    GMAIL_CREDENTIALS_PATH = os.getenv("GMAIL_CREDENTIALS_PATH", "credentials.json")
    GMAIL_TOKEN_PATH = os.getenv("GMAIL_TOKEN_PATH", "token.json")
    
    SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
    
    BASE_DIR = Path(__file__).parent.parent.parent
    DATA_DIR = BASE_DIR / "data"
    RAW_DATA_PATH = str(DATA_DIR / "raw")
    PROCESSED_DATA_PATH = str(DATA_DIR / "processed")
    VECTOR_STORE_PATH = str(DATA_DIR / "vector_store")
    
    @classmethod
    def create_directories(cls):
        os.makedirs(cls.RAW_DATA_PATH, exist_ok=True)
        os.makedirs(cls.PROCESSED_DATA_PATH, exist_ok=True)
        os.makedirs(cls.VECTOR_STORE_PATH, exist_ok=True)
    
    GEMINI_MODEL = "gemini-2.5-flash"
    EMBEDDING_MODEL = "voyage-3.5-lite"

    ENABLE_EMAIL_SCANNING = os.getenv("ENABLE_EMAIL_SCANNING", "true").lower() == "true"
    ENABLE_RAG = True
    ENABLE_REMINDERS = os.getenv("ENABLE_REMINDERS", "true").lower() == "true"
    
    DEFAULT_EMAIL_SCAN_TYPE = os.getenv("DEFAULT_EMAIL_SCAN_TYPE", "bills")
    EMAIL_SCAN_MAX_RESULTS = int(os.getenv("EMAIL_SCAN_MAX_RESULTS", "50"))
    
    @classmethod
    def validate(cls) -> tuple[bool, list[str]]:
        errors = []
        if not cls.GOOGLE_API_KEY:
            errors.append("GOOGLE_API_KEY is not set")
        if not cls.VOYAGE_API_KEY:
            errors.append("VOYAGE_API_KEY is required")
        if cls.ENABLE_EMAIL_SCANNING and not os.path.exists(cls.GMAIL_CREDENTIALS_PATH):
            errors.append(f"Gmail credentials not found: {cls.GMAIL_CREDENTIALS_PATH}")
        return len(errors) == 0, errors

    @classmethod
    def get_config_summary(cls) -> str:
        summary = "Bill Tracker Configuration (Local RAG Mode):\n"
        summary += f"  LLM: {cls.GEMINI_MODEL}\n"
        summary += f"  Storage: Local Vector Store ({cls.VECTOR_STORE_PATH})\n"
        return summary


settings = Settings()
settings.create_directories()