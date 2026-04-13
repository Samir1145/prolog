#!/usr/bin/env python3
"""LexAI-Precision: IBC Resolution Plan Compliance Pipeline

Usage:
    python pipeline.py <pdf_path> [options]

Steps:
    1. parse     — LlamaParse V2 PDF → raw markdown + classification + split
    2. clean     — Strip OCR noise (generic + YAML patterns)
    3. structure — PageIndex document structuring (section tree)
    4. extract   — Structured fact extraction (GPT-4o, LlamaExtract, or hybrid)
    5. prolog    — Generate Prolog facts + run compliance checks
    6. graph     — Load facts into Memgraph knowledge graph
    7. report    — Generate compliance report markdown

LlamaParse V2 Features:
    --parse-mode    Agent-mode parsing for higher fidelity (default: parse_page_with_agent)
    --no-classify   Skip document classification (classify runs by default)
    --split         Run PDF splitting for concatenated documents

Extraction Backends:
    --extract-mode gpt4o           GPT-4o extraction (default, section-routed or full)
    --extract-mode llama_extract   LlamaExtract schema-based extraction with confidence scores
    --extract-mode hybrid          Run both backends, merge results with confidence weighting
"""
import argparse
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

from dotenv import load_dotenv


STEPS = ['parse', 'clean', 'structure', 'extract', 'prolog', 'graph', 'report']


def derive_case_id(pdf_path: str) -> str:
    """Derive case identifier from PDF filename."""
    stem = Path(pdf_path).stem
    return stem.lower().replace(' ', '_').replace('-', '_')


@dataclass
class Step:
    """Declarative definition of a pipeline step.

    Attributes:
        name: Human-readable label used in log prefixes.
        output: Path produced by the step (used for caching and cache-miss errors).
        runner: Callable that executes the step. Should accept no args and use
            closures over ``args``/paths. Must return a Path or None.
        soft_fail: If True, a runner exception is logged as a warning instead of
            aborting the pipeline. Useful for steps like ``graph`` and ``structure``
            that have downstream fallbacks.
        on_soft_fail: Optional callable invoked after a soft failure, e.g. to
            write a skip-sentinel.
        skip_when: Optional callable returning True to skip the step entirely
            (e.g. ``--skip-memgraph``).
    """

    name: str
    output: Optional[Path]
    runner: Callable[[], Optional[Path]]
    soft_fail: bool = False
    on_soft_fail: Optional[Callable[[Exception], None]] = None
    skip_when: Optional[Callable[[], bool]] = None


def run_pipeline(steps: list[Step], start_idx: int) -> None:
    """Execute the pipeline, respecting ``--from`` caching semantics.

    For each step:
      - If the step's index is >= start_idx, run it (or handle a skip/soft-fail).
      - Otherwise, require its cached output to exist.
    """
    for idx, step in enumerate(steps):
        label = step.name.upper()
        if step.skip_when and step.skip_when():
            print(f"[{label}] Skipped.\n")
            continue

        if idx >= start_idx:
            print(f"[{label}] Running...")
            try:
                step.runner()
            except Exception as e:
                if step.soft_fail:
                    print(f"[{label}] WARNING: {e} (continuing)")
                    if step.on_soft_fail:
                        step.on_soft_fail(e)
                else:
                    print(f"[{label}] FAILED: {e}")
                    sys.exit(1)
            print(f"[{label}] Done.\n")
        else:
            if step.output is not None and not step.output.exists():
                print(f"[{label}] Cached file not found: {step.output}")
                print("  Re-run without --from or run this step first.")
                sys.exit(1)
            cache_name = step.output.name if step.output else "cached"
            print(f"[{label}] Using cached: {cache_name}\n")


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
    parser.add_argument('--pageindex-mode', dest='pageindex_mode',
                        choices=['auto', 'md_tree', 'pdf_tree', 'llm_split', 'skip'],
                        default='auto',
                        help='PageIndex structuring mode (default: auto)')
    parser.add_argument('--parse-mode', dest='parse_mode',
                        choices=['parse_page_with_agent', 'parse_document_with_agent',
                                  'parse_page_with_llm', 'parse_page_with_lvm', 'premium'],
                        default='parse_page_with_agent',
                        help='LlamaParse V2 mode (default: parse_page_with_agent)')
    parser.add_argument('--no-classify', dest='do_classify', action='store_false',
                        help='Skip document classification step')
    parser.add_argument('--split', dest='do_split', action='store_true',
                        help='Run PDF splitting step')
    parser.add_argument('--extract-mode', dest='extract_mode',
                        choices=['gpt4o', 'llama_extract', 'hybrid'],
                        default='gpt4o',
                        help='Extraction backend (default: gpt4o). Options: gpt4o, llama_extract, hybrid')
    parser.add_argument('--vault', default='LexAI_Vault',
                        help='Output vault directory (default: LexAI_Vault)')
    parser.add_argument('--prolog-dir', default='prolog',
                        help='Prolog rules directory (default: prolog)')
    parser.add_argument('--verbose', action='store_true',
                        help='Print detailed progress')

    args = parser.parse_args()

    root = Path(__file__).parent
    vault_dir = root / args.vault
    prolog_dir = root / args.prolog_dir
    patterns_file = root / args.patterns

    vault_dir.mkdir(exist_ok=True)
    load_dotenv(root.parent / '.env')

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

    # Intermediate artefacts
    raw_md = vault_dir / f"{case_id}_raw.md"
    clean_md = vault_dir / f"{case_id}_clean.md"
    sections_json = vault_dir / f"{case_id}_sections.json"
    facts_json = vault_dir / f"{case_id}_facts.json"
    results_json = vault_dir / f"{case_id}_results.json"
    report_md = vault_dir / f"{case_id}_report.md"

    def run_parse():
        from steps.parse import parse_pdf
        parse_pdf(
            str(pdf_path), case_id, vault_dir,
            skip_memgraph=args.skip_memgraph,
            parse_mode=args.parse_mode,
            do_classify=args.do_classify,
            do_split=args.do_split,
        )

    def run_clean():
        from steps.clean import clean_markdown
        clean_markdown(raw_md, case_id, vault_dir, patterns_file)

    def run_structure():
        from steps.structure import structure_document
        structure_document(
            clean_md, case_id, vault_dir,
            pdf_path=pdf_path,
            model=args.model,
            pageindex_mode=args.pageindex_mode,
        )

    def structure_fallback(_exc):
        from steps.structure import _write_skip_sections
        _write_skip_sections(clean_md, sections_json, case_id)

    def run_extract():
        from steps.extract import extract_facts
        extract_facts(
            clean_md, case_id, vault_dir,
            model=args.model,
            sections_path=sections_json,
            pdf_path=pdf_path,
            extract_mode=args.extract_mode,
        )

    def run_prolog():
        from steps.prolog import run_prolog as _run
        _run(facts_json, case_id, vault_dir, prolog_dir)

    def run_graph():
        from steps.graph import load_into_memgraph
        load_into_memgraph(
            facts_json, case_id,
            os.environ.get('NEO4J_URI', 'bolt://localhost:7687'),
            os.environ.get('NEO4J_USER', ''),
            os.environ.get('NEO4J_PASS', ''),
            vault_dir=vault_dir,
        )

    def run_report():
        from steps.report import write_report
        write_report(results_json, facts_json, case_id, vault_dir)

    steps = [
        Step(name="parse", output=raw_md, runner=run_parse),
        Step(name="clean", output=clean_md, runner=run_clean),
        Step(name="structure", output=sections_json, runner=run_structure,
             soft_fail=True, on_soft_fail=structure_fallback),
        Step(name="extract", output=facts_json, runner=run_extract),
        Step(name="prolog", output=results_json, runner=run_prolog),
        Step(name="graph", output=None, runner=run_graph,
             soft_fail=True, skip_when=lambda: args.skip_memgraph),
        Step(name="report", output=report_md, runner=run_report),
    ]

    run_pipeline(steps, start_idx)

    print("=" * 50)
    print("Pipeline complete!")
    print(f"  Vault:  {vault_dir}")
    print(f"  Report: {report_md}")
    print("")


if __name__ == '__main__':
    main()
