from typing import List

class LettersSystem:
    """Manages the domain logic for Letters (Official and Secret Reports)."""
    def __init__(self):
        self.official_reports: List[str] = []
        self.secret_reports: List[str] = []
    
    def draft_report(self, is_secret: bool, content: str):
        if is_secret:
            self.secret_reports.append(content)
        else:
            self.official_reports.append(content)
