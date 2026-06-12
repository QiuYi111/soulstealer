import pytest
from unittest.mock import MagicMock, patch
from internal.application.game_session_service import GameSessionService
from internal.domain.letters import LettersSystem
from internal.domain.cases import CasesSystem

@pytest.fixture
def mock_llm():
    return MagicMock()

@pytest.fixture
def mock_magistrate():
    agent = MagicMock()
    agent.name = "Magistrate"
    return agent

@pytest.fixture
def mock_suspect():
    agent = MagicMock()
    agent.name = "Suspect"
    return agent

@pytest.fixture
def service(mock_llm, mock_magistrate, mock_suspect):
    letters = LettersSystem()
    cases = CasesSystem()
    return GameSessionService(
        llm=mock_llm,
        llm_model="test-model",
        letters_system=letters,
        cases_system=cases,
        magistrate=mock_magistrate,
        suspect=mock_suspect
    )

def test_initialization(service, mock_magistrate, mock_suspect):
    assert service.magistrate == mock_magistrate
    assert service.suspect == mock_suspect
    assert service.letters_system is not None
    assert service.cases_system is not None
    assert service.current_session is None

@pytest.mark.asyncio
async def test_run_simulation_sequence(service):
    # Mock CourtSession and its interactions
    with patch("internal.application.game_session_service.CourtSession") as mock_court_class:
        mock_session = MagicMock()
        mock_court_class.return_value = mock_session
        
        # Simulate 2 successful steps then stop
        # In reality, run_auto_step returns True if dialogue continues
        mock_session.run_auto_step.side_effect = [True, False]
        mock_session.log = [
            {"role": "system", "content": "Started"},
            {"role": "user", "content": "Question"},
            {"role": "assistant", "content": "Answer"}
        ]
        mock_session.get_raw_log.return_value = "Raw Log"
        mock_session.location_info = {"province": "A", "prefecture": "B", "county": "C"}
        
        # We also need to mock parsing inside current_session for update_memory
        mock_session._parse_commands.return_value = (None, [("full", "/update_memory", "Summary")])

        # Mock the agents' get_response (which we'll call inside to_thread)
        # 1. Summary
        # 2. Polished case
        # 3. Draft memorial
        service.magistrate.get_response.side_effect = [
            "Summary Response", 
            "Polished Case",
            "密折\nHere is the report"
        ]
        
        events = []
        async for event in service.run_simulation_sequence():
            events.append(event)
            
        assert len(events) > 0
        
        # Ensure the log event was yielded
        log_events = [e for e in events if e["type"] == "log"]
        assert len(log_events) >= 1
        
        # Ensure a report event was generated
        report_events = [e for e in events if e["type"] == "report"]
        assert len(report_events) == 1
        assert report_events[0]["report_type"] == "密折"
        
        # Ensure memory update was called
        service.magistrate.add_memory.assert_called_with("Summary")
        service.magistrate.save_memory.assert_called()
        
        # Ensure case was saved
        # LettersSystem should have the new report
        assert len(service.letters_system.reports) == 1
        report = service.letters_system.reports[0]
        assert report.type == "密折"
        assert report.content == "Here is the report"
        assert report.raw_case_data == "Raw Log"
        assert report.polished_case_data == "Polished Case"
