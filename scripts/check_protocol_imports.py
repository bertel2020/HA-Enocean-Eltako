"""Fail if any module in the protocol layer imports from homeassistant.

The protocol layer must stay usable without Home Assistant (tests, tools,
a later standalone library). Run: python scripts/check_protocol_imports.py
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

PROTOCOL_DIR = Path(__file__).resolve().parent.parent / "custom_components/enocean_eltako/protocol"
FORBIDDEN = "homeassistant"


def find_violations(root: Path = PROTOCOL_DIR) -> list[str]:
    """Return 'file:line: module' for every forbidden import below root."""
    violations = []
    for path in sorted(root.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                modules = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                modules = [node.module]
            else:
                continue
            for module in modules:
                if module == FORBIDDEN or module.startswith(FORBIDDEN + "."):
                    violations.append(f"{path.relative_to(root.parent)}:{node.lineno}: {module}")
    return violations


def main() -> int:
    violations = find_violations()
    for line in violations:
        print(line)
    if violations:
        print(f"{len(violations)} homeassistant import(s) in the protocol layer", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
