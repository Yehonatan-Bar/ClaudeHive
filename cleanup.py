#!/usr/bin/env python3
"""
Cleanup script to remove Windows Zone.Identifier files and other artifacts
"""
import os
from pathlib import Path

def cleanup_zone_files(directory=None):
    """Remove Zone.Identifier files created by Windows"""
    if directory is None:
        directory = Path(__file__).parent
    else:
        directory = Path(directory)
    
    removed_count = 0
    for file in directory.rglob("*:Zone.Identifier"):
        try:
            file.unlink()
            print(f"Removed: {file}")
            removed_count += 1
        except Exception as e:
            print(f"Could not remove {file}: {e}")
    
    if removed_count == 0:
        print("No Zone.Identifier files found")
    else:
        print(f"Removed {removed_count} Zone.Identifier files")

if __name__ == "__main__":
    cleanup_zone_files()