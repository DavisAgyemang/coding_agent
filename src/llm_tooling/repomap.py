# repomap.py
import os
from pathlib import Path
from typing import Union
# 👇 Import Query directly from the core tree_sitter library
from tree_sitter import Language, Parser, Query, QueryCursor
import tree_sitter_python as tspython


class RepoMapper:
    def __init__(self, root_dir: Union[str, Path]):
        self.root_dir = Path(root_dir).resolve()

        # Modern tree-sitter configuration
        self.py_lang = Language(tspython.language())
        self.parser = Parser(self.py_lang)

        # 👇 FIX: Instantiate Query directly rather than through self.py_lang.query()
        self.query = Query(self.py_lang, """
            (class_definition name: (identifier) @class.name)
            (function_definition name: (identifier) @func.name)
        """)

    def extract_structures(self, file_path: Path) -> list[str]:
        """Extracts names of classes and functions from a file using Tree-Sitter."""
        try:
            code = file_path.read_bytes()
            tree = self.parser.parse(code)

            # 👇 Pass self.query directly into QueryCursor's constructor
            cursor = QueryCursor(self.query)
            captures = cursor.captures(tree.root_node)

            structures = []
            # Loop through the extracted captures dictionary mapping
            for capture_name, nodes in captures.items():
                for node in nodes:
                    name = node.text.decode('utf-8', errors='ignore')
                    if capture_name == 'class.name':
                        structures.append(f"  class {name}:")
                    elif capture_name == 'func.name':
                        parent = node.parent
                        prefix = "    def " if parent and parent.type == 'block' else "  def "
                        structures.append(f"{prefix}{name}(...)")
            return structures
        except Exception:
            return []

    def generate_map(self) -> str:
        """Walks the repo and builds a structural skeleton map string."""
        map_lines = ["### REPOSITORY SKELETON MAP (Tree-Sitter LSP Layer) ###\n"]

        for path in sorted(self.root_dir.rglob("*.py")):
            if any(part in path.parts for part in [".venv", "venv", "__pycache__", ".git"]):
                continue

            relative_path = path.relative_to(self.root_dir)
            structures = self.extract_structures(path)

            if structures:
                map_lines.append(f"📄 {relative_path}")
                map_lines.extend(structures)
                map_lines.append("")  # Spacer

        return "\n".join(map_lines)