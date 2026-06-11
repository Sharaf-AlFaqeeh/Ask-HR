# services/vector_db_service/preprocessing/chunker.py
from typing import List, Dict, Any

def chunk_document_pages(pages_data: List[Dict[str, Any]], chunk_size: int = 600, overlap: int = 100) -> List[Dict[str, Any]]:
    """
    يقسم صفحات المستند إلى أجزاء متداخلة دلالياً مع الاحتفاظ ببيانات الصفحة.
    """
    chunks = []
    
    for page in pages_data:
        text = page["text"]
        page_num = page["page_number"]
        
        # تقسيم مبدئي بناءً على الفقرات لضمان عدم قطع الجمل من المنتصف
        paragraphs = text.split("\n")
        current_chunk = ""
        
        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if not paragraph:
                continue
                
            if len(current_chunk) + len(paragraph) < chunk_size:
                current_chunk += " " + paragraph
            else:
                if current_chunk:
                    chunks.append({
                        "text": current_chunk.strip(),
                        "page_number": page_num
                    })
                # الاحتفاظ بجزء متداخل (Overlap)
                current_chunk = paragraph
                
        if current_chunk:
            chunks.append({
                "text": current_chunk.strip(),
                "page_number": page_num
            })
            
    return chunks
