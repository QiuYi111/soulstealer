from unittest.mock import MagicMock
from internal.domain.agent import Agent
from internal.domain.court import SuspectState

def test_agent_prompt_generation():
    # Use existing agent dir for aer
    agent = Agent("agents/aer")
    
    SuspectState(pain=50, health=80)
    # Replicate the TUI logic for context
    phys_context = "疼痛：钻心剜骨, 健康：尚能支撑"
    available_tools = ["/read_memory", "/read_relationships"]
    prompt = agent.generate_prompt("你正在受审", phys_context, available_tools)
    
    assert "阿二" in agent.soul_content
    assert "阿二" in prompt
    assert "钻心剜骨" in prompt
    assert "memory.json" in prompt # Resource mention
    assert "/read_memory" in prompt # Tool mention

def test_agent_response_mock():
    llm_client = MagicMock()
    llm_client.generate_response.return_value = "小的小的招了..."
    
    agent = Agent("agents/aer")
    system_prompt = agent.generate_prompt("任务", "请回答审问。", available_tools=["/cmd"])
    user_prompt = "快说！"
    
    response = agent.get_response(llm_client, system_prompt, user_prompt)
    
    assert response == "小的小的招了..."
    llm_client.generate_response.assert_called_once_with(system_prompt, user_prompt, model=None)
