"""Merged retriever module combining Chroma collections for FAQs, Manuals, and Database records."""

from typing import List, Optional
from pydantic import Field
from langchain_core.callbacks import CallbackManagerForRetrieverRun
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever

from src.config import settings
from src.ingestion import get_vectorstore


class TelecomMergedRetriever(BaseRetriever):
    """Unified retriever that queries FAQ, Technical Manual, and Database collections, merging results."""

    faq_retriever: BaseRetriever = Field(description="Retriever for FAQ collection")
    manual_retriever: BaseRetriever = Field(description="Retriever for Technical Manual collection")
    db_retriever: BaseRetriever = Field(description="Retriever for Tickets/DB collection")

    def _get_relevant_documents(
        self, query: str, *, run_manager: Optional[CallbackManagerForRetrieverRun] = None
    ) -> List[Document]:
        """Query all three collections and return merged, deduplicated documents."""
        faq_docs = self.faq_retriever.invoke(query)
        manual_docs = self.manual_retriever.invoke(query)
        db_docs = self.db_retriever.invoke(query)

        # Merge results with source tagging
        combined_docs: List[Document] = []
        seen_contents = set()

        for doc_list in [faq_docs, manual_docs, db_docs]:
            for doc in doc_list:
                # Deduplicate based on content hash
                content_key = doc.page_content.strip()
                if content_key not in seen_contents:
                    seen_contents.add(content_key)
                    combined_docs.append(doc)

        return combined_docs


def get_merged_retriever(
    k_faqs: int = 3,
    k_manuals: int = 3,
    k_db: int = 3,
) -> TelecomMergedRetriever:
    """
    Construct and return the TelecomMergedRetriever instance wrapping
    all three ChromaDB collections.
    """
    vs_faqs = get_vectorstore(settings.COLLECTION_FAQS)
    vs_manuals = get_vectorstore(settings.COLLECTION_MANUALS)
    vs_db = get_vectorstore(settings.COLLECTION_DB)

    faq_ret = vs_faqs.as_retriever(search_kwargs={"k": k_faqs})
    manual_ret = vs_manuals.as_retriever(search_kwargs={"k": k_manuals})
    db_ret = vs_db.as_retriever(search_kwargs={"k": k_db})

    return TelecomMergedRetriever(
        faq_retriever=faq_ret,
        manual_retriever=manual_ret,
        db_retriever=db_ret,
    )
