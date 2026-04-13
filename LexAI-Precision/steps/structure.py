"""Step 2.5: Structure cleaned markdown into sections using PageIndex.

Inserts between clean and extract steps. Builds a hierarchical section tree
from the document, then routes sections to compliance categories
(section30, section29A, financial) for targeted GPT-4o calls.

Three structuring modes:
  1. pdf_tree — PageIndex PDF-based LLM TOC detection (requires PageIndex + deps)
  2. md_tree — PageIndex markdown-based header detection (requires # headers)
  3. llm_split — Lightweight: uses GPT-4o to extract TOC from first pages,
     then splits document at section boundaries (no PageIndex dependency)
  4. skip — No structuring, fall back to full-document extraction
"""
import json
import os
import re
import sys
from pathlib import Path
from typing import Optional


# === Section Routing Map ===

SECTION_ROUTES = {
    "section30": {
        "title_keywords": [
            "resolution plan",
            "conditions precedent",
            "effective date",
            "earnest money",
            "extinguishment",
            "management restructuring",
            "corporate and management",
            "binding offer",
            "reliefs",
            "concession",
            "monitoring",
            "supervision",
            "implementation",
            "stages of",
        ],
        "text_fallback": [
            "supervision mechanism",
            "monitoring committee",
            "dissenting",
            "implementation trustee",
        ],
    },
    "section29A": {
        "title_keywords": [
            "about resolution applicant",
            "about consortium",
            "resolution applicant",
            "consortium partner",
            "overview",
            "objectives of resolution plan",
        ],
        "text_fallback": [
            "connected person",
            "eligib",
            "disqualified",
            "wilful defaulter",
            "undischarged",
            "proposed by",
            "consortium",
        ],
    },
    "financial": {
        "title_keywords": [
            "source of fund",
            "financial model",
            "annexure",
            "payout",
            "creditor",
            "claims",
            "dtcp",
            "completion cost",
            "liquidation value",
            "financial statement",
            "project status",
            "financials",
        ],
        "text_fallback": [
            "inr cr",
            "crore",
            "payment to",
            "claims admitted",
        ],
    },
}


def structure_document(
    clean_md_path: Path,
    case_id: str,
    vault_dir: Path,
    *,
    pdf_path: Optional[Path] = None,
    model: str = "gpt-4o",
    pageindex_mode: str = "auto",
) -> Path:
    """Structure document into section tree.

    Args:
        clean_md_path: Path to cleaned markdown file.
        case_id: Case identifier.
        vault_dir: Output directory for artifacts.
        pdf_path: Original PDF file (needed for pdf_tree mode).
        model: LLM model for structuring.
        pageindex_mode: One of 'auto', 'md_tree', 'pdf_tree', 'llm_split', 'skip'.

    Returns:
        Path to sections JSON file ({case_id}_sections.json).
    """
    sections_path = vault_dir / f"{case_id}_sections.json"

    if pageindex_mode == "skip":
        _write_skip_sections(clean_md_path, sections_path, case_id)
        return sections_path

    try:
        if pageindex_mode == "pdf_tree":
            tree = _build_tree_from_pdf(pdf_path, model=model)
        elif pageindex_mode == "md_tree":
            tree = _build_tree_from_md(clean_md_path, model=model)
        elif pageindex_mode == "llm_split":
            tree = _build_tree_llm_split(clean_md_path, model=model)
        elif pageindex_mode == "auto":
            # Try LLM split first (no PageIndex dependency needed)
            tree = _build_tree_llm_split(clean_md_path, model=model)
            if not tree or len(tree) <= 1:
                # If LLM split failed, try PageIndex PDF
                if pdf_path and pdf_path.exists():
                    try:
                        tree = _build_tree_from_pdf(pdf_path, model=model)
                    except Exception:
                        pass
        else:
            raise ValueError(f"Unknown pageindex_mode: {pageindex_mode}")

        # Tag each node with compliance route(s)
        _tag_sections(tree, SECTION_ROUTES)

        # Save sections JSON
        output = {
            "case_id": case_id,
            "source_file": str(clean_md_path),
            "pageindex_mode": pageindex_mode,
            "structure": tree,
        }
        with open(sections_path, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)

        node_count = _count_nodes(tree)
        print(f"  Structured: {node_count} sections → {sections_path.name}")
        return sections_path

    except Exception as e:
        print(f"  [STRUCTURE] WARNING: Structuring failed ({e}), falling back to flat mode")
        _write_skip_sections(clean_md_path, sections_path, case_id)
        return sections_path


def gather_sections_for_route(sections_path: Path, route_name: str) -> str:
    """Collect text from all nodes tagged with a given route, concatenated.

    Returns empty string if no sections match the route.
    """
    with open(sections_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    tree = data.get("structure", [])
    flat = _flatten_tree(tree)
    texts = []
    for node in flat:
        if route_name in node.get("routes", []):
            node_text = node.get("text", "")
            if node_text.strip():
                texts.append(node_text.strip())
    return "\n\n---\n\n".join(texts) if texts else ""


# === Internal: LLM-based section splitting (no PageIndex dependency) ===

TOC_EXTRACT_PROMPT = """You are a document structure expert. I have a legal document (IBC Resolution Plan) that starts with a table of contents / index. Extract the section structure from the TOC.

Return a JSON array of section objects. Each object has:
- "title": the section title (exact text from the TOC)
- "page": the page number if available (integer or null)

Only include substantive sections (skip cover page, index itself). Include annexures.

Document text (first pages containing the TOC):
"""


def _build_tree_llm_split(clean_md_path: Path, model: str = "gpt-4o") -> list:
    """Use GPT-4o to extract TOC from document, then split text at section boundaries.

    This approach has no PageIndex dependency — it only uses the OpenAI API
    that's already required for the extract step.
    """
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise EnvironmentError("OPENAI_API_KEY not set")

    from openai import OpenAI
    client = OpenAI(api_key=api_key)

    with open(clean_md_path, "r", encoding="utf-8") as f:
        full_text = f.read()

    # Extract first ~3000 chars to find the TOC
    toc_region = full_text[:3000]
    prompt = TOC_EXTRACT_PROMPT + toc_region

    print(f"  Calling {model} for TOC extraction...")
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0,
    )
    result = json.loads(response.choices[0].message.content)

    # Parse the TOC entries
    toc_entries = result.get("sections", result.get("toc", []))
    if not toc_entries:
        print(f"  [STRUCTURE] No TOC found by LLM, returning single-node tree")
        return []

    # Split document at section boundaries
    tree = _split_text_by_toc(full_text, toc_entries)
    return tree


def _split_text_by_toc(full_text: str, toc_entries: list) -> list:
    """Split document text at section boundaries identified from the TOC.

    For each TOC entry, find the corresponding heading in the text body
    (skipping the TOC/index section itself) and extract everything until
    the next section heading.
    """
    lines = full_text.split("\n")

    # Find where the TOC/index ends — look for the first substantive
    # heading that appears AFTER the index table
    toc_end_line = 0
    for i, line in enumerate(lines):
        stripped = line.strip()
        # The TOC typically ends when we see lines that are NOT
        # just numbers, "S.No", "Description", or page references
        if stripped and not re.match(
            r'^(\d+\s|$|S\.No|Description|Page|S\.? ?No\.?|Cover|Index|\*|INDEX|\d+\s+\w+.*\d+$)',
            stripped
        ):
            # Check if this looks like a real heading (short line, not a table row)
            if len(stripped) < 100 and not re.search(r'\d{2,}', stripped):
                toc_end_line = i
                break
    # Fallback: skip first 60 lines (covers most TOC sections)
    if toc_end_line == 0:
        toc_end_line = 60

    # Build a list of (title, line_index) by searching for TOC titles AFTER the TOC
    section_starts = []  # (title, line_index)

    for entry in toc_entries:
        title = entry.get("title", "").strip()
        if not title:
            continue

        title_lower = title.lower().strip()
        # Extract core words (skip short words like "of", "for", "the")
        title_words = [w for w in re.split(r'[\s,]+', title_lower) if len(w) > 2]

        found_idx = None

        # Strategy 1: Exact title match in a short line (heading-like)
        for i in range(toc_end_line, len(lines)):
            line_stripped = lines[i].strip().lower()
            if title_lower == line_stripped:
                found_idx = i
                break

        # Strategy 2: Title is contained in a short line
        if found_idx is None:
            for i in range(toc_end_line, len(lines)):
                line_stripped = lines[i].strip()
                line_lower = line_stripped.lower()
                if title_lower in line_lower and len(line_stripped) < len(title) + 30:
                    found_idx = i
                    break

        # Strategy 3: Match first 2-3 significant words in a short line
        if found_idx is None and len(title_words) >= 2:
            pattern = " ".join(title_words[:3])
            for i in range(toc_end_line, len(lines)):
                line_stripped = lines[i].strip()
                line_lower = line_stripped.lower()
                if pattern in line_lower and len(line_stripped) < 80:
                    found_idx = i
                    break

        if found_idx is not None:
            section_starts.append((title, found_idx))

    # Sort by line index and deduplicate nearby matches
    section_starts.sort(key=lambda x: x[1])
    deduped = []
    for title, idx in section_starts:
        if not deduped or idx - deduped[-1][1] > 3:
            deduped.append((title, idx))
    section_starts = deduped

    # Extract text for each section
    tree = []
    for idx, (title, start_line) in enumerate(section_starts):
        end_line = section_starts[idx + 1][1] if idx + 1 < len(section_starts) else len(lines)
        section_text = "\n".join(lines[start_line:end_line]).strip()

        if section_text:
            tree.append({
                "title": title,
                "node_id": str(idx + 1).zfill(4),
                "text": section_text,
                "nodes": [],
            })

    # Add preamble text before first section
    if section_starts and section_starts[0][1] > toc_end_line + 5:
        preamble = "\n".join(lines[toc_end_line:section_starts[0][1]]).strip()
        if preamble:
            tree.insert(0, {
                "title": "Overview",
                "node_id": "0000",
                "text": preamble,
                "nodes": [],
            })

    return tree


# === Internal: PageIndex Integration ===

def _build_tree_from_pdf(pdf_path: Path, model: str = "gpt-4o") -> list:
    """Use PageIndex PDF mode to build hierarchical TOC tree."""
    _setup_pageindex_path()
    from pageindex.page_index import page_index_main
    from pageindex.utils import ConfigLoader

    user_opt = {
        "model": model,
        "if_add_node_id": "yes",
        "if_add_node_text": "yes",
        "if_add_node_summary": "no",
        "if_add_doc_description": "no",
    }
    opt = ConfigLoader().load(user_opt)
    tree_dict = page_index_main(str(pdf_path), opt)
    return tree_dict.get("structure", [])


def _build_tree_from_md(clean_md_path: Path, model: str = "gpt-4o") -> list:
    """Use PageIndex md_to_tree to build section tree from markdown.

    Note: Requires markdown headers (# ## ###) in the document.
    """
    import asyncio
    _setup_pageindex_path()
    from pageindex.page_index_md import md_to_tree

    result = asyncio.run(md_to_tree(
        md_path=str(clean_md_path),
        if_thinning=False,
        if_add_node_summary="no",
        if_add_node_text="yes",
        if_add_node_id="yes",
        model=model,
    ))
    return result.get("structure", [])


def _setup_pageindex_path() -> None:
    """Add PageIndex repo to sys.path if PAGEINDEX_ROOT is set."""
    pageindex_root = os.environ.get("PAGEINDEX_ROOT", "")
    if pageindex_root and pageindex_root not in sys.path:
        sys.path.insert(0, pageindex_root)


# === Internal: Section Routing ===

def _tag_sections(tree: list, routes: dict) -> None:
    """Walk the tree and tag each node with matching compliance categories."""
    for node in tree:
        title = node.get("title", "").lower()
        text_preview = node.get("text", "")[:500].lower()
        node["routes"] = []

        for route_name, patterns in routes.items():
            matched = False
            for kw in patterns["title_keywords"]:
                if kw in title:
                    node["routes"].append(route_name)
                    matched = True
                    break
            if not matched:
                for fm in patterns.get("text_fallback", []):
                    if fm in text_preview:
                        node["routes"].append(route_name)
                        break

        # Recurse into child nodes
        if node.get("nodes"):
            _tag_sections(node["nodes"], routes)


def _flatten_tree(tree: list) -> list:
    """Flatten nested tree into a flat list of all nodes."""
    result = []
    for node in tree:
        result.append(node)
        if node.get("nodes"):
            result.extend(_flatten_tree(node["nodes"]))
    return result


def _count_nodes(tree: list) -> int:
    """Count total nodes in tree (including nested)."""
    count = 0
    for node in tree:
        count += 1
        if node.get("nodes"):
            count += _count_nodes(node["nodes"])
    return count


def _write_skip_sections(clean_md_path: Path, sections_path: Path,
                         case_id: str) -> None:
    """Write a minimal sections file representing the entire document as one section.

    Used when structuring is unavailable or skipped. The extract step
    will fall back to full-document extraction.
    """
    with open(clean_md_path, "r", encoding="utf-8") as f:
        full_text = f.read()

    output = {
        "case_id": case_id,
        "source_file": str(clean_md_path),
        "pageindex_mode": "skip",
        "structure": [{
            "title": "Full Document",
            "node_id": "0001",
            "text": full_text,
            "routes": ["section30", "section29A", "financial"],
        }],
    }
    with open(sections_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"  Structured: fallback (full document) → {sections_path.name}")