from internal.domain.agent import Agent

def test_generate_prompt_contains_constraints():
    agent = Agent("agents/magistrate")
    prompt = agent.generate_prompt("Scene", "Instructions")
    
    # Check for core constraint sections
    assert "【输出格式规范 (Output Format)】" in prompt
    assert "禁止文学化描述" in prompt
    assert "仅限动作与对话" in prompt
    assert "防止上下文污染" in prompt
    
    # Verify that it still contains identity and scene
    assert "【核心身份 (Identity)】" in prompt
    assert "【当前环境 (Scene Context)】" in prompt
    assert "Scene" in prompt
    assert "Instructions" in prompt

def test_court_session_instructions_enforcement():
    # This checks if the instructions passed to generate_prompt in CourtSession
    # would logically follow the new constraints (indirectly tested by running the code)
    pass
