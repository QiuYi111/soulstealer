import pytest
import os
import shutil
import json
from unittest.mock import MagicMock
from internal.domain.agent_builder import AgentBuilder

@pytest.fixture
def temp_agent_dir():
    dir_path = "saves/test_generated_agent"
    if os.path.exists(dir_path):
        shutil.rmtree(dir_path)
    os.makedirs(dir_path)
    yield dir_path
    if os.path.exists(dir_path):
        shutil.rmtree(dir_path)

def test_agent_builder_extraction():
    # Test the XML extraction helper
    builder = AgentBuilder(retriever=None, llm_client=None)
    text = "ignore <SOUL_MD>soul content</SOUL_MD> ignore <TRAIT_JSON>{\"test\": 1}</TRAIT_JSON>"
    
    assert builder._extract_tag_content(text, "SOUL_MD") == "soul content"
    assert builder._extract_tag_content(text, "TRAIT_JSON") == "{\"test\": 1}"

def test_agent_builder_flow(temp_agent_dir):
    mock_retriever = MagicMock()
    mock_retriever.query.return_value = [
        {"content": "Historical fact 1", "metadata": {"source": "src1"}}
    ]
    
    mock_llm = MagicMock()
    mock_llm.generate_response.return_value = (
        "<SOUL_MD># Test Agent\nBio here</SOUL_MD>\n"
        "<TRAIT_JSON>{\"basic_info\": {\"name\": \"Test Agent\"}}</TRAIT_JSON>"
    )
    
    builder = AgentBuilder(retriever=mock_retriever, llm_client=mock_llm)
    success = builder.build_agent(temp_agent_dir, "Test Agent", "A test request")
    
    assert success is True
    assert os.path.exists(os.path.join(temp_agent_dir, "Soul.md"))
    assert os.path.exists(os.path.join(temp_agent_dir, "trait.json"))
    
    with open(os.path.join(temp_agent_dir, "trait.json"), "r") as f:
        data = json.load(f)
        assert data["basic_info"]["name"] == "Test Agent"
