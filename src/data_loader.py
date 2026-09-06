"""Data loader module for CSV, PDF, and SQLite database sources."""

import csv
import sqlite3
from pathlib import Path
from typing import List
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
import pypdf

from src.config import settings


def load_faq_documents(csv_path: Path = settings.FAQS_FILE) -> List[Document]:
    """Load and format FAQ records from CSV into LangChain Documents."""
    documents = []
    with open(csv_path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            content = (
                f"Category: {row.get('category', '').strip()}\n"
                f"Question: {row.get('question', '').strip()}\n"
                f"Answer: {row.get('answer', '').strip()}"
            )
            metadata = {
                "source": "faqs.csv",
                "source_type": "faq",
                "faq_id": row.get("id", "").strip(),
                "category": row.get("category", "").strip(),
                "question": row.get("question", "").strip(),
            }
            documents.append(Document(page_content=content, metadata=metadata))
    return documents


def load_pdf_documents(pdf_path: Path = settings.PDF_FILE) -> List[Document]:
    """Load and chunk technical manual PDF into LangChain Documents."""
    reader = pypdf.PdfReader(str(pdf_path))
    raw_docs = []

    for i, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        text = text.strip()
        if not text:
            continue
        # Standardize whitespace
        cleaned_text = "\n".join(
            line.strip() for line in text.splitlines() if line.strip()
        )
        raw_docs.append(
            Document(
                page_content=cleaned_text,
                metadata={
                    "source": "telecom_technical_guide.pdf",
                    "source_type": "manual",
                    "page": i + 1,
                },
            )
        )

    # Chunk the documents for optimal vector search
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=650,
        chunk_overlap=100,
        separators=["\n\n", "\n", " ", ""],
    )
    chunked_docs = splitter.split_documents(raw_docs)
    return chunked_docs


def load_db_documents(db_path: Path = settings.DB_FILE) -> List[Document]:
    """Load records from SQLite database (tickets, alerts, customers) into LangChain Documents."""
    documents = []
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # 1. Ingest Support Tickets
    cursor.execute("SELECT * FROM tickets")
    for row in cursor.fetchall():
        content = (
            f"[Support Ticket {row['ticket_id']}]\n"
            f"Customer: {row['customer_name']} (Phone: {row['phone_number']})\n"
            f"Category: {row['category']} | Issue Type: {row['issue_type']}\n"
            f"Priority: {row['priority']} | Status: {row['status']}\n"
            f"Created At: {row['created_at']} | Updated At: {row['updated_at']}\n"
            f"Customer Complaint / Description:\n{row['description']}\n"
            f"Resolution / Action Taken:\n{row['resolution']}\n"
            f"Technician Notes:\n{row['technician_notes']}"
        )
        metadata = {
            "source": "tickets.db",
            "table": "tickets",
            "source_type": "ticket",
            "ticket_id": row["ticket_id"],
            "category": row["category"],
            "status": row["status"],
            "priority": row["priority"],
        }
        documents.append(Document(page_content=content, metadata=metadata))

    # 2. Ingest Service Alerts / Outages
    cursor.execute("SELECT * FROM service_alerts")
    for row in cursor.fetchall():
        status_text = "Active Outage / Maintenance" if row["active"] else "Resolved"
        content = (
            f"[Network Service Alert: {row['title']}]\n"
            f"Region: {row['region']}\n"
            f"Service Type: {row['service_type']} | Severity: {row['severity']}\n"
            f"Status: {status_text} | ETA: {row['eta'] or 'N/A'}\n"
            f"Alert Details:\n{row['message']}"
        )
        metadata = {
            "source": "tickets.db",
            "table": "service_alerts",
            "source_type": "service_alert",
            "alert_title": row["title"],
            "region": row["region"],
            "severity": row["severity"],
            "is_active": bool(row["active"]),
        }
        documents.append(Document(page_content=content, metadata=metadata))

    # 3. Ingest Customer Profiles
    cursor.execute("SELECT * FROM customers")
    for row in cursor.fetchall():
        content = (
            f"[Customer Profile: {row['name']}]\n"
            f"Customer ID: {row['customer_id']} | Phone: {row['phone_number']}\n"
            f"Email: {row['email']}\n"
            f"Plan Name: {row['plan_name']}\n"
            f"Account Status: {row['account_status']} | Billing Cycle Day: {row['billing_cycle_day']}"
        )
        metadata = {
            "source": "tickets.db",
            "table": "customers",
            "source_type": "customer",
            "customer_id": row["customer_id"],
            "phone_number": row["phone_number"],
            "account_status": row["account_status"],
        }
        documents.append(Document(page_content=content, metadata=metadata))

    conn.close()
    return documents
