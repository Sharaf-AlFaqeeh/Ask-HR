import os

def search_text():
    target_terms = ["0١ يوم", "5553", "ثانياً: تنظيم الإجازات"]
    project_root = r"p:\____AI____\HSAGroup\AskHRPro"
    out_path = r"tests\search_all_files_results.txt"
    
    with open(out_path, "w", encoding="utf-8") as out:
        out.write(f"Searching for terms {target_terms} in {project_root}...\n")
        
        found = False
        for root, dirs, files in os.walk(project_root):
            if any(x in root for x in [".git", ".vscode", "__pycache__", ".pytest_cache", "local_qdrant_db"]):
                continue
                
            for file in files:
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                        for term in target_terms:
                            if term in content:
                                out.write(f"FOUND: '{term}' in file: {file_path}\n")
                                found = True
                except Exception as e:
                    pass
                    
        if not found:
            out.write("No terms found in any text files in the project.\n")

if __name__ == "__main__":
    search_text()
