import json
from pathlib import Path
from typing import List
from langchain_core.documents import Document

class JSONLDocumentLoader:
    """Loader for Phase 1 processed JSONL files."""

    def __init__(self, file_path: str):
        self.file_path = Path(file_path)

    def load(self) -> List[Document]:
        """Load documents from JSONL file."""
        documents = []
        if not self.file_path.exists():
            return documents

        with open(self.file_path, 'r', encoding='utf-8') as f:
            for line in f:
                if not line.strip():
                    continue
                data = json.loads(line)
                content = data.get("content", "")
                metadata = data.get("metadata", {})
                # Ensure id is in metadata for tracking if needed
                if "id" in data and "id" not in metadata:
                    metadata["id"] = data["id"]
                
                doc = Document(page_content=content, metadata=metadata)
                documents.append(doc)
        
        return documents

def load_all_from_dir(directory_path: str) -> List[Document]:
    """Load all JSONL documents from a directory."""
    all_documents = []
    path = Path(directory_path)
    if not path.exists():
        return all_documents

    for file_path in path.glob("*.jsonl"):
        loader = JSONLDocumentLoader(str(file_path))
        all_documents.extend(loader.load())
    
    return all_documents
