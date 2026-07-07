import uuid
import re

def parse_notion_markdown(md_content, file_path="notion_export.md", title="Untitled"):
    chunks = []
    
    title_match = re.search(r'^#\s+(.*)', md_content, re.MULTILINE)
    if title_match:
        title = title_match.group(1).strip()
        
    # Split content on markdown heading tags (## or ###)
    sections = re.split(r'^(##?#?\s+.*)', md_content, flags=re.MULTILINE)
    
    current_text = ""
    for sec in sections:
        if not sec.strip():
            continue
        if len(current_text) + len(sec) > 1500 and current_text:
            chunks.append(current_text.strip())
            current_text = sec
        else:
            current_text += "\n\n" + sec
            
    if current_text:
        chunks.append(current_text.strip())
        
    formatted = []
    for idx, c in enumerate(chunks):
        formatted.append({
            "chunk_id": str(uuid.uuid4()),
            "source_type": "notion_page",
            "source_id": f"{file_path}#section-{idx}",
            "raw_text": f"Notion Page: {title}\n\n{c}",
            "author": None,
            "timestamp": None,  # Handled as null for non-dated Notion documents
            "project": None,
            "metadata": {
                "page_title": title,
                "section_index": idx,
                "file_path": file_path
            }
        })
    return formatted