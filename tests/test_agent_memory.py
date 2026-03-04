import json
from unittest.mock import MagicMock
from internal.domain.agent import Agent
from internal.domain.court import CourtSession

def test_agent_add_memory_and_persistence(tmp_path):
    # Setup a temp agent directory
    agent_dir = tmp_path / "test_agent"
    agent_dir.mkdir()
    memory_file = agent_dir / "memory.json"
    memory_file.write_text("[]")
    
    agent = Agent(str(agent_dir))
    agent.add_memory("测试记忆内容")
    agent.save_memory()
    
    # Verify memory list
    assert len(agent.memory) == 1
    assert agent.memory[0]["content"] == "测试记忆内容"
    assert agent.memory[0]["type"] == "thought"
    
    # Verify file persistence
    with open(memory_file, "r", encoding="utf-8") as f:
        data = json.load(f)
        assert len(data) == 1
        assert data[0]["content"] == "测试记忆内容"

def test_court_session_handles_memory_command(tmp_path):
    # Setup agents
    off_dir = tmp_path / "magistrate"
    off_dir.mkdir()
    (off_dir / "memory.json").write_text("[]")
    (off_dir / "Soul.md").write_text("# 县令")
    
    sus_dir = tmp_path / "suspect"
    sus_dir.mkdir()
    (sus_dir / "memory.json").write_text("[]")
    (sus_dir / "Soul.md").write_text("# 嫌犯")
    
    off_agent = Agent(str(off_dir))
    sus_agent = Agent(str(sus_dir))
    
    session = CourtSession("县令", "嫌犯")
    
    # Mock LLM response with /update_memory command
    llm = MagicMock()
    # 1st call for official: memory command + question
    # 2nd call for suspect: just response
    llm.generate_response.side_effect = [
        "/update_memory 发现嫌犯神情可疑。\n你到底是何人？",
        "小的是冤枉的。"
    ]
    
    session.run_auto_step(off_agent, sus_agent, llm, model="test-model")
    
    # Verify merchant's memory updated
    assert len(off_agent.memory) == 1
    assert off_agent.memory[0]["content"] == "发现嫌犯神情可疑。"
    
    # Verify file persisted
    with open(off_dir / "memory.json", "r", encoding="utf-8") as f:
        data = json.load(f)
        assert len(data) == 1
        assert data[0]["content"] == "发现嫌犯神情可疑。"
        
    # Verify court log contains the question part, not the command
    assert "你到底是何人？" in session.log[1]["content"]
    assert "/update_memory" not in session.log[1]["content"]
