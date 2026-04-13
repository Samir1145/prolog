"""Step 2: Clean parsed markdown using generic + YAML-driven patterns."""
import re
from pathlib import Path
import yaml
from cleaners.base import apply_generic_cleaners


def clean_markdown(raw_md_path: Path, case_id: str, vault_dir: Path,
                   patterns_file: Path = None) -> Path:
    """Clean OCR noise from parsed markdown.

    Returns path to cleaned markdown file.
    """
    with open(raw_md_path, 'r') as f:
        text = f.read()

    original_len = len(text)

    # 1. Apply generic cleaners (page breaks, orphans, blanks, etc.)
    text = apply_generic_cleaners(text)

    # 2. Apply YAML-driven patterns
    if patterns_file and patterns_file.exists():
        with open(patterns_file, 'r') as f:
            patterns = yaml.safe_load(f)
        text = _apply_yaml_patterns(text, patterns)

    # 3. Final collapse of blank lines
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = text.strip() + '\n'

    clean_md_path = vault_dir / f"{case_id}_clean.md"
    with open(clean_md_path, 'w') as f:
        f.write(text)

    removed = original_len - len(text)
    print(f"  Cleaned: {original_len} → {len(text)} chars ({removed} removed) → {clean_md_path.name}")
    return clean_md_path


def _apply_yaml_patterns(text: str, patterns: dict) -> str:
    """Apply header/footer, inline, and typo fix patterns from YAML config."""
    # Header/footer patterns (full-line removal)
    for entry in patterns.get('header_footer', []):
        pattern = entry['pattern']
        text = re.sub(pattern, '', text, flags=re.MULTILINE)

    # Inline patterns (within lines)
    for entry in patterns.get('inline', []):
        pattern = entry['pattern']
        text = re.sub(pattern, '', text)

    # Typo fixes
    for fix in patterns.get('typo_fixes', []):
        text = re.sub(fix['from'], fix['to'], text)

    return text