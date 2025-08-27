
#import os, re, json, sys, pathlib, hashlib
import re, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MATHLIB = Path(ROOT, 'data', 'raw', 'mathlib4', 'Mathlib')
OUT = Path(ROOT, 'data', 'processed', 'statements.json')

decl_pat = re.compile(
    r'^(theorem|lemma)\s+([A-Za-z0-9_\'\.]+)\s*:(.*?)(?:(?==\s*by)|(?::=)|(?:\n\s*:=)|(?:\n\s*where)|$)',
    re.DOTALL | re.MULTILINE
)
import_pat = re.compile(r'^\s*import\s+([A-Za-z0-9\.\s]+)', re.MULTILINE)


def clean_stmt(s: str) -> str:
    # collapse whitespace, keep unicode symbols
    return re.sub(r'\s+', ' ', s).strip()


def module_from_path(p: Path) -> str:
    # Mathlib/Algebra/Group.lean -> Mathlib.Algebra.Group
    parts = list(p.relative_to(MATHLIB).with_suffix('').parts)
    return 'Mathlib.' + '.'.join(parts)


def harvest_file(fp: Path):
    text = fp.read_text(encoding='utf-8', errors='ignore')
    # optional quick skip: files that are entirely tactics/automation are fine to include or skip.
    imports = []
    m = import_pat.findall(text)
    if m:
        # split "A.B C.D" tokens
        for line in m:
            imports.extend([tok for tok in line.split() if tok])

    items = []
    for m in decl_pat.finditer(text):
        kind, name, stmt = m.group(1), m.group(2), m.group(3)
        stmt = clean_stmt(stmt)
        # very light "sorry" guard in the declaration head span
        head_span = text[m.start(): text.find('\n\n', m.start()) if text.find('\n\n', m.start())!=-1 else m.end()]
        if re.search(r'\bsorry\b', head_span):
            continue
        mod = module_from_path(fp)
        sysname = 'lean'
        kind_short = 'thm' if kind == 'theorem' else 'lem'
        _id = f'{sysname}:{mod}.{name}'
        items.append({
            'id': _id,
            'sys': sysname,
            'mod': mod,
            'name': name,
            'kind': kind_short,
            'stmt': stmt
        })
    return items


def main():
    all_items = []

    for fp in MATHLIB.rglob('*.lean'):
        # skip archived or generated if desired
        if '/.lake/' in str(fp): 
            continue
        rel = fp.relative_to(MATHLIB)
        if any(part.startswith('_archive') for part in rel.parts):
            continue
        items = harvest_file(fp)
        all_items.extend(items)

    # deterministic order
    all_items.sort(key=lambda d: d['id'])
    data = {'ver': 1, 'statements': all_items}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'wrote {len(all_items)} statements -> {OUT}')


if __name__ == '__main__':
    main()
