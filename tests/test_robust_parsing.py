import json
from unittest.mock import MagicMock
from internal.domain.court import CourtSession
from internal.domain.agent import Agent

def test_parse_commands_helper():
    session = CourtSession("知县", "李阿二")
    
    # Case 1: Command at start
    text1 = "[[/read_memory]] 容我想想。"
    cleaned1, cmds1 = session._parse_commands(text1)
    assert cleaned1 == "容我想想。"
    assert len(cmds1) == 1
    assert cmds1[0][1] == "/read_memory"
    
    # Case 2: Command in middle
    text2 = "既然你如此说，[[/update_memory 嫌犯供词有诈]] 那我就不客气了。"
    cleaned2, cmds2 = session._parse_commands(text2)
    assert cleaned2 == "既然你如此说， 那我就不客气了。"
    assert len(cmds2) == 1
    assert cmds2[0][1] == "/update_memory"
    assert cmds2[0][2] == "嫌犯供词有诈"
    
    # Case 3: Command at end
    text3 = "拉下去，用刑！[[/torture 夹棍 还不快说？]]"
    cleaned3, cmds3 = session._parse_commands(text3)
    assert cleaned3 == "拉下去，用刑！"
    assert len(cmds3) == 1
    assert cmds3[0][1] == "/torture"
    assert cmds3[0][2] == "夹棍 还不快说？"
    
    # Case 4: Multiple commands
    text4 = "[[/update_memory 发现新线索]] 看来此事不简单。[[/read_memory]]"
    cleaned4, cmds4 = session._parse_commands(text4)
    assert cleaned4 == "看来此事不简单。"
    assert len(cmds4) == 2
    assert cmds4[0][1] == "/update_memory"
    assert cmds4[1][1] == "/read_memory"

def test_run_auto_step_with_embedded_command():
    official = MagicMock(spec=Agent)
    official.name = "知县"
    official.get_formatted_memory.return_value = "Memory content."
    
    suspect = MagicMock(spec=Agent)
    suspect.name = "李阿二"
    
    llm = MagicMock()
    # Official returns a command at the end of text
    official.get_response.return_value = "你这刁民，还不从实招来？[[/torture 赞指 到底是谁指使的？]]"
    suspect.get_response.return_value = "小的冤枉啊！"
    
    session = CourtSession("知县", "李阿二")
    # Instead of full mock, we use a real session but monitor apply_torture
    original_apply = session.apply_torture
    session.apply_torture = MagicMock(side_effect=original_apply)
    
    session.run_auto_step(official, suspect, llm, "model")
    
    # Verify apply_torture was called with '赞指' and '到底是谁指使的？'
    session.apply_torture.assert_called_with("赞指", "到底是谁指使的？")
    
    # Verify suspect received the correct context
    args, kwargs = suspect.get_response.call_args
    user_sus = args[2]
    assert "审问官施加了：" in user_sus
    assert "到底是谁指使的？" in user_sus
