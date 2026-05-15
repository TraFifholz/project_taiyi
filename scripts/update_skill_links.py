#!/usr/bin/env python3
"""Update cross-references from individual skill pages to anchors in merged skill page.

After merging all skill files into a single 技能.md, links like:
  [格斗](../技能/格斗/)
need to become:
  [格斗](../技能/#格斗-fighting)
"""

import re
import os
import glob

SKILLS_DIR = r'src\核心规则\技能'
CORE_RULES_DIR = r'src\核心规则'


def build_skill_map():
    """Read all skill files and build {chinese_name: english_name} mapping."""
    skill_map = {}
    for f in glob.glob(os.path.join(SKILLS_DIR, '*.md')):
        with open(f, 'r', encoding='utf-8') as fh:
            content = fh.read()
        fm = re.match(r'^---\s*\n.*?\n---', content, re.DOTALL)
        if fm:
            title = re.search(r'title:\s*"(.+?)"', fm.group())
            title_en = re.search(r'title_en:\s*"(.+?)"', fm.group())
            if title and title_en:
                cn = title.group(1)
                en = title_en.group(1).lower().replace(' ', '-')
                skill_map[cn] = f'{cn}-{en}'
    return skill_map


def update_file(filepath, skill_map):
    """Replace skill page links with anchor links in a single file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    original = content

    # Pattern: [text](../技能/SKILLNAME/) or [text](../技能/SKILLNAME)
    # The SKILLNAME is the Chinese skill name (which matches the directory/filename)
    def replace_link(m):
        link_text = m.group(1)
        skill_name = m.group(2).rstrip('/')
        if skill_name in skill_map:
            anchor = skill_map[skill_name]
            return f'[{link_text}](../技能/#{anchor})'
        return m.group(0)

    # Match [any text](../技能/skillname) optionally with trailing /
    content = re.sub(
        r'\[([^\]]+)\]\(\.\./技能/([^)]+?)\)',
        replace_link,
        content
    )

    if content != original:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    return False


def main():
    skill_map = build_skill_map()
    print(f'Loaded {len(skill_map)} skill mappings')

    # Update all markdown files in core rules (excluding the skills directory itself)
    updated = 0
    for f in glob.glob(os.path.join(CORE_RULES_DIR, '**/*.md'), recursive=True):
        # Skip files in the skills directory (they're the old individual files)
        if '\\技能\\' in f:
            continue
        if update_file(f, skill_map):
            updated += 1
            print(f'  Updated: {f}')

    print(f'Updated {updated} files')


if __name__ == '__main__':
    main()
