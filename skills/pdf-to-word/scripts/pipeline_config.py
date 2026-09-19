"""Workspace paths and optional, source-bound review settings."""
import hashlib
import json
import os
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
REPOSITORY = next((p for p in PROJECT.parents if (p / '.git').exists()), PROJECT)
ROOT = Path(os.environ.get('PDF_WORD_WORKSPACE', Path.cwd())).expanduser().resolve()
INPUT = ROOT / 'input'
OUT = ROOT / 'output'
WORK = ROOT / 'work' / 'batch'
MODELS = Path(os.environ.get('PDF_WORD_MODELS', ROOT / 'models')).expanduser().resolve()
VALIDATOR = Path(os.environ.get('DOCX_VALIDATOR', Path.home() / '.trae/skills/docx/scripts/office/validate.py')).expanduser()

def require_external(path, label='Workspace'):
    path = path.resolve()
    if path == REPOSITORY or REPOSITORY in path.parents or path == PROJECT or PROJECT in path.parents:
        raise ValueError(f'{label} must be outside the skill repository; set PDF_WORD_WORKSPACE/PDF_WORD_MODELS to task-local paths')
    return path

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def source(stem):
    require_external(ROOT)
    if Path(stem).name != stem or stem in {'.', '..'}:
        raise ValueError('Expected a PDF basename inside input/')
    path = INPUT / f'{stem}.pdf'
    if not path.is_file():
        raise FileNotFoundError(path)
    return path

def profile(stem):
    path = ROOT / 'config' / 'overrides.json'
    config = json.loads(path.read_text()) if path.exists() else {}
    item = config.get(stem, {})
    if item and item.get('source_sha256') != sha(source(stem)):
        raise ValueError(f'{stem}: review settings must match the source SHA-256')
    return item

def word_path(stem):
    return OUT / f'{stem}_转换.docx'

def render_path(stem):
    return WORK / 'rendered' / f'{stem}_转换.pdf'

def assert_audit_current(stem):
    audit = json.loads((WORK / stem / 'audit.json').read_text())
    if audit['sha256'] != sha(source(stem)):
        raise ValueError(f'{stem}: audit belongs to a different source')
    if audit.get('word_sha256') != sha(word_path(stem)):
        raise ValueError(f'{stem}: Word changed after generation; rebuild before automatic audit')
    return audit
