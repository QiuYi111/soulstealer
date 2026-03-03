from unittest.mock import MagicMock
from internal.domain.agent import SuspectAgent
from internal.domain.court import SuspectState

def test_suspect_agent_prompt_generation():
    soul = "你是一个胆小的乞丐，名叫阿二。"
    agent = SuspectAgent(name="阿二", soul=soul)
    
    state = SuspectState(pain=50, health=80)
    prompt = agent._generate_system_prompt(state)
    
    assert soul in prompt
    assert "钻心剜骨" in prompt or "剧痛" in prompt # Adjust based on implementation
    assert "阿二" in prompt

def test_suspect_agent_response_mock():
    llm_client = MagicMock()
    llm_client.generate_response.return_value = "小的小的招了..."
    
    agent = SuspectAgent(name="阿二", soul="...")
    state = SuspectState()
    history = [{"role": "interrogator", "content": "快说！"}]
    
    response = agent.get_response(state, history, llm_client)
    
    assert response == "小的小的招了..."
    llm_client.generate_response.assert_called_once()
