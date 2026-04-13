import re, os

vault_dir = os.path.join(os.path.dirname(__file__), 'LexAI_Vault')

with open(os.path.join(vault_dir, 'SRPL_premium_parse.md'), 'r') as f:
    text = f.read()

original_len = len(text)

# === STEP 1: Remove page separator lines (---) ===
text = re.sub(r'^---\s*$', '', text, flags=re.MULTILINE)

# === STEP 2: Remove garbled headers/footers ===
# Patterns observed in the document:
# - "GURGAON" variants: GURGACN5, GURGAON, RGURGAON2, GURGAON 7, GURGAON d, GURGAON₂, etc.
# - "INFRA" / "INFRA N" / "SRIAN INFRA" fragments
# - "VRGACN" / "GURGACN" (OCR errors for GURGAON)
# - Random chars: "$r", "alleay    *", "C G P -", "a", "F", standalone digits
# - "COVER PAGE" marker
# - Page numbers as standalone lines
# - "SRIAN INFRA LLP" header on cover

# Garbled header/footer lines (full line matches)
garbled_patterns = [
    r'^\s*GURGAON\d*\s*$',                    # GURGAON, GURGAON2, GURGAON7
    r'^\s*GURGACN\d*\s*$',                    # GURGACN5
    r'^\s*RGURGAON\d*\s*$',                   # RGURGAON2
    r'^\s*\w?\s*GURGAON\s*\w?\s*$',           # (GURGAON)3, GURGAON d, etc.
    r'^\s*GURGAON\s*[₂₀¹₃₄₅₆₇₈₉]*\s*$',     # GURGAON₂
    r'^\s*\(?GURGAON\)?\s*\d*\s*$',           # (GURGAON)3
    r'^\s*INFRA\s*$',                          # standalone INFRA
    r'^\s*INFRA\s*N\s*$',                     # INFRA N
    r'^\s*VRGACN\s*$',                         # VRGACN
    r'^\s*SRIAN INFRA LLP\s*$',               # Cover header
    r'^\s*COVER PAGE\s*$',                     # Cover marker
    r'^\s*alleay\s*\*?\s*$',                   # garbled "alley"
    r'^\s*\$r\s*$',                            # random $r
    r'^\s*C\s*G\s*P\s*-\s*$',                 # CGP-
    r'^\s*F\s*$',                              # standalone F
    r'^\s*a\s*$',                              # standalone a (from VRGACN a)
    r'^\s*\*\s*$',                             # standalone *
    r'^\s*\d{1,2}\s*\(\s*GURGAON\s*\)\s*\d*\s*$',  # page numbers with GURGAON
    r'^\s+\d{1,2}\s*$',                        # standalone page numbers (indented)
    r'^\s*\d{1,3}\s*$',                         # standalone page numbers
    r'^\s*S\s*GURGAONE\s*$',                  # S GURGAONE
    r'^\s*CA\s+GURGAON\s+\w?\s*$',            # CA GURGAON d
    r'^\s+\d+\s+\(\s*GURGAON\s*\)\s*\d*\s*$', # 7 (GURGAON)
    r'^\s+GURGAON\s+\d+\s*$',                  # GURGAON 7
    r'^\s*\w?\s*INFRA\s*\w?\s*$',              # mixed INFRA fragments
    r'^\s*N\s*$',                               # standalone N (from INFRA N)
    r'^\s*FOF\s+ORIENTAL BANK.*$',             # garbled bank footer
    r'^\s*GURGAON\s*$',                        # plain GURGAON
]

for pattern in garbled_patterns:
    text = re.sub(pattern, '', text, flags=re.MULTILINE)

# === STEP 3: Remove garbled inline fragments ===
# "INFRA" embedded in mid-line noise
text = re.sub(r'\bINFRA\b', '', text)
text = re.sub(r'\bVRGACN\b', '', text)

# Remove "7 (GURGAON" type inline fragments
text = re.sub(r'\d+\s*\(\s*GURGAON\s*\)\s*', '', text)
text = re.sub(r'\d+\s*GURGAON\s*\d*', '', text)
text = re.sub(r'GURGAON\s*\d*', '', text)
text = re.sub(r'RGURGAON\d*', '', text)
text = re.sub(r'GURGACN\d*', '', text)

# === STEP 4: Remove excessive blank lines (3+ consecutive → 2) ===
text = re.sub(r'\n{4,}', '\n\n\n', text)

# === STEP 5: Trim leading/trailing whitespace per line ===
lines = text.split('\n')
lines = [l.rstrip() for l in lines]
text = '\n'.join(lines)

# Remove leading/trailing blank lines
text = text.strip() + '\n'

# === STEP 6: Remove single-character orphan lines ===
# These are OCR noise from page edges (d, s, n, m, R, S, x, P, etc.)
# But keep lines that are part of numbered lists like "a." "b."
text = re.sub(r'^\s*[a-zA-Z]\s*$', '', text, flags=re.MULTILINE)

# === STEP 7: Remove "COVER PAGE" markers ===
text = re.sub(r'^\s*\*?\s*COVER PAGE\s*\*?\s*$', '', text, flags=re.MULTILINE)

# === STEP 8: Remove standalone "I s" fragments ===
text = re.sub(r'^\s*I\s+s\s*$', '', text, flags=re.MULTILINE)

# === STEP 9: Remove phone numbers on standalone lines ===
text = re.sub(r'^\s*\d{10,}\s*$', '', text, flags=re.MULTILINE)

# === STEP 10: Collapse excessive blanks again after all removals ===
text = re.sub(r'\n{4,}', '\n\n', text)

# === STEP 11: Fix common OCR artifacts ===
text = re.sub(r'\bsever\b', 'sewer', text)          # "sever" → "sewer"
text = re.sub(r'\bIntcrcst\b', 'Interest', text)     # OCR error
text = re.sub(r'\bHomc Buycrs\b', 'Home Buyers', text)
text = re.sub(r'\bnccds\b', 'needs', text)
text = re.sub(r'\bOperatio na\b', 'Operational', text)
text = re.sub(r'\bCorpui dlion\b', 'Corporation', text)
text = re.sub(r'\bUharge\b', 'charge', text)
text = re.sub(r'\bmcd\b', 'MCD', text)

cleaned_len = len(text)
print(f"Original: {original_len} chars")
print(f"Cleaned:  {cleaned_len} chars")
print(f"Removed:  {original_len - cleaned_len} chars ({100*(original_len-cleaned_len)/original_len:.1f}%)")

out_path = os.path.join(vault_dir, 'SRPL_Resolution_Plan_Clean.md')
with open(out_path, 'w') as f:
    f.write(text)

print(f"Saved to: {out_path}")

# Show a sample of cleaned text (first 100 lines)
lines = text.split('\n')
print(f"\n--- First 80 lines of cleaned output ---")
for line in lines[:80]:
    print(line)