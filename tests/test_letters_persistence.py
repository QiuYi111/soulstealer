import os
import json
from internal.domain.letters import LettersSystem

def test_letters_save_and_load(tmp_path):
    file_path = tmp_path / "test_reports.json"
    system = LettersSystem()
    
    # Add a report
    system.add_report("密折", "这是秘密内容", "德清县令")
    system.save_to_file(str(file_path))
    
    # Check if file exists and content is correct
    assert os.path.exists(file_path)
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        assert len(data) == 1
        assert data[0]["type"] == "密折"
        assert data[0]["author"] == "德清县令"

    # Load into a new system
    new_system = LettersSystem()
    new_system.load_from_file(str(file_path))
    
    assert len(new_system.reports) == 1
    assert new_system.reports[0].content == "这是秘密内容"
    assert new_system.reports[0].id == 1
    assert new_system._next_id == 2

def test_letters_load_non_existent():
    system = LettersSystem()
    system.load_from_file("non_existent.json")
    assert len(system.reports) == 0
