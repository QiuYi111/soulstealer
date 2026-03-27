import os
import json
from datetime import datetime
from typing import List, Any, Optional

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
        
        # Granular Traits: Loaded from trait.json
        self.traits = {}
        
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
                self.name = str(first_line.replace("# ", "").split('：')[-1].split(' (')[0].strip())
        
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

        # Granular Traits
        trait_path = os.path.join(self.agent_dir, "trait.json")
        if os.path.exists(trait_path):
            with open(trait_path, "r", encoding="utf-8") as f:
                self.traits = json.load(f)

    def save_memory(self):
        """Persists L2 memory to memory.json."""
        memory_path = os.path.join(self.agent_dir, "memory.json")
        os.makedirs(self.agent_dir, exist_ok=True)
        with open(memory_path, "w", encoding="utf-8") as f:
            json.dump(self.memory, f, ensure_ascii=False, indent=2)

    def save_traits(self):
        """Persists granular traits to trait.json."""
        trait_path = os.path.join(self.agent_dir, "trait.json")
        os.makedirs(self.agent_dir, exist_ok=True)
        with open(trait_path, "w", encoding="utf-8") as f:
            json.dump(self.traits, f, ensure_ascii=False, indent=2)

    def add_memory(self, content: str):
        """Adds a new autonomous memory entry."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
        self.memory.append({
            "type": "thought",
            "content": content,
            "timestamp": timestamp
        })

    def get_formatted_memory(self) -> str:
        """Returns L2 memory as a formatted string."""
        if not self.memory:
            return "你的记忆中目前没有任何记录。"
        
        lines = ["【过往记忆记录 (L2 Memory)】"]
        for entry in self.memory:
            lines.append(f"- [{entry.get('timestamp', '未知时间')}] {entry.get('content', '')}")
        return "\n".join(lines)


    def generate_prompt(self, scene_context: str, scene_instructions: str, available_tools: Optional[List[str]] = None, returned_memorials: Optional[str] = None) -> str:
        """
        Synthesizes a system prompt by decoupling Identity (Soul) from Scene (Environment).
        
        :param scene_context: The immediate situation (e.g., 'You are in the court log, bleeding').
        :param scene_instructions: How the agent should behave in this scene (e.g., 'You are a suspect, try to survive').
        :param available_tools: Specific API commands allowed in this scene.
        :param returned_memorials: Optional external context of memorials returned with imperial rescripts.
        """
        tools_str = "\n".join([f"- {tool}" for tool in available_tools]) if available_tools else "无可用指令。"

        # Identity Section (The Soul)
        identity_prompt = (
            f"【核心身份 (Identity)】\n"
            f"你即是：{str(self.name)}。\n"
            "以下是你的个人传记与灵魂深度定义 (Soul.md)，它决定了你的世界观、语言风格和潜在动机：\n"
            f"{self.soul_content}\n"
        )

        # Scene Section (The Vessel/Environment)
        returned_context = f"\n【奉旨批回奏折 (Returned Memorials with Rescripts)】\n{returned_memorials}\n" if returned_memorials else ""
        scene_prompt = (
            f"【当前环境 (Scene Context)】\n{str(scene_context)}\n"
            f"{returned_context}\n"
            f"【行为准则 (Instructions)】\n{scene_instructions}\n"
        )

        # Output Format Section (The Constraint)
        format_prompt = (
            "【输出格式规范 (Output Format)】\n"
            "1. **禁止文学化描述**：严禁输出任何关于心理活动、神态描写、环境渲染或第三人称动作描述（如：“他深吸一口气”、“眼神中透露出忧虑”）。\n"
            "2. **仅限动作与对话**：你的输出应仅包含你作为角色的直接言语（对话）或系统允许的指令。如需表达情感或态度，请通过对话内容或具体的法律/行政动作体现。\n"
            "3. **防止上下文污染**：保持输出精炼，直接进入主题。**严禁虚构或传唤任何未在‘当前环境’中明确列出的角色。** 你的交互对象仅限于当前场景中存在的实体。\n"
        )

        # Resources & Tools
        recent_memories = self.memory[-5:]
        memory_str = "\n".join([f"- [{m.get('timestamp', '未知')}] {m.get('content')}" for m in recent_memories]) if recent_memories else "（无近期记忆）"
        
        resource_prompt = (
            "【可用资源库】\n"
            f"你的近期部分记忆 (L2 Memory - Recent / memory.json):\n{memory_str}\n\n"
            f"你的极细粒度特征 (L1 Traits - trait.json):\n{json.dumps(self.traits, ensure_ascii=False, indent=2)}\n\n"
            "- L3 (Relationships): 你的社会关系网 (relationships.json)\n"
        )

        if available_tools:
            tools_str = "\n".join([f"- {tool}" for tool in available_tools])
            resource_prompt += (
                f"\n【系统 API 指令 (System API Commands)】\n"
                f"如需执行指令，**必须**将其包裹在双中括号内，格式为：`[[/指令名称 参数1 参数2 ...]]`。\n"
                f"指令可以出现在你回复的任何位置（开头、中间或结尾）。\n"
                f"例如：`看来不加点刑具是不行了。[[/torture 夹棍 还不招来？]]` 或 `[[/read_memory]] 容我再想想。`\n\n"
                f"当前可用指令：\n"
                f"{tools_str}\n"
                f"- /update_memory [内容]：自主记录洞察。可以多次调用或与其他指令并列。\n\n"
                f"如果你调用了指令，请等待系统返回结果后再继续。如果你已有足够信息做出符合身份的反应，请直接回答。"
            )
        else:
            resource_prompt += "\n（当前环境下无可用 API 指令，请直接根据提示要求进行内容输出。）"

        return f"{identity_prompt}\n{scene_prompt}\n{format_prompt}\n{resource_prompt}"

    def get_response(self, llm_client: Any, system_prompt: str, user_prompt: str, model: str = None) -> str:
        """Call LLM with the synthesized prompts."""
        return llm_client.generate_response(system_prompt, user_prompt, model=model)
