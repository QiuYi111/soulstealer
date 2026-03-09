from unittest.mock import MagicMock
from internal.domain.court import CourtSession
from internal.domain.agent import Agent

def test_read_memory_tool_execution():
    # Setup agents
    official = MagicMock(spec=Agent)
    official.name = "知县"
    official.get_formatted_memory.return_value = "记忆：嫌犯有同伙。"
    
    suspect = MagicMock(spec=Agent)
    suspect.name = "阿二"
    suspect.get_formatted_memory.return_value = "记忆：我是冤枉的。"
    
    llm = MagicMock()
    # First call returns /read_memory, second returns the actual action
    official.get_response.side_effect = ["/read_memory", "既然你有同伙，还不招来？"]
    suspect.get_response.side_effect = ["/read_memory", "草民真的没有同伙！"]
    
    session = CourtSession("知县", "阿二")
    
    # Run one step
    session.run_auto_step(official, suspect, llm, "model")
    
    # Verify official tool handling
    # get_response should be called twice for each agent
    assert official.get_response.call_count == 2
    # Second call should include memory data in the user prompt
    args, kwargs = official.get_response.call_args
    assert "记忆：嫌犯有同伙。" in args[2] # user_prompt is the 3rd positional arg
    
    # Verify suspect tool handling
    assert suspect.get_response.call_count == 2
    args_sus, kwargs_sus = suspect.get_response.call_args
    assert "记忆：我是冤枉的。" in args_sus[2]
