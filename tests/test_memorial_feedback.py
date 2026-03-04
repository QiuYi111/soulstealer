import os
import json
from internal.domain.letters import LettersSystem, Rescript
from internal.domain.agent import Agent

def test_memorial_comment_persistence(tmp_path):
    # Setup paths
    letters_file = tmp_path / "letters.json"
    agent_dir = tmp_path / "test_agent"
    os.makedirs(agent_dir, exist_ok=True)
    
    # Initialize systems
    letters_system = LettersSystem()
    report = letters_system.add_report("密折", "汇报内容", "德清县令")
    
    # Add rescript
    comment_text = "继续彻查，不得玩忽职守！"
    rescript = Rescript(content=comment_text, row=0, col=0, timestamp="2026-03-04 00:00:00")
    report.rescripts = [rescript]
    letters_system.save_to_file(str(letters_file))
    
    # Verify letters persistence
    new_letters = LettersSystem()
    new_letters.load_from_file(str(letters_file))
    assert len(new_letters.reports) == 1
    assert new_letters.reports[0].rescripts[0].content == comment_text

def test_agent_memory_persistence(tmp_path):
    agent_dir = tmp_path / "test_agent"
    os.makedirs(agent_dir, exist_ok=True)
    
    # Initialize agent
    agent = Agent(str(agent_dir))
    
    # Add memory and save
    memory_entry = {"type": "rescript", "content": "朱批内容", "timestamp": "2026-03-04"}
    agent.memory.append(memory_entry)
    agent.save_memory()
    
    # Verify persistence
    memory_file = agent_dir / "memory.json"
    assert os.path.exists(memory_file)
    with open(memory_file, "r", encoding="utf-8") as f:
        data = json.load(f)
        assert len(data) == 1
        assert data[0]["content"] == "朱批内容"
    
    # Load back in new agent
    new_agent = Agent(str(agent_dir))
    assert len(new_agent.memory) == 1
    assert new_agent.memory[0]["content"] == "朱批内容"
