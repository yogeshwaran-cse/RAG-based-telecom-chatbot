"""Vercel Serverless Function entrypoint for Telecom RAG API.
Ultra-lightweight direct implementation using standard HTTP client (httpx) to stay well below
Vercel's 500 MB serverless function uncompressed bundle limit.
"""

import os
import sys
import math
import json
import logging
from pathlib import Path
from typing import List, Dict, Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx
from dotenv import load_dotenv

load_dotenv()
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("telecom-serverless-api")

app = FastAPI(
    title="Telecom RAG API",
    description="Ultra-lightweight Vercel Serverless Function for Telecom RAG Support Chatbot",
    version="1.1.0",
)

# Enable CORS for all origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

TELECOM_SYSTEM_PROMPT = """You are an expert AI Telecom Support & Operations Specialist.
Your role is to provide accurate, professional, and actionable support to customers and network engineers using ONLY the verified context below.

The context is aggregated from three telecom knowledge sources:
1. Telecom FAQs (faqs.csv): Standard customer answers on balance, SIM, billing, and roaming.
2. Technical Reference Guide (telecom_technical_guide.pdf): In-depth engineering procedures, network generations, VoLTE, SIM architecture, and connectivity diagnostics.
3. Operations Database (tickets.db): Past resolved support tickets, live network service alerts/outages, and customer profiles.

Instructions:
- Synthesize an accurate and comprehensive answer directly addressing the question.
- Provide a direct, natural, and professional answer. Do NOT include citation tags, bracketed references (such as [Source: ...]), or file names in the response.
- If providing troubleshooting steps, format them into clear, actionable numbered steps.
- If there are active network outages or alerts in the region mentioned, naturally mention them as part of your answer.
- If the required information is not available in the context, clearly state what is missing and advise contacting customer care (dial 611) or checking the live status portal. Do not make up facts.

Context:
{context}
"""

COLLECTION_FAQS = "telecom_faqs"
COLLECTION_MANUALS = "telecom_manuals"
COLLECTION_DB = "telecom_tickets_db"


class Document:
    """Lightweight document container replacing langchain_core.documents.Document."""

    def __init__(self, page_content: str, metadata: Dict[str, Any] = None):
        self.page_content = page_content
        self.metadata = metadata or {}


def get_api_key() -> str:
    """Retrieve Google Gemini API key from environment."""
    key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or ""
    return key.strip().strip('"').strip("'")


def get_chat_model_name() -> str:
    return os.getenv("GEMINI_CHAT_MODEL", "gemini-3.5-flash-lite")


def get_embedding_model_name() -> str:
    return os.getenv("GEMINI_EMBEDDING_MODEL", "gemini-embedding-001")


_KNOWLEDGE_CACHE = None


def get_knowledge() -> Dict[str, Any]:
    """Load pre-embedded knowledge vectors into memory from canonical path."""
    global _KNOWLEDGE_CACHE
    if _KNOWLEDGE_CACHE is None:
        base_file = Path(__file__).resolve()
        candidates = [
            base_file.parent.parent / "data" / "embedded_knowledge.json",
            base_file.parent / "data" / "embedded_knowledge.json",
            Path.cwd() / "data" / "embedded_knowledge.json",
        ]
        chosen_path = None
        for cand in candidates:
            resolved = cand.resolve()
            if resolved.exists():
                chosen_path = resolved
                break

        if not chosen_path:
            raise FileNotFoundError(
                f"Knowledge base not found. Checked: {[str(c.resolve()) for c in candidates]}"
            )

        with open(chosen_path, "r", encoding="utf-8") as f:
            _KNOWLEDGE_CACHE = json.load(f)
    return _KNOWLEDGE_CACHE


def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    """Compute cosine similarity between two vectors."""
    dot = sum(a * b for a, b in zip(v1, v2))
    norm1 = math.sqrt(sum(a * a for a, b in zip(v1, v2)))
    norm2 = math.sqrt(sum(b * b for b in v2))
    return dot / (norm1 * norm2) if norm1 and norm2 else 0.0


def format_docs_with_sources(docs: List[Document]) -> str:
    """Format retrieved documents with clean metadata citations."""
    if not docs:
        return "No relevant documents found."

    formatted_chunks = []
    for i, doc in enumerate(docs, 1):
        source = doc.metadata.get("source", "Unknown")
        source_type = doc.metadata.get("source_type", "document")
        extras = []

        if "page" in doc.metadata:
            extras.append(f"Page {doc.metadata['page']}")
        if "category" in doc.metadata:
            extras.append(f"Category: {doc.metadata['category']}")
        if "ticket_id" in doc.metadata:
            extras.append(f"Ticket ID: {doc.metadata['ticket_id']}")
        if "table" in doc.metadata:
            extras.append(f"Table: {doc.metadata['table']}")
        if "severity" in doc.metadata:
            extras.append(f"Severity: {doc.metadata['severity']}")

        extra_str = f" | {', '.join(extras)}" if extras else ""
        header = f"--- [Document {i}] Source: {source} ({source_type}{extra_str}) ---"
        formatted_chunks.append(f"{header}\n{doc.page_content.strip()}")

    return "\n\n".join(formatted_chunks)


def embed_text_direct(text: str, api_key: str, model_name: str) -> List[float]:
    """Embed input query directly via Gemini REST API without heavy SDKs."""
    clean_model = model_name.replace("models/", "")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{clean_model}:embedContent?key={api_key}"
    payload = {"content": {"parts": [{"text": text}]}}

    with httpx.Client(timeout=30.0) as client:
        resp = client.post(url, json=payload)
        if resp.status_code != 200:
            raise RuntimeError(f"Gemini Embedding API returned {resp.status_code}: {resp.text}")
        data = resp.json()
        embedding = data.get("embedding", {}).get("values")
        if not embedding:
            raise RuntimeError(f"No embedding returned in Gemini response: {data}")
        return embedding


def generate_chat_direct(question: str, context: str, api_key: str, model_name: str) -> str:
    """Call Gemini generateContent directly via REST API with fallback support."""
    clean_model = model_name.replace("models/", "")
    system_text = TELECOM_SYSTEM_PROMPT.format(context=context)
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{clean_model}:generateContent?key={api_key}"

    payload = {
        "system_instruction": {
            "parts": [{"text": system_text}]
        },
        "contents": [
            {"role": "user", "parts": [{"text": question}]}
        ],
        "generationConfig": {
            "temperature": 0.2
        }
    }

    with httpx.Client(timeout=45.0) as client:
        resp = client.post(url, json=payload)
        if resp.status_code == 404 and clean_model != "gemini-3.5-flash-lite":
            logger.warning(f"Model {clean_model} returned 404, falling back to gemini-3.5-flash-lite")
            fallback_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash-lite:generateContent?key={api_key}"
            resp = client.post(fallback_url, json=payload)

        if resp.status_code != 200:
            raise RuntimeError(f"Gemini Chat API returned {resp.status_code}: {resp.text}")

        data = resp.json()
        candidates = data.get("candidates", [])
        if not candidates:
            return "Unable to generate answer from context."

        parts = candidates[0].get("content", {}).get("parts", [])
        return "".join(part.get("text", "") for part in parts).strip()


def retrieve_serverless_documents(
    query: str, top_k_per_source: int = 3
) -> List[Document]:
    """Retrieve top relevant documents across all three telecom sources."""
    knowledge = get_knowledge()
    api_key = get_api_key()
    if not api_key:
        raise ValueError(
            "Missing Gemini API Key. Please configure GEMINI_API_KEY in Vercel Environment Variables."
        )

    query_vector = embed_text_direct(query, api_key, get_embedding_model_name())

    retrieved_docs: List[Document] = []
    seen_contents = set()

    for collection_key in [COLLECTION_FAQS, COLLECTION_MANUALS, COLLECTION_DB]:
        items = knowledge.get(collection_key, [])
        scored = []
        for item in items:
            sim = cosine_similarity(query_vector, item["embedding"])
            scored.append((sim, item["content"], item.get("metadata", {})))
        scored.sort(key=lambda x: x[0], reverse=True)

        for sim, content, meta in scored[:top_k_per_source]:
            content_key = content.strip()
            if content_key not in seen_contents:
                seen_contents.add(content_key)
                retrieved_docs.append(Document(page_content=content, metadata=meta))

    return retrieved_docs


def query_serverless_rag(question: str) -> Dict[str, Any]:
    """Process a user question through the serverless RAG pipeline."""
    docs = retrieve_serverless_documents(question)
    formatted_context = format_docs_with_sources(docs)

    api_key = get_api_key()
    answer_text = generate_chat_direct(
        question=question,
        context=formatted_context,
        api_key=api_key,
        model_name=get_chat_model_name(),
    )

    return {
        "question": question,
        "answer": answer_text,
        "source_documents": docs,
    }


class ChatRequest(BaseModel):
    question: str


class ChatResponse(BaseModel):
    question: str
    answer: str


@app.get("/")
@app.get("/api")
@app.get("/api/health")
def health_check():
    """Health check endpoint."""
    return {"status": "ok", "service": "telecom-rag-vercel-serverless"}


@app.post("/api/chat", response_model=ChatResponse)
def chat_endpoint(request: ChatRequest):
    """Process a user question through the Telecom RAG pipeline."""
    cleaned_question = request.question.strip()
    if not cleaned_question:
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    try:
        logger.info(f"Processing question: {cleaned_question}")
        result = query_serverless_rag(cleaned_question)
        return ChatResponse(
            question=cleaned_question,
            answer=result["answer"],
        )
    except Exception as exc:
        logger.error(f"Error in serverless query: {exc}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error processing query: {str(exc)}",
        )
