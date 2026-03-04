import pytest
import os
import hydra
from omegaconf import DictConfig
from internal.domain.court import CourtSession
from internal.domain.agent import Agent
from internal.domain.letters import LettersSystem
from internal.infrastructure.llm import LLMClient

@pytest.fixture
def cfg():
    """Load configuration via Hydra."""
    # Ensure we use the actual config file
    with hydra.initialize(version_base="1.3", config_path="../conf"):
        return hydra.compose(config_name="config")

def test_real_llm_full_flow(cfg: DictConfig):
    """
    Perform a real end-to-end integration test using the configured LLM.
    This test verifies that:
    1. LLM connectivity is operational.
    2. Agent prompts are correctly handled by the real model.
    3. The domain state transitions correctly based on real LLM output.
    """
    # 1. Setup Infrastructure from Config
    api_key = cfg.llm.get("api_key", "test_key")
    base_url = cfg.llm.get("base_url", "https://api.test")
    model = cfg.llm.get("model", "test_model")
    
    llm_client = LLMClient(api_key=api_key, base_url=base_url)

    # 2. Setup Domain
    session = CourtSession("德清县令", "阿二")
    suspect = Agent("agents/aer")
    official = Agent("agents/magistrate")
    letters = LettersSystem()

    # 3. Step 1: Interrogation with Real LLM
    print(f"\n[Step 1] Interrogating with model: {model}...")
    session.apply_torture("夹棍", "实说！你为何在德清县城行踪诡秘？")
    
    current_task = "你正在公堂之上接受县令的严厉审问。"
    phys_context = "你处于剧烈的疼痛中。"
    available_tools = ["/read_memory", "/read_relationships"]
    system_prompt = suspect.generate_prompt(current_task, phys_context, available_tools)
    user_prompt = session.full_history[-1]["content"] if session.full_history else "..."
    
    response = suspect.get_response(llm_client, system_prompt, user_prompt, model=model)
    session.add_suspect_response(response)

    print(f"[Suspect AI]: {response}")
    assert response and len(response) > 5
    assert session.state.pain >= 30

    # 4. Step 2: Drafting Report with Real LLM
    print("[Step 2] Drafting report...")
    current_task_official = "请根据审讯记录撰写密折。"
    log_text = "\n".join([f"{entry['role']}: {entry['content']}" for entry in session.log])
    system_prompt_official = official.generate_prompt(current_task_official, "请完成公文撰写。")
    user_prompt_official = f"以下是审讯记录：\n{log_text}"
    
    report_content = official.get_response(llm_client, system_prompt_official, user_prompt_official, model=model)
    letters.add_report("密折", report_content, official.name)

    print(f"[Official AI Report]:\n{report_content}")
    assert "奏" in report_content or "臣" in report_content or len(report_content) > 20

    # 5. Step 3: Persistence Check
    temp_file = "real_integration_test_reports.json"
    letters.save_to_file(temp_file)
    
    assert os.path.exists(temp_file)
    new_letters = LettersSystem()
    new_letters.load_from_file(temp_file)
    assert len(new_letters.reports) == 1
    
    if os.path.exists(temp_file):
        os.remove(temp_file)
    
    print("[Integration Test] Full flow completed successfully.")
