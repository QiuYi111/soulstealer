from unittest.mock import MagicMock
from internal.domain.agent import Agent

def test_agent_generate_prompt_with_rescripts():
    # Setup agent
    agent = Agent("agents/magistrate")
    agent.name = "阮呈麟"
    agent.soul_content = "我是知县。"
    
    scene_ctx = "公堂之上。"
    scene_inst = "审案。"
    returned_memorials = "《奏折 ID:1》朱批：速办！"
    
    prompt = agent.generate_prompt(scene_ctx, scene_inst, returned_memorials=returned_memorials)
    
    assert "奉旨批回奏折 (Returned Memorials with Rescripts)" in prompt
    assert "速办！" in prompt
    assert "阮呈麟" in prompt

def test_court_session_passes_rescripts():
    from internal.domain.court import CourtSession
    
    mock_official = MagicMock()
    mock_suspect = MagicMock()
    mock_llm = MagicMock()
    
    session = CourtSession("知县", "阿二")
    returned_memorials = "圣旨：严查！"
    
    # We want to see if run_auto_step calls generate_prompt with returned_memorials
    session.run_auto_step(mock_official, mock_suspect, mock_llm, "model", returned_memorials=returned_memorials)
    
    # Check the call to generate_prompt for the official agent
    # official_agent.generate_prompt(scene_ctx_off, scene_inst_off, ["/torture", "/read_memory"], returned_memorials=returned_memorials)
    args, kwargs = mock_official.generate_prompt.call_args
    assert kwargs['returned_memorials'] == returned_memorials
