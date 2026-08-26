"""
rag_store.py
Vector Database (ChromaDB / Azure AI Search integration) & Document RAG module.
Handles text chunking, vector embedding, and context retrieval for large
annual reports / financial statements exceeding standard prompt limits.
"""

import os
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)

try:
    import chromadb
    from chromadb.config import Settings
    HAS_CHROMADB = True
except ImportError:
    HAS_CHROMADB = False
    logger.warning("ChromaDB is not installed. Falling back to in-memory sliding window RAG.")

class FinancialRAGStore:
    def __init__(self, collection_name: str = "financial_reports"):
        self.collection_name = collection_name
        self.chroma_client = None
        self.collection = None

        if HAS_CHROMADB:
            try:
                self.chroma_client = chromadb.Client(Settings(anonymized_telemetry=False))
                self.collection = self.chroma_client.get_or_create_collection(name=self.collection_name)
            except Exception as e:
                logger.error(f"Failed to initialize ChromaDB collection: {e}")

    def chunk_text(self, text: str, chunk_size: int = 1500, overlap: int = 200) -> List[str]:
        """
        Splits large document text into overlapping semantic chunks.
        """
        if not text:
            return []
        
        chunks = []
        start = 0
        text_length = len(text)

        while start < text_length:
            end = min(start + chunk_size, text_length)
            chunks.append(text[start:end])
            start += (chunk_size - overlap)

        return chunks

    def index_document(self, doc_id: str, document_text: str) -> int:
        """
        Chunks and indexes financial document text in vector store.
        """
        chunks = self.chunk_text(document_text)
        if not chunks:
            return 0

        if HAS_CHROMADB and self.collection:
            ids = [f"{doc_id}_chunk_{i}" for i in range(len(chunks))]
            metadatas = [{"doc_id": doc_id, "chunk_index": i} for i in range(len(chunks))]
            
            self.collection.add(
                documents=chunks,
                ids=ids,
                metadatas=metadatas
            )
            logger.info(f"Indexed {len(chunks)} chunks in ChromaDB vector store for doc {doc_id}.")
        
        return len(chunks)

    def retrieve_relevant_context(self, query: str, document_text: str, top_k: int = 5) -> str:
        """
        Retrieves top_k most relevant chunks using vector similarity or keyword matching.
        """
        chunks = self.chunk_text(document_text)
        if not chunks:
            return ""

        if HAS_CHROMADB and self.collection:
            try:
                results = self.collection.query(
                    query_texts=[query],
                    n_results=min(top_k, len(chunks))
                )
                if results and 'documents' in results and results['documents']:
                    retrieved_chunks = results['documents'][0]
                    return "\n\n--- FINANCIAL SECTION CHUNK ---\n\n".join(retrieved_chunks)
            except Exception as e:
                logger.error(f"Vector search query failed: {e}. Falling back to text slice.")

        # Fallback: Top-k keyword match scoring
        query_words = set(query.lower().split())
        scored_chunks = []
        for chunk in chunks:
            score = sum(1 for word in query_words if word in chunk.lower())
            scored_chunks.append((score, chunk))
        
        scored_chunks.sort(key=lambda x: x[0], reverse=True)
        top_chunks = [c[1] for c in scored_chunks[:top_k]]
        return "\n\n--- FINANCIAL SECTION CHUNK ---\n\n".join(top_chunks)


# Singleton RAG store instance
rag_store = FinancialRAGStore()
