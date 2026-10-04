import os
import json
from pathlib import Path

def discover():
    root = Path(".")
    inventory = {
        "directories": {},
        "top_level_scripts": [],
        "config_files": [],
        "ci_files": [],
    }
    
    for d in ["src", "behavioral_evasion_suite", "tests", "providers", "docs", "scripts", "examples"]:
        dp = root / d
        if dp.exists():
            py_files = [f.as_posix() for f in dp.glob("**/*.py")]
            all_files = [f.as_posix() for f in dp.glob("**/*") if f.is_file()]
            inventory["directories"][d] = {
                "py_count": len(py_files),
                "total_files": len(all_files),
                "py_files": py_files,
            }
            
    inventory["top_level_scripts"] = [f.name for f in root.glob("*.py")]
    inventory["config_files"] = [f.name for f in [root / "pyproject.toml", root / "requirements.txt", root / ".gitignore"] if f.exists()]
    ci_p = root / ".github"
    if ci_p.exists():
        inventory["ci_files"] = [f.as_posix() for f in ci_p.glob("**/*") if f.is_file()]
        
    print(f"Discovered: {len(inventory['directories'])} directories")
    for d, info in inventory["directories"].items():
        print(f"  - {d}: {info['py_count']} py files / {info['total_files']} total files")
    print(f"Top level scripts ({len(inventory['top_level_scripts'])}): {inventory['top_level_scripts']}")
    print(f"Config files: {inventory['config_files']}")
    print(f"CI files: {inventory['ci_files']}")
    
    return inventory

if __name__ == "__main__":
    discover()
