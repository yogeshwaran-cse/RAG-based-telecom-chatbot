"""FastAPI backend application for Telecom RAG Chatbot."""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import logging

from src.rag_chain import query_telecom_rag
from src.config import validate_config
from src.ingestion import ingest_all_sources
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Telecom RAG API",
    description="Backend API for Telecom RAG Support Chatbot",
    version="0.1.0",
)

# Enable CORS for local development and Vercel deployments
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "*",
    ],
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    question: str


class ChatResponse(BaseModel):
    question: str
    answer: str


@app.on_event("startup")
def startup_event():
    """Validate environment and ensure ChromaDB collections are populated."""
    try:
        validate_config()
        # Automatically ingest documents if collections do not exist yet (e.g. on fresh cloud deployments)
        ingest_all_sources(force=False)
        logger.info("Telecom RAG API started successfully.")
    except Exception as exc:
        logger.error(f"Startup validation failed: {exc}")


@app.get("/")
def root_endpoint():
    """Root endpoint for status inspection."""
    return {
        "status": "online",
        "service": "Telecom RAG Chatbot API",
        "endpoints": {
            "health": "/api/health",
            "chat": "/api/chat",
            "docs": "/docs",
        },
    }


@app.get("/api/health")
def health_check():
    """Health check endpoint."""
    return {"status": "ok", "service": "telecom-rag-api"}


@app.post("/api/chat", response_model=ChatResponse)
def chat_endpoint(request: ChatRequest):
    """Process a user question through the Telecom RAG pipeline."""
    cleaned_question = request.question.strip()
    if not cleaned_question:
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    try:
        logger.info(f"Processing question: {cleaned_question}")
        result = query_telecom_rag(cleaned_question)
        return ChatResponse(
            question=cleaned_question,
            answer=result["answer"],
        )
    except Exception as exc:
        logger.error(f"Error executing RAG query: {exc}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process telecom query: {str(exc)}",
        )


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("src.api:app", host="0.0.0.0", port=port, reload=False)
