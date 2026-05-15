#!/usr/bin/env python3
"""Merge all skill markdown files into a single page.

Usage: python merge_skills.py
"""

import re
import os
import glob

SKILLS_DIR = r'src\核心规则\技能'
OUTPUT_FILE = r'src\核心规则\技能.md'

# Put unskilled attempt first as it's a general rule
FIRST_SKILL = '未受训尝试'


def parse_skill(filepath):
    """Extract frontmatter and content from a skill file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Extract frontmatter
    fm_match = re.match(r'^---\s*\n(.*?)\n---\s*\n(.*)', content, re.DOTALL)
    if not fm_match:
        return None

    fm_text = fm_match.group(1)
    body = fm_match.group(2).strip()

    # Parse frontmatter fields
    title = re.search(r'title:\s*"(.+?)"', fm_text)
    title_en = re.search(r'title_en:\s*"(.+?)"', fm_text)

    return {
        'title': title.group(1) if title else '',
        'title_en': title_en.group(1) if title_en else '',
        'body': body,
    }


def main():
    skill_files = glob.glob(os.path.join(SKILLS_DIR, '*.md'))

    skills = []
    for f in skill_files:
        data = parse_skill(f)
        if data:
            skills.append(data)

    # Sort: unskilled attempt first, then alphabetically by English name
    def sort_key(s):
        if s['title'] == FIRST_SKILL:
            return ('', '')  # sorts first
        return ('', s['title_en'].lower())

    skills.sort(key=sort_key)

    # Build output
    lines = []
    lines.append('---')
    lines.append('title: "技能 Skills"')
    lines.append('---')
    lines.append('')
    lines.append('# 技能 Skills')
    lines.append('')

    for s in skills:
        # Heading: ## ChineseName / EnglishName
        lines.append(f'## {s["title"]} {s["title_en"]}')
        lines.append('')

        body = s['body']

        # Demote any ## sub-headings to ###
        body = re.sub(r'^## ', '### ', body, flags=re.MULTILINE)

        lines.append(body)
        lines.append('')

    result = '\n'.join(lines)

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(result)

    print(f'Merged {len(skills)} skills into {OUTPUT_FILE}')


if __name__ == '__main__':
    main()
