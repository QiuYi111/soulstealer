from internal.domain.agent import Agent

def test_agent_auto_memory_injection():
    agent = Agent("agents/magistrate")
    agent.memory = [
        {"timestamp": "2026-01-01 10:00:00", "content": "Memory 1"},
        {"timestamp": "2026-01-01 10:01:00", "content": "Memory 2"},
        {"timestamp": "2026-01-01 10:02:00", "content": "Memory 3"},
        {"timestamp": "2026-01-01 10:03:00", "content": "Memory 4"},
        {"timestamp": "2026-01-01 10:04:00", "content": "Memory 5"},
        {"timestamp": "2026-01-01 10:05:00", "content": "Memory 6"},
    ]
    
    prompt = agent.generate_prompt("Context", "Instructions")
    
    # Check that only the last 5 memories are included
    assert "Memory 6" in prompt
    assert "Memory 5" in prompt
    assert "Memory 4" in prompt
    assert "Memory 3" in prompt
    assert "Memory 2" in prompt
    assert "Memory 1" not in prompt
    
    assert "你的近期部分记忆 (L2 Memory - Recent)" in prompt

def test_agent_no_memory_injection():
    agent = Agent("agents/magistrate")
    agent.memory = []
    
    prompt = agent.generate_prompt("Context", "Instructions")
    
    assert "（无近期记忆）" in prompt
