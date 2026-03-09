import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from internal.rag.document_loader import load_all_from_dir
from internal.rag.vector_store import VectorStoreManager

def main():
    processed_data_dir = "data/archives/processed"
    vector_db_dir = "data/vectordb"
    
    print(f"Loading documents from {processed_data_dir}...")
    documents = load_all_from_dir(processed_data_dir)
    
    if not documents:
        print("No documents found to index.")
        return

    print(f"Indexing {len(documents)} documents into {vector_db_dir}...")
    manager = VectorStoreManager(persist_directory=vector_db_dir)
    
    # Batch processing to track progress and handle large indexing
    batch_size = 1000
    for i in range(0, len(documents), batch_size):
        batch = documents[i:i+batch_size]
        if i == 0:
            manager.initialize_store(batch)
        else:
            manager.add_documents(batch)
        print(f"Index Progress: {min(i + batch_size, len(documents))}/{len(documents)}")
    
    print("Vector database built successfully.")

if __name__ == "__main__":
    main()
