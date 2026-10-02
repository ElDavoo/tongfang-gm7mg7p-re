#!/usr/bin/env python3
"""Print every suite `tools/run-tests.sh` runs, with the first line of its docstring.

A suite says what it stands in for in its own module docstring, so this is the
index: generated on demand from the files themselves, never committed, and so
never a line two branches both have to edit. `--full` prints whole docstrings.
Discovery is `tools/test_readme_suite_table.py`'s `discover()`, the runner's rule.
"""
import argparse
import ast
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_readme_suite_table import REPO, discover  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--full', action='store_true', help='print whole docstrings')
    ap.add_argument('paths', nargs='*', help='only suites under these directories')
    args = ap.parse_args()
    for rel in sorted(discover()):
        if args.paths and not any(rel.startswith(p.rstrip('/') + '/') for p in args.paths):
            continue
        doc = ast.get_docstring(ast.parse((REPO / rel).read_text(encoding='utf-8'))) or ''
        if args.full:
            print(f'## {rel}\n\n{doc}\n')
        else:
            print(f'{rel}: {doc.splitlines()[0] if doc else "(no docstring)"}')


if __name__ == '__main__':
    main()
