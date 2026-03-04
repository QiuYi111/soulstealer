from unittest.mock import MagicMock
from internal.domain.court import CourtSession
from internal.domain.agent import Agent

def test_magistrate_receives_prisoner_registry():
    official = MagicMock(spec=Agent)
    official.name = "知县"
    official.get_response.return_value = "既然名册上只有你，李阿二，那你就招了吧！"
    
    suspect = MagicMock(spec=Agent)
    suspect.name = "李阿二"
    
    llm = MagicMock()
    
    prisoner_list = ["李阿二"]
    session = CourtSession("知县", "李阿二", prisoner_list=prisoner_list)
    
    # Run one step
    session.run_auto_step(official, suspect, llm, "model")
    
    # Check that generate_prompt was called with the registry in scene_context
    args, kwargs = official.generate_prompt.call_args
    scene_context = args[0]
    
    assert "【在押名册 (Prisoner Registry)】：李阿二" in scene_context
    assert "重要提示：当前堂上仅有 李阿二 在场受审" in scene_context

def test_anti_hallucination_instruction():
    agent = Agent("agents/magistrate")
    prompt = agent.generate_prompt("Context", "Instructions")
    
    assert "严禁虚构或传唤任何未在‘当前环境’中明确列出的角色" in prompt
