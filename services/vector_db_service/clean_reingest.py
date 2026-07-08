# services/vector_db_service/clean_reingest.py
"""
Clean Re-ingestion Script
=========================
Phase 1: Analyze source MD file quality
Phase 2: Completely delete old corrupted database
Phase 3: Re-ingest from structured_texts_md ONLY
Phase 4: Verify every inserted point
"""
import os
import sys
import re
import shutil
from pathlib import Path

# Adjust paths
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from core.logger import get_logger
from core.config_manager import get_settings

logger = get_logger("clean_reingest")
settings = get_settings()


# ========================================
# Phase 1: Analyze source files
# ========================================
def analyze_source_files():
    """Comprehensive analysis of structured_texts_md files."""
    structured_md_path = Path(__file__).parent / "structured_texts_md"
    
    print("\n" + "=" * 70)
    print("  PHASE 1: Analyzing Source Files (structured_texts_md)")
    print("=" * 70)
    
    if not structured_md_path.exists():
        print("[FAIL] structured_texts_md directory not found!")
        return None
    
    total_files = 0
    files_with_content = 0
    empty_files = []
    all_files_info = []
    total_pages_content = 0
    total_pages_empty = 0
    
    for md_path in sorted(structured_md_path.rglob("*.md")):
        total_files += 1
        category = md_path.parent.name
        
        with open(md_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        page_matches = re.findall(
            r'<!-- PAGE_START (\d+) -->\s*(.*?)\s*<!-- PAGE_END \1 -->', 
            content, re.DOTALL
        )
        
        pages_with_content = 0
        pages_empty = 0
        
        for match in page_matches:
            page_text = match[1].strip()
            page_text = re.sub(r'^##\s+صفحة\s+\d+\s*\n*', '', page_text).strip()
            
            if page_text and len(page_text) > 10:
                pages_with_content += 1
            else:
                pages_empty += 1
        
        total_pages_content += pages_with_content
        total_pages_empty += pages_empty
        
        file_info = {
            "path": md_path,
            "name": md_path.name,
            "category": category,
            "total_pages": len(page_matches),
            "content_pages": pages_with_content,
            "empty_pages": pages_empty,
        }
        all_files_info.append(file_info)
        
        if pages_with_content > 0:
            files_with_content += 1
            print(f"  [OK] [{category}] {md_path.name} ({pages_with_content} pages)")
        else:
            empty_files.append(file_info)
            print(f"  [EMPTY] [{category}] {md_path.name} ({len(page_matches)} pages, NO content)")
    
    print(f"\n--- Analysis Summary ---")
    print(f"  Total files: {total_files}")
    print(f"  Files with content: {files_with_content}")
    print(f"  Empty files (will be skipped): {len(empty_files)}")
    print(f"  Pages with content: {total_pages_content}")
    print(f"  Empty pages (will be skipped): {total_pages_empty}")
    
    if empty_files:
        print(f"\n  Empty files (protected PDF / no text):")
        for f in empty_files:
            print(f"    - {f['category']}/{f['name']}")
    
    return {
        "total_files": total_files,
        "files_with_content": files_with_content,
        "empty_files": len(empty_files),
    }


# ========================================
# Phase 2: Delete old database completely
# ========================================
def nuke_database():
    """Complete deletion of old corrupted database."""
    qdrant_db_path = Path(settings.vector_db.storage_path)
    
    print("\n" + "=" * 70)
    print("  PHASE 2: Deleting Old Database Completely")
    print("=" * 70)
    
    if qdrant_db_path.exists():
        print(f"  DB path: {qdrant_db_path.absolute()}")
        
        file_count = sum(1 for _ in qdrant_db_path.rglob("*") if _.is_file())
        print(f"  Current files: {file_count}")
        
        # Delete everything except .gitkeep
        for item in qdrant_db_path.iterdir():
            if item.name == ".gitkeep":
                continue
            if item.is_dir():
                shutil.rmtree(item)
                print(f"  [DEL] directory: {item.name}")
            else:
                item.unlink()
                print(f"  [DEL] file: {item.name}")
        
        print("  [DONE] Old database deleted completely")
    else:
        print("  [INFO] Database does not exist yet (first run)")
        qdrant_db_path.mkdir(parents=True, exist_ok=True)
        print(f"  [CREATED] {qdrant_db_path.absolute()}")


# ========================================
# Phase 3: Clean re-ingestion
# ========================================
def clean_ingest():
    """Re-ingest data from structured_texts_md ONLY."""
    print("\n" + "=" * 70)
    print("  PHASE 3: Clean Re-ingestion from structured_texts_md")
    print("=" * 70)
    
    from data_ingestion import ingest_documents
    ingest_documents()
    
    print("  [DONE] Ingestion completed")


# ========================================
# Phase 4: Comprehensive verification
# ========================================
def verify_database():
    """Verify every inserted point in the database."""
    qdrant_db_path = Path(settings.vector_db.storage_path)
    collection_name = settings.vector_db.collection_name
    
    print("\n" + "=" * 70)
    print("  PHASE 4: Comprehensive Verification")
    print("=" * 70)
    
    try:
        from qdrant_client import QdrantClient
        client = QdrantClient(path=str(qdrant_db_path))
        
        if not client.collection_exists(collection_name):
            print(f"  [FAIL] Collection '{collection_name}' not found!")
            client.close()
            return
        
        info = client.get_collection(collection_name)
        print(f"  Collection: {collection_name}")
        print(f"  Points count: {info.points_count}")
        print(f"  Status: {info.status}")
        
        # Fetch ALL points
        all_points = []
        offset = None
        while True:
            points, next_offset = client.scroll(
                collection_name=collection_name,
                limit=100,
                offset=offset,
                with_payload=True,
                with_vectors=False
            )
            all_points.extend(points)
            if next_offset is None:
                break
            offset = next_offset
        
        print(f"\n  Inspecting {len(all_points)} points...")
        
        # Analyze data
        sources = {}
        categories = {}
        issues_found = 0
        clean_count = 0
        sample_issues = []
        
        for p in all_points:
            doc = p.payload.get("document", "")
            # Qdrant add() stores metadata fields at top level of payload
            source = p.payload.get("source", "UNKNOWN")
            category = p.payload.get("category", "UNKNOWN")
            page_num = p.payload.get("page_number", "?")
            
            sources[source] = sources.get(source, 0) + 1
            categories[category] = categories.get(category, 0) + 1
            
            if doc:
                # Check for corruption patterns
                arabic = len(re.findall(r'[\u0600-\u06FF]', doc))
                english = len(re.findall(r'[a-zA-Z]', doc))
                digits = len(re.findall(r'[0-9]', doc))
                spaces = len(re.findall(r'\s', doc))
                normal = arabic + english + digits + spaces
                ratio = normal / len(doc) if len(doc) > 0 else 0
                
                # Check for reversed Arabic text pattern (FExx range = Arabic Presentation Forms)
                reversed_arabic = len(re.findall(r'[\uFE70-\uFEFF]', doc))
                
                has_issue = False
                issue_type = ""
                
                if ratio < 0.7:
                    has_issue = True
                    issue_type = f"low normal ratio ({ratio:.2f})"
                elif reversed_arabic > len(doc) * 0.1:
                    has_issue = True
                    issue_type = f"reversed Arabic chars ({reversed_arabic})"
                elif len(doc.strip()) < 15:
                    has_issue = True
                    issue_type = f"too short ({len(doc.strip())} chars)"
                
                if has_issue:
                    issues_found += 1
                    if len(sample_issues) < 10:
                        snippet = doc[:80].replace('\n', ' ')
                        sample_issues.append(f"    [{source} p{page_num}] {issue_type}: {snippet}...")
                else:
                    clean_count += 1
        
        # Results
        print(f"\n  --- Policies indexed ({len(sources)} sources) ---")
        for src, count in sorted(sources.items(), key=lambda x: -x[1]):
            print(f"    {src}: {count} chunks")
        
        print(f"\n  --- Categories ({len(categories)}) ---")
        for cat, count in sorted(categories.items(), key=lambda x: -x[1]):
            print(f"    {cat}: {count} chunks")
        
        print(f"\n  --- Data Quality ---")
        print(f"    Clean points: {clean_count}")
        print(f"    Problematic points: {issues_found}")
        
        if issues_found > 0:
            print(f"\n  [WARNING] Sample issues:")
            for issue in sample_issues:
                print(issue)
        else:
            print(f"\n  [SUCCESS] ALL {clean_count} points are clean!")
        
        # Test retrieval
        print(f"\n  --- Test Retrieval ---")
        client.set_model("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
        
        test_queries = [
            "ما هي سياسة الإجازة السنوية؟",
            "إجراءات الترقية",
            "مكافحة الرشوة والفساد",
        ]
        
        for query in test_queries:
            results = client.query(
                collection_name=collection_name,
                query_text=query,
                limit=2
            )
            print(f"\n  Query: '{query}'")
            for i, res in enumerate(results):
                snippet = res.document[:100].replace('\n', ' ')
                src = res.metadata.get("source", "?")
                page = res.metadata.get("page_number", "?")
                cat = res.metadata.get("category", "?")
                print(f"    Result {i+1} [{cat}/{src} p{page}]: {snippet}...")
        
        client.close()
        
        print("\n" + "=" * 70)
        if issues_found == 0:
            print("  [SUCCESS] Verification PASSED - Database is clean!")
        else:
            print(f"  [WARNING] {issues_found} issues found - review above")
        print("=" * 70)
        
    except Exception as e:
        print(f"  [ERROR] Verification failed: {e}")
        import traceback
        traceback.print_exc()


# ========================================
# Main execution
# ========================================
if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("  CLEAN RE-INGESTION PIPELINE")
    print("  Source: structured_texts_md ONLY")
    print("  Action: DELETE old data + RE-INGEST clean data")
    print("=" * 70)
    
    # Phase 1
    analysis = analyze_source_files()
    if analysis is None:
        print("[FAIL] Analysis failed - aborting")
        sys.exit(1)
    
    if analysis["files_with_content"] == 0:
        print("[FAIL] No files with content - aborting")
        sys.exit(1)
    
    print(f"\n  Will delete ALL old data and re-ingest {analysis['files_with_content']} clean files.")
    print(f"  Proceeding automatically...")
    
    # Phase 2
    nuke_database()
    
    # Phase 3
    clean_ingest()
    
    # Phase 4
    verify_database()
    
    print("\n  PIPELINE COMPLETED!")
