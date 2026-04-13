"""Generic text cleaners that apply to any OCR'd PDF."""
import re


def remove_page_separators(text: str) -> str:
    """Remove --- page break lines."""
    return re.sub(r'^---\s*$', '', text, flags=re.MULTILINE)


def remove_standalone_page_numbers(text: str) -> str:
    """Remove lines that are just a page number (1-3 digits)."""
    return re.sub(r'^\s*\d{1,3}\s*$', '', text, flags=re.MULTILINE)


def remove_single_char_orphans(text: str) -> str:
    """Remove lines that are a single letter (OCR edge noise).
    Preserves list items like 'a.' or 'b)'."""
    return re.sub(r'^\s*[a-zA-Z]\s*$', '', text, flags=re.MULTILINE)


def remove_standalone_phone_numbers(text: str) -> str:
    """Remove lines that are just a phone number (10+ digits)."""
    return re.sub(r'^\s*\d{10,}\s*$', '', text, flags=re.MULTILINE)


def remove_cover_page_markers(text: str) -> str:
    """Remove COVER PAGE markers."""
    return re.sub(r'^\s*\*?\s*COVER PAGE\s*\*?\s*$', '', text, flags=re.MULTILINE)


def remove_i_s_fragments(text: str) -> str:
    """Remove 'I s' OCR artifacts."""
    return re.sub(r'^\s*I\s+s\s*$', '', text, flags=re.MULTILINE)


def collapse_blank_lines(text: str) -> str:
    """Collapse 4+ consecutive newlines down to 2."""
    return re.sub(r'\n{4,}', '\n\n', text)


def strip_trailing_whitespace(text: str) -> str:
    """Remove trailing whitespace from each line."""
    lines = text.split('\n')
    lines = [l.rstrip() for l in lines]
    return '\n'.join(lines)


def strip_outer_blanks(text: str) -> str:
    """Remove leading/trailing blank lines."""
    return text.strip() + '\n'


# Ordered list of generic cleaners, applied sequentially
GENERIC_CLEANERS = [
    remove_page_separators,
    remove_standalone_page_numbers,
    remove_single_char_orphans,
    remove_standalone_phone_numbers,
    remove_cover_page_markers,
    remove_i_s_fragments,
    collapse_blank_lines,
    strip_trailing_whitespace,
    strip_outer_blanks,
]


def apply_generic_cleaners(text: str) -> str:
    """Run all generic cleaners in order."""
    for cleaner in GENERIC_CLEANERS:
        text = cleaner(text)
    return text