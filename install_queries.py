#!/usr/bin/env python3
"""
Helper script to install tree-sitter query files for RepoMap

This script finds tree-sitter language query files from installed packages
and copies them to the local queries directory.
"""

import os
import sys
import importlib
import shutil
from pathlib import Path

def find_query_files():
    """Find and collect tree-sitter query files from installed packages"""

    # Create queries directory if it doesn't exist
    queries_dir = Path(__file__).parent / "queries"
    queries_dir.mkdir(exist_ok=True)

    print(f"Installing query files to {queries_dir}")

    # Try to find tree-sitter language pack
    try:
        import tree_sitter_language_pack
        pkg_dir = Path(tree_sitter_language_pack.__file__).parent
        print(f"Found tree-sitter-language-pack at {pkg_dir}")

        # Check for queries directory
        queries_pkg_dir = pkg_dir / "queries"
        if queries_pkg_dir.exists() and queries_pkg_dir.is_dir():
            for query_file in queries_pkg_dir.glob("*-tags.scm"):
                dest_file = queries_dir / query_file.name
                print(f"Copying {query_file.name}")
                shutil.copy2(query_file, dest_file)

        # Also look for language-specific modules
        from tree_sitter_language_pack import __all__ as langs
        for lang_name in langs:
            if lang_name.startswith("tree_sitter_"):
                try:
                    lang_module = importlib.import_module(lang_name)
                    lang_dir = Path(lang_module.__file__).parent
                    queries_lang_dir = lang_dir / "queries"

                    if queries_lang_dir.exists() and queries_lang_dir.is_dir():
                        for query_file in queries_lang_dir.glob("tags.scm"):
                            lang = lang_name.replace("tree_sitter_", "")
                            dest_file = queries_dir / f"{lang}-tags.scm"
                            print(f"Copying {lang} tags")
                            shutil.copy2(query_file, dest_file)
                except (ImportError, AttributeError) as e:
                    print(f"Error with {lang_name}: {e}")

    except ImportError:
        print("tree-sitter-language-pack not found")

    # Also check grep_ast
    try:
        import grep_ast
        pkg_dir = Path(grep_ast.__file__).parent
        print(f"Found grep-ast at {pkg_dir}")

        queries_pkg_dir = pkg_dir / "queries"
        if queries_pkg_dir.exists() and queries_pkg_dir.is_dir():
            for query_file in queries_pkg_dir.glob("*-tags.scm"):
                dest_file = queries_dir / query_file.name
                print(f"Copying {query_file.name}")
                shutil.copy2(query_file, dest_file)

    except ImportError:
        print("grep-ast not found")

    # Count installed query files
    num_files = len(list(queries_dir.glob("*-tags.scm")))
    print(f"Installed {num_files} query files")

if __name__ == "__main__":
    find_query_files()
