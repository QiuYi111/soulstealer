import os
import json
import shutil
from datetime import datetime
from typing import List, Dict, Any, Optional

class PersistenceManager:
    """Handles the serialization and deserialization of the game state."""
    
    def __init__(self, base_save_dir: str = "saves"):
        self.base_save_dir = base_save_dir
        os.makedirs(self.base_save_dir, exist_ok=True)

    def _get_slot_dir(self, slot_id: str) -> str:
        return os.path.join(self.base_save_dir, f"slot_{slot_id}")

    def save_game(self, slot_id: str, metadata: Dict[str, Any], letters_data: List[Dict[str, Any]], 
                  cases_dir: str, agents: List[Any], ap: int) -> bool:
        """
        Saves the current game state to a slot.
        :param slot_id: Unique identifier for the save slot.
        :param metadata: Game metadata (e.g., timestamp, player name).
        :param letters_data: Raw data from LettersSystem.
        :param cases_dir: Path to the directory containing case files.
        :param agents: List of Agent objects to save memory from.
        :param ap: Current action points.
        """
        slot_dir = self._get_slot_dir(slot_id)
        os.makedirs(slot_dir, exist_ok=True)
        
        # 1. Save Metadata & AP
        state = {
            "metadata": metadata,
            "ap": ap,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        with open(os.path.join(slot_dir, "state.json"), "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
            
        # 2. Save Letters
        with open(os.path.join(slot_dir, "letters.json"), "w", encoding="utf-8") as f:
            json.dump(letters_data, f, ensure_ascii=False, indent=2)
            
        # 3. Save Cases
        dest_cases_dir = os.path.join(slot_dir, "cases")
        if os.path.exists(cases_dir):
            if os.path.exists(dest_cases_dir):
                shutil.rmtree(dest_cases_dir)
            shutil.copytree(cases_dir, dest_cases_dir)
            
        # 4. Save Agent Memory
        agents_dir = os.path.join(slot_dir, "agents")
        os.makedirs(agents_dir, exist_ok=True)
        for agent in agents:
            agent_dir = os.path.join(agents_dir, agent.name)
            os.makedirs(agent_dir, exist_ok=True)
            with open(os.path.join(agent_dir, "memory.json"), "w", encoding="utf-8") as f:
                json.dump(agent.memory, f, ensure_ascii=False, indent=2)
                
        return True

    def load_game(self, slot_id: str) -> Optional[Dict[str, Any]]:
        """Loads the game state from a slot."""
        slot_dir = self._get_slot_dir(slot_id)
        if not os.path.exists(slot_dir):
            return None
            
        # 1. Load State
        with open(os.path.join(slot_dir, "state.json"), "r", encoding="utf-8") as f:
            state = json.load(f)
            
        # 2. Load Letters
        with open(os.path.join(slot_dir, "letters.json"), "r", encoding="utf-8") as f:
            letters_data = json.load(f)
            
        # 3. Reference where cases are (caller should copy back if needed, or we just point to it)
        cases_dir = os.path.join(slot_dir, "cases")
        
        # 4. Load Agent Memory mappings
        agents_memories = {}
        agents_dir = os.path.join(slot_dir, "agents")
        if os.path.exists(agents_dir):
            for agent_name in os.listdir(agents_dir):
                mem_path = os.path.join(agents_dir, agent_name, "memory.json")
                if os.path.isfile(mem_path):
                    with open(mem_path, "r", encoding="utf-8") as f:
                        agents_memories[agent_name] = json.load(f)
                        
        return {
            "ap": state["ap"],
            "letters": letters_data,
            "cases_dir": cases_dir,
            "agents_memories": agents_memories,
            "metadata": state["metadata"]
        }

    def list_slots(self) -> List[Dict[str, Any]]:
        """Returns a list of available save slots with their metadata."""
        slots = []
        if not os.path.exists(self.base_save_dir):
            return []
            
        for d in os.listdir(self.base_save_dir):
            if d.startswith("slot_"):
                slot_id = d.replace("slot_", "")
                state_path = os.path.join(self.base_save_dir, d, "state.json")
                if os.path.exists(state_path):
                    with open(state_path, "r", encoding="utf-8") as f:
                        state = json.load(f)
                        slots.append({
                            "id": slot_id,
                            "timestamp": state.get("timestamp", "未知"),
                            "ap": state.get("ap", 0),
                            "metadata": state.get("metadata", {})
                        })
        return sorted(slots, key=lambda x: x['timestamp'], reverse=True)

    def delete_slot(self, slot_id: str) -> bool:
        slot_dir = self._get_slot_dir(slot_id)
        if os.path.exists(slot_dir):
            shutil.rmtree(slot_dir)
            return True
        return False
