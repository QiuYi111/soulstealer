import os

class CasesSystem:
    """Manages the persistence of case files (Raw and Polished)."""
    
    def __init__(self, storage_dir: str = "data/cases"):
        self.storage_dir = storage_dir
        if not os.path.exists(self.storage_dir):
            os.makedirs(self.storage_dir)

    def save_case(self, report_id: int, raw_content: str, polished_content: str):
        """Saves case files to the local disk."""
        case_dir = os.path.join(self.storage_dir, f"case_{report_id}")
        if not os.path.exists(case_dir):
            os.makedirs(case_dir)
            
        raw_path = os.path.join(case_dir, "case_raw.txt")
        polished_path = os.path.join(case_dir, "case_polished.txt")
        
        with open(raw_path, "w", encoding="utf-8") as f:
            f.write(raw_content)
            
        with open(polished_path, "w", encoding="utf-8") as f:
            f.write(polished_content)
            
        return raw_path, polished_path

    def get_case_paths(self, report_id: int) -> tuple[str, str]:
        """Returns the paths for the raw and polished files of a report."""
        case_dir = os.path.join(self.storage_dir, f"case_{report_id}")
        raw_path = os.path.join(case_dir, "case_raw.txt")
        polished_path = os.path.join(case_dir, "case_polished.txt")
        return raw_path, polished_path
