import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from internal.application.archive_service import ArchiveService

@pytest.fixture
def mock_persistence():
    return MagicMock()

@pytest.fixture
def mock_llm():
    m = MagicMock()
    m.get_response_async = AsyncMock()
    return m

@pytest.fixture
def service(mock_persistence, mock_llm):
    return ArchiveService(persistence=mock_persistence, llm=mock_llm, llm_model="test-model")

@pytest.mark.asyncio
async def test_generate_save_name(service, mock_llm):
    mock_llm.get_response_async.return_value = "'德清妖道初露端倪'"
    name = await service.generate_save_name(ap=5, total_reports=3)
    assert name == "德清妖道初露端倪"

@pytest.mark.asyncio
async def test_generate_save_name_fallback(service, mock_llm):
    mock_llm.get_response_async.side_effect = Exception("API Error")
    name = await service.generate_save_name(ap=5, total_reports=3)
    assert name == "圣踪微巡"

@pytest.mark.asyncio
@patch("internal.application.archive_service.datetime")
async def test_quick_save(mock_datetime, service, mock_persistence, mock_llm):
    mock_llm.get_response_async.return_value = "Test Save Name"
    # Mock datetime to a specific time
    mock_datetime.now.return_value.strftime.return_value = "20260101_120000"

    magistrate = MagicMock()
    suspect = MagicMock()
    letters_system = MagicMock()
    
    mock_report = MagicMock()
    mock_report.id = 1
    mock_report.type = "密折"
    mock_report.content = "Content"
    mock_report.author = "Author"
    mock_report.timestamp = "2026-01-01 12:00:00"
    mock_report.is_returned = False
    mock_report.rescripts = []
    mock_report.raw_case_data = "Raw"
    mock_report.polished_case_data = "Polished"
    
    letters_system.reports = [mock_report]
    
    # We expect True back from save
    mock_persistence.save_game.return_value = True

    result, slot_id = await service.quick_save(
        ap=5,
        letters_system=letters_system,
        agents=[magistrate, suspect]
    )

    assert result is True
    assert slot_id == "20260101_120000"
    mock_persistence.save_game.assert_called_once()
    args, kwargs = mock_persistence.save_game.call_args
    assert args[0] == "20260101_120000"
    assert args[1]["desc"] == "Test Save Name"
    assert len(args[2]) == 1  # 1 letter data

def test_load_game(service, mock_persistence):
    mock_persistence.load_game.return_value = {
        "ap": 3,
        "letters": [{"id": 1, "type": "密折", "content": "Hello", "author": "Mag", "timestamp": "Now"}],
        "agents_memories": {"magistrate": ["Mem1"], "aer": ["Mem2"]}
    }

    magistrate = MagicMock()
    suspect = MagicMock()
    letters_system = MagicMock()
    
    success = service.load_game(
        slot_id="slot_1",
        letters_system=letters_system,
        magistrate=magistrate,
        suspect=suspect
    )
    
    assert success is True
    assert letters_system.reports == [] # ensure clear logic test could be checked
    letters_system.add_report.assert_called_once_with("密折", "Hello", "Mag")
    assert magistrate.memory == ["Mem1"]
    assert suspect.memory == ["Mem2"]
