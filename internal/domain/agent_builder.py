import os
import json
from typing import Dict, Any, Optional
from internal.rag.retriever import SoulstealerRetriever

class AgentBuilder:
    """Builder for instantiating Agents based on historical RAG context."""

    def __init__(self, retriever: SoulstealerRetriever, llm_client: Any, model: str = "deepseek-chat"):
        self.retriever = retriever
        self.llm_client = llm_client
        self.model = model

    def build_agent(self, agent_dir: str, name: str, profile_request: str) -> bool:
        """
        Builds a new agent directory with Soul.md and trait.json.
        
        Args:
            agent_dir: Directory where agent files will be saved.
            name: Name of the agent.
            profile_request: Description of who this person should be (e.g., "A beggar from Deqing").
        """
        os.makedirs(agent_dir, exist_ok=True)
        
        # 1. Retrieve Historical Context
        print(f"Retrieving context for: {profile_request}...")
        context_docs = self.retriever.query(profile_request, top_k=5)
        context_str = "\n\n".join([
            f"--- 史料来源: {doc['metadata'].get('source', '未知')} ---\n{doc['content']}" 
            for doc in context_docs
        ])
        
        # 2. Construct LLM Prompt
        system_prompt = (
            "你是一位精通清史、《叫魂》案背景及社会学的模拟专家。\n"
            "你的任务是为一个名为《叫魂》的历史社会学模拟系统生成一个‘活生生’的角色身份。\n"
            "生成的角色必须极具历史感，符合乾隆三十三年的社会背景，且其生平、口音、物理特征应与史料逻辑紧密结合。\n\n"
            "【输出要求】\n"
            "你必须严格遵循以下格式输出，不要包含任何额外的 Markdown 代码块外壳（如 ```json 等）：\n"
            "1. 将 Soul.md 的内容包裹在 <SOUL_MD> 标签中。\n"
            "2. 将 trait.json 的内容（纯 JSON 对象）包裹在 <TRAIT_JSON> 标签中。\n\n"
            "【禁止事项】\n"
            "- 禁止生成现代化的描述。\n"
            "- 严禁虚构与当前提供的史料上下文完全冲突的大规模历史事件。\n"
            "- <TRAIT_JSON> 标签内必须是合法的 JSON，禁止使用任何形式的格式标记。"
        )
        
        user_prompt = (
            f"目标角色要求：{profile_request}\n"
            f"角色姓名建议：{name}\n\n"
            f"【参考史料上下文 (RAG Context)】\n"
            f"{context_str}\n\n"
            "请基于以上信息，生成角色的 Soul.md 和 trait.json 内容。"
        )
        
        # 3. Call LLM
        print("Calling LLM for agent generation...")
        response = self.llm_client.generate_response(system_prompt, user_prompt, model=self.model)
        
        soul_md = self._extract_tag_content(response, "SOUL_MD")
        trait_json_str = self._extract_tag_content(response, "TRAIT_JSON")

        if not soul_md or not trait_json_str:
            print(f"Error: Missing required tags in LLM output. Response preview: {response[:200]}...")
            return False
        
        # 4. Save Files
        try:
            # Save Soul.md
            with open(os.path.join(agent_dir, "Soul.md"), "w", encoding="utf-8") as f:
                f.write(soul_md.strip())
            
            # Robust JSON extraction
            trait_data = self._extract_json(trait_json_str)
            if trait_data is None:
                print(f"Failed to parse trait JSON. Raw string: {trait_json_str[:200]}...")
                return False

            with open(os.path.join(agent_dir, "trait.json"), "w", encoding="utf-8") as f:
                json.dump(trait_data, f, ensure_ascii=False, indent=2)
                
            # Create an empty memory.json
            with open(os.path.join(agent_dir, "memory.json"), "w", encoding="utf-8") as f:
                json.dump([], f)
                
            print(f"Successfully instantiated agent at: {agent_dir}")
            return True
        except Exception as e:
            print(f"Failed to save agent files: {e}")
            return False

    def _extract_tag_content(self, text: str, tag: str) -> Optional[str]:
        """Extracts content between XML-like tags."""
        start_tag = f"<{tag}>"
        end_tag = f"</{tag}>"
        start_idx = text.find(start_tag)
        end_idx = text.find(end_tag)
        
        if start_idx != -1 and end_idx != -1:
            return text[start_idx + len(start_tag):end_idx].strip()
        return None

    def _extract_json(self, text: str) -> Optional[Dict[str, Any]]:
        """Extracts JSON object from text that might contain markdown blocks."""
        text = text.strip()
        # Remove markdown code fences if present
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()
            
        # Find first '{' and last '}'
        start = text.find('{')
        end = text.rfind('}')
        if start != -1 and end != -1:
            json_str = text[start:end+1]
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                return None
        return None
