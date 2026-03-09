from typing import List, Dict, Any, Optional
from .vector_store import VectorStoreManager

class SoulstealerRetriever:
    """High-level retriever interface for the Soulstealer RAG system."""

    def __init__(self, vector_store_dir: str):
        self.manager = VectorStoreManager(persist_directory=vector_store_dir)
        try:
            self.manager.load_store()
        except FileNotFoundError:
            # If store doesn't exist yet, we'll handle it during query or wait for build
            self.manager.vector_store = None

    def query(self, text: str, top_k: int = 3, filter_kwargs: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Query the RAG system for relevant historical context.
        
        Args:
            text: The query string.
            top_k: Number of results to return.
            filter_kwargs: Metadata filters (e.g., {"location": "浙江"}).
            
        Returns:
            A list of dicts containing 'content' and 'metadata'.
        """
        if self.manager.vector_store is None:
            try:
                self.manager.load_store()
            except FileNotFoundError:
                return []

        search_kwargs = {"k": top_k}
        if filter_kwargs:
            search_kwargs["filter"] = filter_kwargs

        docs = self.manager.vector_store.similarity_search(text, **search_kwargs)
        
        return [
            {
                "content": doc.page_content,
                "metadata": doc.metadata
            }
            for doc in docs
        ]
