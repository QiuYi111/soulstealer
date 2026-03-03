from typing import List, Dict, Any
from internal.domain.court import SuspectState

class SuspectAgent:
    """Agent representing the suspect, whose behavior is influenced by physiological state."""
    
    def __init__(self, name: str, soul: str):
        self.name = name
        self.soul = soul

    def _generate_system_prompt(self, state: SuspectState) -> str:
        """Converts physiological state into natural language descriptions for the LLM."""
        pain_desc = ""
        if state.pain <= 30:
            pain_desc = "隐隐作痛"
        elif state.pain <= 70:
            pain_desc = "钻心剜骨"
        else:
            pain_desc = "意识模糊，剧痛让你随时想自杀"

        health_desc = ""
        if state.health >= 80:
            health_desc = "尚能支撑"
        elif state.health >= 30:
            health_desc = "气息奄奄，伤口开始发炎脓肿"
        else:
            health_desc = "命悬一线，随时可能断气"

        thirst_desc = ""
        if state.thirst > 80:
            thirst_desc = "喉咙如火烧，嘴唇干裂出血，你为了喝一口水愿意做任何事"

        physiological_state = (
            f"你当前的状态：\n"
            f"- 疼痛：{pain_desc}\n"
            f"- 健康：{health_desc}\n"
        )
        if thirst_desc:
            physiological_state += f"- 饥渴：{thirst_desc}\n"

        full_prompt = (
            f"【角色设定】\n{self.soul}\n\n"
            f"【生理状态注入】\n{physiological_state}\n\n"
            "请根据你的设定和当前的生理状态，自主决定如何回应审问。你可以选择死扛，也可以选择攀咬他人来减轻痛苦。"
        )
        return full_prompt

    def get_response(self, state: SuspectState, history: List[Dict[str, str]], llm_client: Any) -> str:
        """Gets the suspect's reaction from the LLM."""
        system_prompt = self._generate_system_prompt(state)
        
        # We assume history contains the recent dialogue
        # The first user prompt in history is the interrogator's question
        user_prompt = history[-1]["content"] if history else "..."
        
        return llm_client.generate_response(system_prompt, user_prompt)
