import os
import json
from typing import List, Dict, Any, Optional

class Agent:
    """Unified Agent class implementing the Three-Level Cache structure."""
    
    def __init__(self, agent_dir: str):
        self.agent_dir = agent_dir
        self.name = ""
        
        # L1: Soul (Permanent) - Loaded from Soul.md
        self.soul_content = ""
        
        # L2: Memory (Short-term/Intermediate) - Loaded from memory.json
        self.memory = []
        
        # L3: Relationships/External Context - Loaded from relationships.json
        self.relationships = {}
        
        self._load_data()

    def _load_data(self):
        """Loads L1, L2, and L3 data from the agent directory."""
        # L1: Soul
        soul_path = os.path.join(self.agent_dir, "Soul.md")
        if os.path.exists(soul_path):
            with open(soul_path, "r", encoding="utf-8") as f:
                self.soul_content = f.read()
            # Extract name from first line if it's a markdown header
            first_line = self.soul_content.split('\n')[0]
            if first_line.startswith("# "):
                self.name = first_line.replace("# ", "").split('：')[-1].split(' (')[0].strip()
        
        # L2: Memory
        memory_path = os.path.join(self.agent_dir, "memory.json")
        if os.path.exists(memory_path):
            with open(memory_path, "r", encoding="utf-8") as f:
                self.memory = json.load(f)
                
        # L3: Relationships
        rel_path = os.path.join(self.agent_dir, "relationships.json")
        if os.path.exists(rel_path):
            with open(rel_path, "r", encoding="utf-8") as f:
                self.relationships = json.load(f)

    def generate_prompt(self, current_task: str, context: Optional[str] = None, available_tools: Optional[List[str]] = None) -> str:
        """
        Synthesizes a system prompt that encourages selective resource retrieval.
        """
        tools_str = ""
        if available_tools:
            tools_str = "\n".join([f"- {tool}" for tool in available_tools])
        else:
            tools_str = "无可用指令。"

        prompt = (
            f"【角色灵魂 (L1 常驻)】\n{self.soul_content}\n\n"
            "【可用资源库】\n"
            "- L2: 个人记忆 (memory.json)\n"
            "- L3: 社会关系 (relationships.json)\n\n"
            "【系统 API 指令】\n"
            "如果你需要获取更多信息或执行操作，请在回复的最开始直接输入指令（如：/read_memory）。\n"
            f"{tools_str}\n\n"
            "【当前情境与任务】\n"
            f"{current_task}\n"
        )
        if context:
            prompt += f"\n【实时信息】\n{context}\n"
            
        prompt += "\n如果你已有足够信息，请直接以角色身份做出回应。如果你调用了指令，请等待系统返回结果。"
        return prompt

    def get_response(self, llm_client: Any, system_prompt: str, user_prompt: str, model: str = None) -> str:
        """Call LLM with the synthesized prompts."""
        return llm_client.generate_response(system_prompt, user_prompt, model=model)
