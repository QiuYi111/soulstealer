import pytest
from unittest.mock import MagicMock, patch
from internal.application.setup_service import SetupService

@pytest.fixture
def mock_retriever():
    return MagicMock()

@pytest.fixture
def mock_llm():
    return MagicMock()

@pytest.fixture
def setup_service(mock_retriever, mock_llm):
    return SetupService(retriever=mock_retriever, llm=mock_llm, max_concurrency=2)

def test_setup_service_initialization(mock_retriever, mock_llm):
    service = SetupService(retriever=mock_retriever, llm=mock_llm)
    assert service.retriever == mock_retriever
    assert service.llm == mock_llm
    assert service.max_concurrency == 10  # default

@pytest.mark.asyncio
async def test_batch_generate_agents(setup_service):
    # Setup mock builder behavior
    with patch("internal.application.setup_service.AgentBuilder") as mock_builder_cls:
        mock_builder = MagicMock()
        # Mock build_agent_async if it exists, otherwise we assume build_agent is made async or wrapped
        # We'll design SetupService to wrap the synchronous build_agent into an async call or similar
        mock_builder.build_agent.return_value = True
        mock_builder_cls.return_value = mock_builder

        requests = [
            {"save_dir": "temp_dir/agent1", "name": "Agent1", "desc": "Desc 1"},
            {"save_dir": "temp_dir/agent2", "name": "Agent2", "desc": "Desc 2"},
            {"save_dir": "temp_dir/agent3", "name": "Agent3", "desc": "Desc 3"},
        ]

        def stub_progress(done, total, status):
            pass

        results = await setup_service.batch_generate_agents(requests, progress_callback=stub_progress)
        
        assert len(results) == 3
        assert all(results)
        # Check if build_agent was called correctly
        assert mock_builder.build_agent.call_count == 3
        mock_builder.build_agent.assert_any_call("temp_dir/agent1", "Agent1", "Desc 1")
        mock_builder.build_agent.assert_any_call("temp_dir/agent2", "Agent2", "Desc 2")
        mock_builder.build_agent.assert_any_call("temp_dir/agent3", "Agent3", "Desc 3")

@pytest.mark.asyncio
async def test_batch_generate_agents_with_failure(setup_service):
    with patch("internal.application.setup_service.AgentBuilder") as mock_builder_cls:
        mock_builder = MagicMock()
        # Fail on the second agent
        def side_effect(save_dir, name, desc):
            return name != "FailAgent"
        mock_builder.build_agent.side_effect = side_effect
        mock_builder_cls.return_value = mock_builder

        requests = [
            {"save_dir": "temp_dir/agent1", "name": "Agent1", "desc": "Desc 1"},
            {"save_dir": "temp_dir/fail", "name": "FailAgent", "desc": "Desc 2"},
        ]

        results = await setup_service.batch_generate_agents(requests)
        
        assert len(results) == 2
        assert results[0] is True
        assert results[1] is False
