"""Offline only. Remap the public docs set into independent screenshot workspaces.
Run from repo root. Does not contact the reference instance or edit the source sample.
"""
import json
from pathlib import Path
from uuid import UUID
from hashlib import sha256

ROOT = Path(__file__).resolve().parents[4]
DEST = Path(__file__).resolve().parent / 'picture-data'
WORKSPACES = {
    'c10-workbook-pictures': 'C10 workbook pictures',
    'c10-words-pictures': 'C10 words pictures',
    'c10-whole-move-pictures': 'C10 whole move pictures',
    'c10-partial-move-pictures': 'C10 partial move pictures',
    'c10-mapping-pictures': 'C10 mapping pictures',
    'c10-history-pictures': 'C10 history pictures',
    'c10-jobs-pictures': 'C10 jobs pictures',
    'c10-import-pictures': 'C10 import pictures',
    'c10-webhook-pictures': 'C10 webhook pictures',
}

def remap(value, workspace):
    if isinstance(value, dict):
        return {k: remap(v, workspace) for k, v in value.items()}
    if isinstance(value, list):
        return [remap(v, workspace) for v in value]
    if isinstance(value, str):
        try:
            UUID(value)
        except ValueError:
            return value
        return str(UUID(bytes=sha256(f'guide:C10:{workspace}:{value}'.encode()).digest()[:16], version=4))
    return value

if __name__ == '__main__':
    for workspace in WORKSPACES:
        target = DEST / workspace / 'docs'
        target.mkdir(parents=True, exist_ok=True)
        for source in (ROOT / 'guide/samples/data/docs').glob('*.json'):
            (target / source.name).write_text(json.dumps(remap(json.loads(source.read_text()), workspace), ensure_ascii=False) + '\n')
    print(f'Prepared {len(WORKSPACES)} isolated copies of the public docs set; no instance calls.')
