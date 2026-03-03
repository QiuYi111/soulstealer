from dataclasses import dataclass
from typing import List, Dict

@dataclass
class SuspectState:
    health: int = 100
    pain: int = 0
    thirst: int = 0
    hunger: int = 0

class CourtSession:
    """Manages the domain logic for a single court session (Interrogation)."""
    def __init__(self, interrogator_name: str, suspect_name: str):
        self.interrogator = interrogator_name
        self.suspect = suspect_name
        self.state = SuspectState()
        self.log: List[Dict[str, str]] = []
        self.full_history: List[Dict[str, str]] = []
    
    def apply_torture(self, tool: str, question: str) -> str:
        """Applies torture, mutates physical state, and registers to contextual log."""
        if tool == "夹棍":
            self.state.pain += 30
            self.state.health -= 10
        elif tool == "掌嘴":
            self.state.pain += 10
            self.state.health -= 2
        elif tool == "不给水":
            self.state.thirst += 40
        else:
            # Standard questioning, minimal pain increase
            self.state.pain += 2
            
        action_desc = f"用刑 [{tool}]。当前嫌犯疼痛值: {self.state.pain}, 健康值: {self.state.health}。"
        self.log.append({"role": "system", "content": action_desc})
        self.log.append({"role": "interrogator", "content": question})
        self.full_history.append({"role": "user", "content": f"（审问官 {self.interrogator}：）{question}"})
        return action_desc

    def add_suspect_response(self, content: str):
        self.log.append({"role": "suspect", "content": content})
        self.full_history.append({"role": "assistant", "content": content})
