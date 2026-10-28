"""Locate a pre-migration workspace path without modifying archived evidence."""
from pathlib import Path
import argparse, json

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / 'maintenance/workspace-20260911/moves.json'

def resolve_old_path(value):
    value = value.replace('\\', '/').rstrip('/')
    prefix = ROOT.as_posix() + '/'
    if value.casefold().startswith(prefix.casefold()):
        value = value[len(prefix):]
    rules = json.loads(MANIFEST.read_text(encoding='utf-8'))['rules']
    for old in sorted(rules, key=len, reverse=True):
        if value == old or value.startswith(old + '/'):
            value = rules[old] + value[len(old):]
            break
    return (ROOT / value).resolve()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('path', help='Old or current local workspace path')
    args = parser.parse_args()
    target = resolve_old_path(args.path)
    print(target)
    if not target.exists():
        print('Path does not currently exist.')
        raise SystemExit(1)
