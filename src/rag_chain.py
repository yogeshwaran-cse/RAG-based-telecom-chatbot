"""LangChain RAG chain module for Telecom Chatbot."""

from typing import Dict, Any, List, Generator, Optional
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_core.documents import Document
from langchain_google_genai import ChatGoogleGenerativeAI

from src.config import settings, validate_config
from src.retriever import get_merged_retriever, TelecomMergedRetriever


TELECOM_SYSTEM_PROMPT = """You are an expert AI Telecom Support & Operations Specialist.
Your role is to provide accurate, professional, and actionable support to customers and network engineers using ONLY the verified context below.

The context is aggregated from three telecom knowledge sources:
1. Telecom FAQs (faqs.csv): Standard customer answers on balance, SIM, billing, and roaming.
2. Technical Reference Guide (telecom_technical_guide.pdf): In-depth engineering procedures, network generations, VoLTE, SIM architecture, and connectivity diagnostics.
3. Operations Database (tickets.db): Past resolved support tickets, live network service alerts/outages, and customer profiles.

Instructions:
- Synthesize an accurate and comprehensive answer directly addressing the question.
- Cite the relevant source(s) transparently (e.g., "[Source: faqs.csv]", "[Source: Technical Guide, Page X]", or "[Source: Ticket TK-XXX / tickets.db]").
- If providing troubleshooting steps, format them into clear, actionable numbered steps.
- If there are active network outages or alerts in the region mentioned, prominently highlight them.
- If the required information is not available in the context, clearly state what is missing and advise contacting customer care (dial 611) or checking the live status portal. Do not make up facts.

Context:
{context}
"""


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


def build_rag_chain(retriever: Optional[TelecomMergedRetriever] = None):
    """Build and return a LangChain LCEL RAG chain."""
    validate_config()

    if retriever is None:
        retriever = get_merged_retriever()

    llm = ChatGoogleGenerativeAI(
        model=settings.CHAT_MODEL,
        google_api_key=settings.GOOGLE_API_KEY,
        temperature=0.2,
    )

    prompt = ChatPromptTemplate.from_messages([
        ("system", TELECOM_SYSTEM_PROMPT),
        ("human", "{question}"),
    ])

    chain = (
        {
            "context": retriever | format_docs_with_sources,
            "question": RunnablePassthrough(),
        }
        | prompt
        | llm
        | StrOutputParser()
    )
    return chain


def query_telecom_rag(
    question: str, retriever: Optional[TelecomMergedRetriever] = None
) -> Dict[str, Any]:
    """
    Execute a full RAG query, returning the LLM answer, retrieved documents,
    and formatted context for inspection and testing.
    """
    validate_config()

    if retriever is None:
        retriever = get_merged_retriever()

    # 1. Retrieve merged documents
    retrieved_docs = retriever.invoke(question)

    # 2. Format context
    formatted_context = format_docs_with_sources(retrieved_docs)

    # 3. Build prompt and run LLM
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

    # Handle output whether string or structured content
    answer_text = response.content
    if isinstance(answer_text, list):
        # Extract text blocks if returned as list of dicts/blocks
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
        "source_documents": retrieved_docs,
        "context": formatted_context,
    }


def stream_telecom_rag(
    question: str, retriever: Optional[TelecomMergedRetriever] = None
) -> Generator[str, None, None]:
    """Stream answer tokens for real-time interactive response."""
    chain = build_rag_chain(retriever)
    for chunk in chain.stream(question):
        yield chunk
