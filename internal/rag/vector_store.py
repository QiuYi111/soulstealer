import os
from typing import List, Optional
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.documents import Document

class VectorStoreManager:
    """Manages the ChromaDB vector store."""

    def __init__(self, persist_directory: str, embedding_model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"):
        self.persist_directory = persist_directory
        # Using a multilingual model suitable for Chinese/Classical Chinese
        self.embeddings = HuggingFaceEmbeddings(model_name=embedding_model_name)
        self.vector_store: Optional[Chroma] = None

    def initialize_store(self, documents: List[Document]):
        """Create a new vector store from documents."""
        self.vector_store = Chroma.from_documents(
            documents=documents,
            embedding=self.embeddings,
            persist_directory=self.persist_directory
        )

    def load_store(self):
        """Load an existing vector store from disk."""
        if os.path.exists(self.persist_directory):
            self.vector_store = Chroma(
                persist_directory=self.persist_directory,
                embedding_function=self.embeddings
            )
        else:
            raise FileNotFoundError(f"Vector store directory {self.persist_directory} not found.")

    def add_documents(self, documents: List[Document]):
        """Add more documents to an existing store."""
        if self.vector_store is None:
            self.load_store()
        self.vector_store.add_documents(documents)

    def get_retriever(self, search_kwargs: Optional[dict] = None):
        """Get a retriever object."""
        if self.vector_store is None:
            self.load_store()
        return self.vector_store.as_retriever(search_kwargs=search_kwargs or {"k": 3})
