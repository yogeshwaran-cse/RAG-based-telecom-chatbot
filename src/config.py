"""Configuration module for Telecom RAG system."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Base directory paths
BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BASE_DIR / ".env"

# Load environment variables from .env
load_dotenv(dotenv_path=ENV_FILE)


def _get_api_key() -> str:
    """Retrieve Google Gemini API key from environment variables."""
    key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or ""
    # Strip any enclosing quotes that might be present in .env
    key = key.strip().strip('"').strip("'")
    return key


class Settings:
    """Application settings and path configurations."""

    # API Keys & Models
    GOOGLE_API_KEY: str = _get_api_key()
    CHAT_MODEL: str = os.getenv("GEMINI_CHAT_MODEL", "gemini-3.6-flash")
    EMBEDDING_MODEL: str = os.getenv("GEMINI_EMBEDDING_MODEL", "models/gemini-embedding-001")

    # Storage Paths
    BASE_DIR: Path = BASE_DIR
    DATA_DIR: Path = BASE_DIR / "data"
    CHROMA_PERSIST_DIR: Path = BASE_DIR / "chroma_db"

    # Source Files
    FAQS_FILE: Path = DATA_DIR / "faqs.csv"
    PDF_FILE: Path = DATA_DIR / "telecom_technical_guide.pdf"
    DB_FILE: Path = Path(os.getenv("DATABASE_PATH", str(DATA_DIR / "tickets.db")))
    if not DB_FILE.is_absolute():
        DB_FILE = (BASE_DIR / DB_FILE).resolve()

    # ChromaDB Collection Names
    COLLECTION_FAQS: str = "telecom_faqs"
    COLLECTION_MANUALS: str = "telecom_manuals"
    COLLECTION_DB: str = "telecom_tickets_db"


settings = Settings()


def validate_config() -> None:
    """Validate that required environment variables and data files exist."""
    api_key = settings.GOOGLE_API_KEY
    if not api_key or api_key == "your_gemini_api_key_here":
        raise ValueError(
            "Missing valid Google Gemini API Key. Please set GEMINI_API_KEY or GOOGLE_API_KEY in .env file."
        )

    for path, name in [
        (settings.FAQS_FILE, "FAQ CSV"),
        (settings.PDF_FILE, "Technical Guide PDF"),
        (settings.DB_FILE, "Tickets Database"),
    ]:
        if not path.exists():
            raise FileNotFoundError(f"Required {name} not found at: {path}")


# Ensure consistent environment variable for Google GenAI libraries
if settings.GOOGLE_API_KEY:
    os.environ["GOOGLE_API_KEY"] = settings.GOOGLE_API_KEY
    # Remove duplicate GEMINI_API_KEY from os.environ to prevent warning from langchain_google_genai
    if "GEMINI_API_KEY" in os.environ:
        del os.environ["GEMINI_API_KEY"]
