import os
from collections import Counter
from pathlib import Path

# 1. Directories to completely ignore for performance and cleanliness
IGNORED_DIRS = [
    ".git",
    "__pycache__",
    "node_modules",
    "build",
    "dist",
    ".out",
    "venv",
    ".venv",
    "env",
    ".pytest_cache",
    ".vscode",
    ".idea",
]

# 2. Reference map for core project files (Python, React, AI/LLM Models)
KNOWN_EXTENSIONS = {
    # Web & React
    ".jsx": "React JSX Component",
    ".tsx": "React TSX Component",
    ".js": "JavaScript Source",
    ".ts": "TypeScript Source",
    ".html": "HTML Page",
    ".css": "CSS Stylesheet",
    # AI/ML Models & Weights
    ".safetensors": "Safetensors Model Weights",
    ".gguf": "GGUF Quantized Model",
    ".bin": "Binary / Model Weights",
    ".pt": "PyTorch Model",
    ".pth": "PyTorch Weights",
    ".onnx": "ONNX Model",
    ".pkl": "Python Pickle Data",
    # Programming Languages & Scripts
    ".py": "Python Source",
    ".sh": "Shell Script",
    # Data & Configuration
    ".json": "JSON Data",
    ".yaml": "YAML Configuration",
    ".yml": "YML Configuration",
    ".xml": "XML Data",
    ".csv": "CSV Spreadsheet",
    # Documents & Text
    ".md": "Markdown Documentation",
    ".txt": "Plain Text",
    ".pdf": "PDF Document",
}


def analyze_project_professional():
    root_dir = Path.cwd()
    print(f"🔍 Scanning Project Root: {root_dir}")
    print(f"🚫 Ignored Directories: {', '.join(IGNORED_DIRS)}\n")

    known_counter = Counter()
    other_counter = Counter()
    no_ext_count = 0
    total_files = 0

    # Walk through the directory tree
    for root, dirs, files in os.walk(root_dir):
        # Modify dirs in-place to prune ignored directories instantly
        dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]

        for file in files:
            total_files += 1
            ext = Path(file).suffix.lower()

            if ext == "":
                no_ext_count += 1
            elif ext in KNOWN_EXTENSIONS:
                known_counter[KNOWN_EXTENSIONS[ext]] += 1
            else:
                # Dynamic tracking for any other unexpected extensions
                other_counter[ext] += 1

    total_others = sum(other_counter.values())

    # --- Clean & Professional English Terminal Output ---
    print("=" * 65)
    print(f"📊 Total Target Files Found: {total_files}")
    print("=" * 65)

    # 1. Print primary known extensions
    if known_counter:
        print(f"{'File Type / Extension':<35} | {'Count':<10}")
        print("-" * 65)
        for file_type, count in known_counter.most_common():
            print(f"{file_type:<35} | {count:<10}")

    # 2. Print files without extensions if any
    if no_ext_count > 0:
        print(f"{'Files with No Extension':<35} | {no_ext_count:<10}")

    print("-" * 65)

    # 3. Print "Other" files summary and dynamic breakdown
    print(f"{'📁 Total Miscellaneous Files (Others)':<35} | {total_others:<10}")

    if total_others > 0:
        print("\n📋 Breakdown of Miscellaneous Extensions Detected:")
        details = [f"{ext} ({count})" for ext, count in other_counter.items()]
        print("   " + ", ".join(details))

    print("=" * 65)


if __name__ == "__main__":
    analyze_project_professional()