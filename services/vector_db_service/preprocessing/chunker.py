from typing import List, Dict, Any
from langchain_text_splitters import RecursiveCharacterTextSplitter

def chunk_document_pages(pages_data: List[Dict[str, Any]], chunk_size: int = 600, chunk_overlap: int = 100) -> List[Dict[str, Any]]:
    """
    يقسم صفحات المستند باستخدام LangChain لضمان تقسيم دلالي سليم وتداخل حقيقي.
    """
    # تهيئة أداة التقسيم
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        separators=["\n\n", "\n", ".", "،", " ", ""] # أولويات التقسيم (فقرة، سطر، نقطة، فاصلة)
    )
    
    chunks = []
    for page in pages_data:
        text = page["text"]
        page_num = page["page_number"]
        
        # الأداة تتكفل بالتقسيم والتداخل بشكل مثالي
        split_texts = text_splitter.split_text(text)
        
        for split in split_texts:
            chunks.append({
                "text": split,
                "page_number": page_num
            })
            
    return chunks