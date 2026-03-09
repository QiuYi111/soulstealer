import pytest
import os
import shutil
from internal.rag.vector_store import VectorStoreManager
from internal.rag.retriever import SoulstealerRetriever

@pytest.fixture
def temp_db_dir():
    dir_path = "data/test_vectordb"
    if os.path.exists(dir_path):
        shutil.rmtree(dir_path)
    os.makedirs(dir_path)
    yield dir_path
    if os.path.exists(dir_path):
        shutil.rmtree(dir_path)

def test_document_loader():
    # Test reading from a sample file if needed, 
    # but here we focus on verifying retrieval flow
    pass

def test_vector_store_and_retriever(temp_db_dir):
    manager = VectorStoreManager(persist_directory=temp_db_dir)
    
    # Mock documents
    from langchain_core.documents import Document
    docs = [
        Document(page_content="乾隆三十三年，德清县发生剪辫案。", metadata={"source": "test1"}),
        Document(page_content="乞丐名为阿二，在茶馆传播流言。", metadata={"source": "test2"})
    ]
    
    manager.add_documents(docs)
    
    retriever = SoulstealerRetriever(vector_store_dir=temp_db_dir)
    results = retriever.query("德清 剪辫", top_k=1)
    
    assert len(results) > 0
    assert "德清" in results[0]["content"]
    assert results[0]["metadata"]["source"] == "test1"
