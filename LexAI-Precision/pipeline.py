#!/usr/bin/env python3
"""LexAI-Precision: IBC Resolution Plan Compliance Pipeline

Usage:
    python pipeline.py <pdf_path> [options]

Steps:
    1. parse   — LlamaParse PDF → raw markdown
    2. clean   — Strip OCR noise (generic + YAML patterns)
    3. extract — GPT-4o structured fact extraction
    4. prolog  — Generate Prolog facts + run compliance checks
    5. graph   — Load facts into Memgraph knowledge graph
    6. report  — Generate compliance report markdown
"""
import argparse
import os
import sys
from pathlib import Path
from dotenv import load_dotenv


STEPS = ['parse', 'clean', 'extract', 'prolog', 'graph', 'report']


def derive_case_id(pdf_path: str) -> str:
    """Derive case identifier from PDF filename."""
    stem = Path(pdf_path).stem
    return stem.lower().replace(' ', '_').replace('-', '_')


def main():
    parser = argparse.ArgumentParser(description='LexAI-Precision IBC Compliance Pipeline')
    parser.add_argument('pdf_path', help='Path to Resolution Plan PDF')
    parser.add_argument('--from', dest='from_step', choices=STEPS,
                        help='Run from STEP onwards (using cached intermediates)')
    parser.add_argument('--skip-memgraph', action='store_true',
                        help='Skip Memgraph load step')
    parser.add_argument('--patterns', default='cleaning_patterns.yaml',
                        help='YAML file with cleaning patterns (default: cleaning_patterns.yaml)')
    parser.add_argument('--model', default='gpt-4o',
                        help='OpenAI model for extraction (default: gpt-4o)')
    parser.add_argument('--vault', default='LexAI_Vault',
                        help='Output vault directory (default: LexAI_Vault)')
    parser.add_argument('--prolog-dir', default='prolog',
                        help='Prolog rules directory (default: prolog)')
    parser.add_argument('--verbose', action='store_true',
                        help='Print detailed progress')

    args = parser.parse_args()

    # Resolve paths relative to this script
    root = Path(__file__).parent
    vault_dir = root / args.vault
    prolog_dir = root / args.prolog_dir
    patterns_file = root / args.patterns

    vault_dir.mkdir(exist_ok=True)

    # Load .env from project parent
    load_dotenv(root.parent / '.env')

    # Verify PDF exists
    pdf_path = Path(args.pdf_path)
    if not pdf_path.exists():
        print(f"ERROR: PDF not found: {args.pdf_path}")
        sys.exit(1)

    case_id = derive_case_id(str(pdf_path))
    start_idx = STEPS.index(args.from_step) if args.from_step else 0

    print(f"LexAI-Precision Pipeline")
    print(f"  PDF:    {pdf_path.name}")
    print(f"  Case:   {case_id}")
    print(f"  Start:  {STEPS[start_idx]}")
    print(f"  Vault:  {vault_dir}")
    print("")

    # Track intermediate file paths
    raw_md = vault_dir / f"{case_id}_raw.md"
    clean_md = vault_dir / f"{case_id}_clean.md"
    facts_json = vault_dir / f"{case_id}_facts.json"
    results_json = vault_dir / f"{case_id}_results.json"

    # Step 1: Parse
    if start_idx <= 0:
        print("[PARSE] Running LlamaParse...")
        try:
            from steps.parse import parse_pdf
            raw_md = parse_pdf(
                str(pdf_path), case_id, vault_dir,
                skip_memgraph=args.skip_memgraph,
            )
        except Exception as e:
            print(f"[PARSE] FAILED: {e}")
            sys.exit(1)
        print("[PARSE] Done.\n")
    elif not raw_md.exists():
        print(f"[PARSE] Cached file not found: {raw_md}")
        print(f"  Re-run without --from or run parse step first.")
        sys.exit(1)
    else:
        print(f"[PARSE] Using cached: {raw_md.name}\n")

    # Step 2: Clean
    if start_idx <= 1:
        print("[CLEAN] Running text cleaners...")
        try:
            from steps.clean import clean_markdown
            clean_md = clean_markdown(raw_md, case_id, vault_dir, patterns_file)
        except Exception as e:
            print(f"[CLEAN] FAILED: {e}")
            sys.exit(1)
        print("[CLEAN] Done.\n")
    elif not clean_md.exists():
        print(f"[CLEAN] Cached file not found: {clean_md}")
        sys.exit(1)
    else:
        print(f"[CLEAN] Using cached: {clean_md.name}\n")

    # Step 3: Extract
    if start_idx <= 2:
        print("[EXTRACT] Running GPT-4o fact extraction...")
        try:
            from steps.extract import extract_facts
            facts_json = extract_facts(clean_md, case_id, vault_dir, model=args.model)
        except Exception as e:
            print(f"[EXTRACT] FAILED: {e}")
            sys.exit(1)
        print("[EXTRACT] Done.\n")
    elif not facts_json.exists():
        print(f"[EXTRACT] Cached file not found: {facts_json}")
        sys.exit(1)
    else:
        print(f"[EXTRACT] Using cached: {facts_json.name}\n")

    # Step 4: Prolog
    if start_idx <= 3:
        print("[PROLOG] Generating facts and running compliance checks...")
        try:
            from steps.prolog import run_prolog
            results_json = run_prolog(facts_json, case_id, vault_dir, prolog_dir)
        except Exception as e:
            print(f"[PROLOG] FAILED: {e}")
            sys.exit(1)
        print("[PROLOG] Done.\n")
    elif not results_json.exists():
        print(f"[PROLOG] Cached file not found: {results_json}")
        sys.exit(1)
    else:
        print(f"[PROLOG] Using cached: {results_json.name}\n")

    # Step 5: Graph (Memgraph knowledge graph)
    if start_idx <= 4 and not args.skip_memgraph:
        print("[GRAPH] Loading into Memgraph knowledge graph...")
        try:
            from steps.graph import load_into_memgraph
            neo4j_uri = os.environ.get('NEO4J_URI', 'bolt://localhost:7687')
            neo4j_user = os.environ.get('NEO4J_USER', '')
            neo4j_pass = os.environ.get('NEO4J_PASS', '')
            load_into_memgraph(facts_json, case_id, neo4j_uri, neo4j_user, neo4j_pass,
                               vault_dir=vault_dir)
        except Exception as e:
            print(f"[GRAPH] WARNING: {e} (continuing without graph)")
        print("[GRAPH] Done.\n")
    elif args.skip_memgraph:
        print("[GRAPH] Skipped (--skip-memgraph)\n")
    else:
        print("[GRAPH] Using cached (already loaded)\n")

    # Step 6: Report
    if start_idx <= 5:
        print("[REPORT] Generating compliance report...")
        try:
            from steps.report import write_report
            report_path = write_report(results_json, facts_json, case_id, vault_dir)
        except Exception as e:
            print(f"[REPORT] FAILED: {e}")
            sys.exit(1)
        print("[REPORT] Done.\n")
    else:
        print("[REPORT] Skipped.\n")

    # Summary
    print("=" * 50)
    print("Pipeline complete!")
    print(f"  Vault:  {vault_dir}")
    print(f"  Report: {vault_dir / f'{case_id}_report.md'}")
    print("")


if __name__ == '__main__':
    main()