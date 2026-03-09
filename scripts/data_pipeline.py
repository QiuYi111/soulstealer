import os
import json
import uuid
import re

# Refined keywords for the Soulstealing (叫魂) incident
KEYWORDS = [
    "割辫", "剪辫", "叫魂", "妖术", "邪术", "厌胜", "迷人", 
    "石匠", "僧", "道", "比丘", "尼", "流丐", "乞丐",
    "德清", "萧山", "苏州", "杭州", "湖州", "乾隆三十三年",
    "富尼汉", "永德", "公报", "明瑞", "高晋", "彰宝"
]

def clean_text(text):
    # Remove markers but keep meaningful content
    text = text.replace('\n', ' ').strip()
    text = re.sub(r'\s+', ' ', text)
    return text

def parse_shilu_1768(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    entries = []
    current_month = "未知"
    current_day = "未知"
    
    raw_text = "".join(lines)
    raw_entries = re.split(r'○', raw_text)
    
    file_name = os.path.basename(file_path)

    for raw_entry in raw_entries:
        raw_entry = raw_entry.strip()
        if not raw_entry:
            continue
            
        month_match = re.search(r'([正二三四五六七八九十]{1,2})月', raw_entry)
        if "乾隆三十三年" in raw_entry and month_match:
            current_month = month_match.group(1) + "月"
            day_match = re.search(r'([甲乙丙丁戊己庚辛壬癸][子丑寅卯辰巳午未申酉戌亥][朔]?)', raw_entry)
            if day_match:
                current_day = day_match.group(1)

        entry_date = current_day
        is_summary = False
        
        if raw_entry.startswith("是月"):
            is_summary = True
            entry_date = "全月汇总"
        else:
            day_marker_match = re.match(r'^([甲乙丙丁戊己庚辛壬癸][子丑寅卯辰巳午未申酉戌亥][朔]?)。', raw_entry)
            if day_marker_match:
                current_day = day_marker_match.group(1)
                entry_date = current_day

        cleaned_content = clean_text(raw_entry)
        if len(cleaned_content) < 20: # Skip very short snippets
            continue

        entries.append({
            "id": str(uuid.uuid4()),
            "content": cleaned_content,
            "metadata": {
                "source": file_name,
                "year": "1768",
                "month": current_month,
                "day": entry_date,
                "is_summary": is_summary,
                "type": "official_shilu"
            }
        })
            
    return entries

def parse_generic_text(file_path):
    """Generic parser for non-Shilu files using character-based chunking."""
    file_name = os.path.basename(file_path)
    with open(file_path, 'r', encoding='utf-8') as f:
        text = f.read()
    
    # Split by double newlines or similar to keep some semantic coherence
    raw_chunks = re.split(r'\n\s*\n', text)
    entries = []
    for chunk in raw_chunks:
        cleaned = clean_text(chunk)
        if len(cleaned) < 50:
            continue
            
        entries.append({
            "id": str(uuid.uuid4()),
            "content": cleaned,
            "metadata": {
                "source": file_name,
                "type": "historical_archive",
                "year": "清代 (通用)"
            }
        })
    return entries

def main():
    ref_dir = "ref"
    output_file = "data/archives/processed/chunks.jsonl"
    
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    print(f"Starting pipeline for directory: {ref_dir}...")
    if not os.path.isdir(ref_dir):
        print(f"Error: {ref_dir} not found.")
        return

    all_processed_entries = []
    
    for filename in os.listdir(ref_dir):
        if not filename.endswith(".txt"):
            continue
            
        file_path = os.path.join(ref_dir, filename)
        print(f"Processing {filename}...")
        
        if "实录" in filename:
            entries = parse_shilu_1768(file_path)
        else:
            entries = parse_generic_text(file_path)
            
        all_processed_entries.extend(entries)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        for entry in all_processed_entries:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')
            
    print(f"Successfully processed {len(all_processed_entries)} entries into {output_file}")

if __name__ == "__main__":
    main()
