#!/usr/bin/env python3
"""Sort specialty edges in markdown files by rank, then English name.

Usage: python sort_edges.py <file1.md> [file2.md ...]
"""

import re
import sys

RANK_ORDER = {
    '入门': 0,
    '行家': 1,
    '老练': 2,
    '英杰': 3,
    '传奇': 4,
}


def get_english_name(heading_line):
    """Extract English name from heading like '## 精通CQB CQB, Improved'."""
    text = heading_line[3:].strip()
    m = re.match(r'^(.+?)\s+([A-Z][A-Za-z0-9 ,.\'\-!&+]+)$', text)
    if m:
        return m.group(2).strip()
    return ""


def get_rank(block_text):
    """Extract rank from edge block."""
    m = re.search(r'需求：\*\*\s*(入门|行家|老练|英杰|传奇)', block_text)
    if m:
        return m.group(1)
    return None


def is_real_edge(block_text):
    """Check if a ## block is a real edge (has 需求) or a sub-section."""
    return get_rank(block_text) is not None


def sort_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Find the first edge heading
    m = re.search(r'\n## ', content)
    if not m:
        print(f"  No edges found, skipping")
        return

    split_point = m.start() + 1  # include the \n
    header = content[:split_point]
    body = content[split_point:]

    # Split by \n## to get individual blocks
    raw_blocks = re.split(r'\n(?=## )', body)

    # Merge sub-sections into parent edges
    edges = []
    for block in raw_blocks:
        if not block.strip():
            continue
        if is_real_edge(block):
            edges.append(block)
        elif edges:
            edges[-1] = edges[-1] + '\n' + block
        else:
            edges.append(block)

    # Sort
    def sort_key(edge):
        heading = edge.split('\n')[0]
        rank = get_rank(edge)
        eng = get_english_name(heading)
        return (RANK_ORDER.get(rank, 99), eng.lower())

    edges.sort(key=sort_key)

    # Reconstruct: header + edges joined with blank line
    result = header + '\n\n'.join(edges)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(result)

    print(f"  Sorted {len(edges)} edges")


if __name__ == '__main__':
    files = sys.argv[1:]
    if not files:
        print("Usage: python sort_edges.py <file1.md> [file2.md ...]")
        sys.exit(1)

    for f in files:
        print(f"Processing: {f}")
        sort_file(f)
