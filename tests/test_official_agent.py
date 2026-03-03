from unittest.mock import MagicMock
from internal.domain.agent import Agent

def test_agent_draft_report_logic():
    llm_client = MagicMock()
    llm_client.generate_response.return_value = "这是润色后的汇报内容。"
    
    agent = Agent("agents/magistrate")
    
    session_log = [
        {"role": "system", "content": "用刑 [夹棍]"},
        {"role": "interrogator", "content": "谁指使你的？"},
        {"role": "suspect", "content": "是德清书院的张三！"}
    ]
    log_text = "\n".join([f"{entry['role']}: {entry['content']}" for entry in session_log])
    
    current_task = "请根据审讯记录撰写明发奏折。"
    system_prompt = agent.generate_prompt(current_task)
    user_prompt = f"以下是审讯记录：\n{log_text}"
    
    # Test report generation
    report = agent.get_response(llm_client, system_prompt, user_prompt)
    assert "润色" in report
    llm_client.generate_response.assert_called_once_with(system_prompt, user_prompt, model=None)
    
    # Verify contents
    assert "德清县令" in agent.soul_content
    assert "L1" in system_prompt
    assert "张三" in user_prompt
