"""Ingestion pipeline to parse CSV, PDF, and DB and store into ChromaDB collections."""

import logging
from typing import Dict, Any
from langchain_chroma import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings

from src.config import settings, validate_config
from src.data_loader import (
    load_faq_documents,
    load_pdf_documents,
    load_db_documents,
)

logger = logging.getLogger(__name__)


def get_embedding_model() -> GoogleGenerativeAIEmbeddings:
    """Instantiate Google Generative AI Embeddings."""
    validate_config()
    return GoogleGenerativeAIEmbeddings(
        model=settings.EMBEDDING_MODEL,
        google_api_key=settings.GOOGLE_API_KEY,  # pyright: ignore[reportCallIssue]
    )


def get_vectorstore(collection_name: str) -> Chroma:
    """Get or initialize a Chroma vectorstore collection."""
    embeddings = get_embedding_model()
    settings.CHROMA_PERSIST_DIR.mkdir(parents=True, exist_ok=True)
    return Chroma(
        collection_name=collection_name,
        embedding_function=embeddings,
        persist_directory=str(settings.CHROMA_PERSIST_DIR),
    )


def ingest_collection(
    collection_name: str, documents: list, force: bool = False
) -> int:
    """Ingest documents into the specified ChromaDB collection."""
    vectorstore = get_vectorstore(collection_name)
    current_count = vectorstore._collection.count()

    if current_count > 0 and not force:
        logger.info(
            f"Collection '{collection_name}' already contains {current_count} documents. Skipping (use force=True to re-ingest)."
        )
        return current_count

    if force and current_count > 0:
        logger.info(f"Clearing existing {current_count} documents in '{collection_name}'...")
        vectorstore.reset_collection()

    logger.info(f"Ingesting {len(documents)} documents into '{collection_name}'...")
    # Add documents in batches
    batch_size = 50
    for i in range(0, len(documents), batch_size):
        batch = documents[i : i + batch_size]
        vectorstore.add_documents(batch)

    final_count = vectorstore._collection.count()
    logger.info(f"Successfully populated '{collection_name}' with {final_count} documents.")
    return final_count


def ingest_all_sources(force: bool = False) -> Dict[str, Any]:
    """
    Ingest all three telecom data sources (CSV, PDF, SQLite DB) into distinct ChromaDB collections.
    Returns a dictionary of collection names and document counts.
    """
    validate_config()

    print("[*] Loading source documents...")
    faq_docs = load_faq_documents()
    pdf_docs = load_pdf_documents()
    db_docs = load_db_documents()

    print(f"    - FAQ documents: {len(faq_docs)}")
    print(f"    - PDF manual chunks: {len(pdf_docs)}")
    print(f"    - Database records: {len(db_docs)}")

    print("\n[*] Ingesting into ChromaDB collections...")
    faq_count = ingest_collection(settings.COLLECTION_FAQS, faq_docs, force=force)
    manual_count = ingest_collection(settings.COLLECTION_MANUALS, pdf_docs, force=force)
    db_count = ingest_collection(settings.COLLECTION_DB, db_docs, force=force)

    results = {
        settings.COLLECTION_FAQS: faq_count,
        settings.COLLECTION_MANUALS: manual_count,
        settings.COLLECTION_DB: db_count,
    }

    print("\n[+] Ingestion Complete!")
    for coll, count in results.items():
        print(f"    - {coll}: {count} vectors")

    return results


import json
from pathlib import Path
from typing import Optional


def export_embedded_knowledge(output_path: Optional[Path] = None) -> Path:
    """
    Export vector documents and embeddings from all three ChromaDB collections
    into a consolidated JSON file for lightweight serverless deployment.
    """
    if output_path is None:
        output_path = settings.DATA_DIR / "embedded_knowledge.json"

    print(f"\n[*] Exporting embedded knowledge to: {output_path}")
    collections = [
        settings.COLLECTION_FAQS,
        settings.COLLECTION_MANUALS,
        settings.COLLECTION_DB,
    ]

    export_payload: Dict[str, list] = {}
    total_docs = 0

    for coll_name in collections:
        vs = get_vectorstore(coll_name)
        data = vs._collection.get(include=["documents", "metadatas", "embeddings"])
        docs = data.get("documents")
        metas = data.get("metadatas")
        embs = data.get("embeddings")

        if docs is None or metas is None or embs is None:
            print(f"    - Warning: Incomplete data or empty vectors in '{coll_name}'")
            continue

        coll_items = []
        for doc_text, meta, emb in zip(docs, metas, embs):
            coll_items.append({
                "content": doc_text,
                "metadata": meta or {},
                "embedding": list(emb) if emb is not None else [],
            })

        export_payload[coll_name] = coll_items
        total_docs += len(coll_items)
        print(f"    - Extracted {len(coll_items)} vectors from '{coll_name}'")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(export_payload, f)

    file_size_mb = output_path.stat().st_size / (1024 * 1024)
    print(f"[+] Successfully exported {total_docs} vectors ({file_size_mb:.2f} MB) -> {output_path}\n")
    return output_path


if __name__ == "__main__":
    import sys

    force_run = "--force" in sys.argv
    export_run = "--export" in sys.argv

    ingest_all_sources(force=force_run)

    if export_run:
        export_embedded_knowledge()

