"""Vercel Serverless Function entrypoint for Telecom RAG API."""

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

# Ensure root repository directory is in sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.documents import Document
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings

from src.config import settings
from src.rag_chain import TELECOM_SYSTEM_PROMPT, format_docs_with_sources

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("telecom-serverless-api")

app = FastAPI(
    title="Telecom RAG API",
    description="Vercel Serverless Function for Telecom RAG Support Chatbot",
    version="1.0.0",
)

# Enable CORS for all origins and Vercel domains
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_KNOWLEDGE_CACHE = None


def get_knowledge() -> Dict[str, Any]:
    """Load pre-embedded knowledge vectors into memory."""
    global _KNOWLEDGE_CACHE
    if _KNOWLEDGE_CACHE is None:
        knowledge_path = ROOT_DIR / "data" / "embedded_knowledge.json"
        if not knowledge_path.exists():
            raise FileNotFoundError(
                f"Knowledge base not found at: {knowledge_path}. "
                "Ensure data/embedded_knowledge.json is present."
            )
        with open(knowledge_path, "r", encoding="utf-8") as f:
            _KNOWLEDGE_CACHE = json.load(f)
    return _KNOWLEDGE_CACHE


def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    """Compute cosine similarity between two vectors."""
    dot = sum(a * b for a, b in zip(v1, v2))
    norm1 = math.sqrt(sum(a * a for a, b in zip(v1, v2)))
    norm2 = math.sqrt(sum(b * b for a, b in zip(v1, v2)))
    return dot / (norm1 * norm2) if norm1 and norm2 else 0.0


def retrieve_serverless_documents(
    query: str, top_k_per_source: int = 3
) -> List[Document]:
    """Retrieve top relevant documents across all three telecom sources."""
    knowledge = get_knowledge()
    api_key = settings.GOOGLE_API_KEY
    if not api_key:
        raise ValueError(
            "Missing Gemini API Key. Please configure GEMINI_API_KEY in Vercel Environment Variables."
        )

    embeddings_model = GoogleGenerativeAIEmbeddings(
        model=settings.EMBEDDING_MODEL,
        google_api_key=api_key,
    )
    query_vector = embeddings_model.embed_query(query)

    retrieved_docs: List[Document] = []
    seen_contents = set()

    collections = [
        settings.COLLECTION_FAQS,
        settings.COLLECTION_MANUALS,
        settings.COLLECTION_DB,
    ]

    for collection_key in collections:
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

    llm = ChatGoogleGenerativeAI(
        model=settings.CHAT_MODEL,
        google_api_key=settings.GOOGLE_API_KEY,
        temperature=0.2,
    )

    prompt = ChatPromptTemplate.from_messages([
        ("system", TELECOM_SYSTEM_PROMPT),
        ("human", "{question}"),
    ])

    messages = prompt.format_messages(context=formatted_context, question=question)
    response = llm.invoke(messages)

    answer_text = response.content
    if isinstance(answer_text, list):
        text_parts = []
        for part in answer_text:
            if isinstance(part, dict) and "text" in part:
                text_parts.append(part["text"])
            elif isinstance(part, str):
                text_parts.append(part)
        answer_text = "\n".join(text_parts)

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
