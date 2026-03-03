from typing import List, Optional, Dict
from dataclasses import dataclass, asdict
from datetime import datetime
import json
import os

@dataclass
class Report:
    id: int
    type: str  # "明发奏折" or "密折"
    content: str
    timestamp: str
    author: str

class LettersSystem:
    """Manages the domain logic for Letters (Official and Secret Reports)."""
    def __init__(self):
        self.reports: List[Report] = []
        self._next_id = 1
    
    def add_report(self, type: str, content: str, author: str) -> Report:
        report = Report(
            id=self._next_id,
            type=type,
            content=content,
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            author=author
        )
        self.reports.append(report)
        self._next_id += 1
        return report

    def get_report(self, report_id: int) -> Optional[Report]:
        for r in self.reports:
            if r.id == report_id:
                return r
        return None

    def save_to_file(self, file_path: str):
        """Saves all reports to a JSON file."""
        data = [asdict(r) for r in self.reports]
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load_from_file(self, file_path: str):
        """Loads reports from a JSON file."""
        if not os.path.exists(file_path):
            return
        
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.reports = [Report(**item) for item in data]
                if self.reports:
                    self._next_id = max(r.id for r in self.reports) + 1
        except Exception:
            # If corruption occurs, we ignore for MVP
            pass
