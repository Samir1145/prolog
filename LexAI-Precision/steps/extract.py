"""Step 4: Extract structured facts from cleaned markdown.

Supports three extraction backends:
  1. gpt4o (default): Routed or full GPT-4o extraction via OpenAI API.
  2. llama_extract: Schema-based extraction via LlamaExtract API with
     confidence scores and citation support.
  3. hybrid: Both backends, merging results with confidence-weighted selection.

The Pydantic models in ``steps.schemas`` are the single source of truth for
the facts payload. Both backends target the same schema, and GPT-4o
responses are validated against the ``IBCFacts`` model before being written
out.
"""
import json
import os
import time
from pathlib import Path
from typing import Optional

from pydantic import ValidationError

from steps.schemas import (
    FULL_INSTRUCTIONS,
    IBC_FACTS_SCHEMA,
    IBCFacts,
    SECTION29A_INSTRUCTIONS,
    SECTION30_INSTRUCTIONS,
    build_prompt,
)


# === LlamaExtract backend ===

def _extract_llama(pdf_path: str, case_id: str, vault_dir: Path,
                    extract_mode: str = "BALANCED") -> dict:
    """Extract structured IBC facts using LlamaExtract API with confidence scores.

    Args:
        pdf_path: Path to the original PDF file.
        case_id: Case identifier.
        vault_dir: Output directory.
        extract_mode: LlamaExtract mode (FAST, BALANCED, PREMIUM, MULTIMODAL).

    Returns:
        Dict with extracted facts and confidence scores.
    """
    api_key = os.environ.get('LLAMA_CLOUD_API_KEY')
    if not api_key:
        raise EnvironmentError("LLAMA_CLOUD_API_KEY not set in .env")

    from llama_cloud.client import LlamaCloud
    from llama_cloud import ExtractConfig, ExtractMode

    client = LlamaCloud(token=api_key)

    # Upload the PDF
    print(f"  Uploading {pdf_path} to LlamaExtract...")
    with open(pdf_path, "rb") as f:
        file_obj = client.files.upload_file(upload_file=f)
    file_id = file_obj.id
    print(f"  Uploaded: file_id={file_id}")

    # Configure extraction with confidence scores
    config = ExtractConfig(
        extraction_mode=ExtractMode(extract_mode),
        confidence_scores=True,
        cite_sources=True,
    )

    # Run stateless extraction
    print(f"  Running LlamaExtract ({extract_mode})...")
    job = client.llama_extract.extract_stateless(
        config=config,
        data_schema=IBC_FACTS_SCHEMA,
        file_id=file_id,
    )
    job_id = job.id
    print(f"  Job created: {job_id}")

    # Poll for completion using get_job (not get_run, which is for extraction agents)
    terminal_ok = {"SUCCESS", "COMPLETED"}
    terminal_err = {"ERROR", "FAILED", "CANCELLED"}
    status = "PENDING"
    for i in range(120):
        job_status = client.llama_extract.get_job(job_id)
        raw = str(job_status.status)
        status = raw.rsplit(".", 1)[-1].upper()
        if status in terminal_ok:
            break
        if status in terminal_err:
            raise RuntimeError(f"LlamaExtract failed: {getattr(job_status, 'error', status)}")
        if i % 5 == 0:
            print(f"  Poll {i}: status={status}")
        time.sleep(3)
    else:
        raise RuntimeError(f"LlamaExtract job {job_id} did not complete in time (last status={status})")

    # Fetch results using get_job_result
    resultset = client.llama_extract.get_job_result(job_id)
    extracted_data = resultset.data
    if extracted_data is None:
        raise RuntimeError("LlamaExtract returned no data")

    # Extraction metadata includes confidence scores
    extraction_metadata = resultset.extraction_metadata or {}

    # Save LlamaExtract raw output
    llama_raw_path = vault_dir / f"{case_id}_llama_extract.json"
    with open(llama_raw_path, 'w') as f:
        json.dump({
            "data": extracted_data,
            "metadata": extraction_metadata,
            "status": status,
        }, f, indent=2, default=str)

    print(f"  LlamaExtract complete → {llama_raw_path.name}")

    # Transform LlamaExtract output to standard facts schema
    facts = _transform_llama_to_facts(extracted_data, extraction_metadata, case_id)
    return facts


def _transform_llama_to_facts(extracted_data: dict, metadata: dict,
                               case_id: str) -> dict:
    """Transform LlamaExtract output to standard facts schema.

    LlamaExtract returns data matching the JSON Schema, plus confidence
    scores in metadata. This function normalizes the output to match
    the format expected by downstream Prolog and report steps.
    """
    # LlamaExtract data should already match our schema
    section30 = extracted_data.get("section30_facts", {})
    section29a = extracted_data.get("section29A_facts", {})
    financial = extracted_data.get("financial_data", {})
    notes = extracted_data.get("compliance_notes", [])

    # Ensure plan_id
    if "plan_id" not in section30 or not section30["plan_id"]:
        section30["plan_id"] = case_id

    # Extract confidence scores from metadata if available
    confidence_scores = {}
    if metadata and "confidence" in metadata:
        confidence_scores = metadata["confidence"]

    result = {
        "section30_facts": section30,
        "section29A_facts": section29a,
        "financial_data": financial,
        "compliance_notes": notes,
    }

    # Include confidence scores if available
    if confidence_scores:
        result["llama_confidence"] = confidence_scores

    return result


# === Hybrid extraction (LlamaExtract + GPT-4o) ===

_LLAMA_CONF_THRESHOLD = 0.8


def _is_missing(v) -> bool:
    return v is None or v == "" or v == "not_mentioned"


def _pick_value(lv, gv, conf):
    """Pick one value from LlamaExtract (lv) and GPT-4o (gv).

    Strategy:
      - If only one is present, return it.
      - If Llama confidence >= threshold, prefer Llama.
      - Otherwise prefer GPT when it has a real value.
      - Numeric fields never average — averaging corrupts financial figures.
    """
    l_missing = _is_missing(lv)
    g_missing = _is_missing(gv)
    if l_missing and g_missing:
        return lv if lv is not None else gv
    if l_missing:
        return gv
    if g_missing:
        return lv
    if isinstance(conf, (int, float)) and conf >= _LLAMA_CONF_THRESHOLD:
        return lv
    return gv


def _merge_flat(llama_map: dict, gpt_map: dict, conf_map: dict) -> dict:
    """Merge two flat {field: value} dicts using _pick_value."""
    out = {}
    conf_map = conf_map if isinstance(conf_map, dict) else {}
    for key in llama_map.keys() | gpt_map.keys():
        out[key] = _pick_value(
            llama_map.get(key),
            gpt_map.get(key),
            conf_map.get(key, 0.0),
        )
    return out


def _merge_entity_list(llama_list: list, gpt_list: list, key_fn) -> list:
    """Merge two lists of dict-entities keyed by key_fn, picking per-field."""
    l_map = {key_fn(e): e for e in llama_list}
    g_map = {key_fn(e): e for e in gpt_list}
    merged = []
    for k in l_map.keys() | g_map.keys():
        ll = l_map.get(k, {})
        gp = g_map.get(k, {})
        if ll and gp:
            merged.append(_merge_flat(ll, gp, {}))
        else:
            merged.append(ll or gp)
    return merged


def _merge_facts(llama_facts: dict, gpt_facts: dict) -> dict:
    """Merge LlamaExtract and GPT-4o results, preferring higher-confidence values."""
    merged = {
        "section30_facts": {},
        "section29A_facts": {},
        "financial_data": {},
        "compliance_notes": [],
    }

    llama_conf = llama_facts.get("llama_confidence", {}) or {}

    # section30_facts
    merged["section30_facts"] = _merge_flat(
        llama_facts.get("section30_facts", {}),
        gpt_facts.get("section30_facts", {}),
        llama_conf.get("section30_facts", {}),
    )
    if not merged["section30_facts"].get("plan_id"):
        merged["section30_facts"]["plan_id"] = (
            llama_facts.get("section30_facts", {}).get("plan_id")
            or gpt_facts.get("section30_facts", {}).get("plan_id")
            or ""
        )

    # section29A_facts
    s29a_llama = llama_facts.get("section29A_facts", {})
    s29a_gpt = gpt_facts.get("section29A_facts", {})
    merged["section29A_facts"]["resolution_applicants"] = _merge_entity_list(
        s29a_llama.get("resolution_applicants", []),
        s29a_gpt.get("resolution_applicants", []),
        lambda e: e.get("name", ""),
    )
    merged["section29A_facts"]["connected_persons"] = _merge_entity_list(
        s29a_llama.get("connected_persons", []),
        s29a_gpt.get("connected_persons", []),
        lambda e: f"{e.get('name','')}|{e.get('connected_to','')}",
    )

    # financial_data
    merged["financial_data"] = _merge_flat(
        llama_facts.get("financial_data", {}),
        gpt_facts.get("financial_data", {}),
        llama_conf.get("financial_data", {}),
    )

    # Merge compliance_notes (concatenate unique)
    llama_notes = llama_facts.get("compliance_notes", [])
    gpt_notes = gpt_facts.get("compliance_notes", [])
    seen = set()
    merged_notes = []
    for note in llama_notes + gpt_notes:
        if note not in seen:
            merged_notes.append(note)
            seen.add(note)
    merged["compliance_notes"] = merged_notes

    merged["extraction_mode"] = "hybrid"
    return merged


# === Main extraction function ===

def extract_facts(clean_md_path: Path, case_id: str, vault_dir: Path,
                  model: str = "gpt-4o",
                  sections_path: Optional[Path] = None,
                  pdf_path: Optional[Path] = None,
                  extract_mode: str = "gpt4o") -> Path:
    """Extract structured IBC compliance facts.

    Args:
        clean_md_path: Path to cleaned markdown file.
        case_id: Case identifier.
        vault_dir: Output directory.
        model: LLM model for GPT-4o extraction.
        sections_path: Path to sections JSON (for routed extraction).
        pdf_path: Path to original PDF (required for LlamaExtract).
        extract_mode: Extraction backend - 'gpt4o' (default), 'llama_extract', or 'hybrid'.

    Returns:
        Path to facts JSON file.
    """
    if extract_mode == "llama_extract":
        if not pdf_path or not pdf_path.exists():
            raise ValueError("pdf_path is required for LlamaExtract mode")
        result = _extract_llama(str(pdf_path), case_id, vault_dir)

    elif extract_mode == "hybrid":
        if not pdf_path or not pdf_path.exists():
            raise ValueError("pdf_path is required for hybrid extraction mode")
        # Run both extractors
        llama_facts = _extract_llama(str(pdf_path), case_id, vault_dir)
        gpt_facts = _extract_gpt(clean_md_path, case_id, model, sections_path)
        result = _merge_facts(llama_facts, gpt_facts)

    else:
        # Default: GPT-4o extraction
        result = _extract_gpt(clean_md_path, case_id, model, sections_path)

    facts_path = vault_dir / f"{case_id}_facts.json"
    with open(facts_path, 'w') as f:
        json.dump(result, f, indent=4)

    ra_count = len(result.get('section29A_facts', {}).get('resolution_applicants', []))
    cp_count = len(result.get('section29A_facts', {}).get('connected_persons', []))
    print(f"  Extracted ({extract_mode}): {ra_count} RAs, {cp_count} connected persons → {facts_path.name}")
    return facts_path


def _extract_gpt(clean_md_path: Path, case_id: str, model: str,
                  sections_path: Optional[Path] = None) -> dict:
    """GPT-4o extraction backend (routed or full).

    If sections_path is provided and contains routed sections, makes
    2 focused GPT-4o calls (Section 30+Financial, Section 29A).
    Otherwise falls back to single full-document call.
    """
    use_routed = False
    if sections_path and sections_path.exists():
        from steps.structure import gather_sections_for_route
        s30_text = gather_sections_for_route(sections_path, "section30")
        s29a_text = gather_sections_for_route(sections_path, "section29A")
        if s30_text.strip() and s29a_text.strip():
            use_routed = True

    api_key = os.environ.get('OPENAI_API_KEY')
    if not api_key:
        raise EnvironmentError("OPENAI_API_KEY not set in .env")

    from openai import OpenAI
    client = OpenAI(api_key=api_key)

    if use_routed:
        result = _extract_routed(clean_md_path, sections_path, case_id, client, model)
    else:
        result = _extract_full(clean_md_path, case_id, client, model)

    return _validate_facts(result, case_id)


def _call_gpt_json(client, model: str, prompt: str) -> dict:
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0,
    )
    return json.loads(response.choices[0].message.content)


def _validate_facts(result: dict, case_id: str) -> dict:
    """Validate an extracted facts dict against the IBCFacts Pydantic model.

    On success, returns the normalized model dump. On validation failure,
    logs the errors and returns the raw dict unchanged (so downstream steps
    can still run against partial data). Ensures ``plan_id`` is populated.
    """
    result = dict(result or {})
    result.setdefault("section30_facts", {})
    result.setdefault("section29A_facts", {})
    result.setdefault("financial_data", {})
    result.setdefault("compliance_notes", [])
    if not result["section30_facts"].get("plan_id"):
        result["section30_facts"]["plan_id"] = case_id

    try:
        model = IBCFacts.model_validate(result)
        return model.model_dump(exclude_none=False)
    except ValidationError as e:
        print(f"  [EXTRACT] WARNING: response failed schema validation ({len(e.errors())} errors)")
        for err in e.errors()[:5]:
            loc = ".".join(str(p) for p in err.get("loc", []))
            print(f"    - {loc}: {err.get('msg')}")
        return result


def _extract_routed(
    clean_md_path: Path,
    sections_path: Path,
    case_id: str,
    client,
    model: str,
) -> dict:
    """Make 2 focused GPT-4o calls using section-routed content."""
    from steps.structure import gather_sections_for_route

    s30_text = gather_sections_for_route(sections_path, "section30")
    fin_text = gather_sections_for_route(sections_path, "financial")
    s29a_text = gather_sections_for_route(sections_path, "section29A")

    if s30_text and fin_text and s30_text != fin_text:
        combined_s30_text = s30_text + "\n\n---\n\n" + fin_text
    elif s30_text:
        combined_s30_text = s30_text
    elif fin_text:
        combined_s30_text = fin_text
    else:
        with open(clean_md_path, 'r') as f:
            combined_s30_text = f.read()

    if not s29a_text.strip():
        with open(clean_md_path, 'r') as f:
            s29a_text = f.read()

    print(f"  Calling {model} for Section 30 + Financial facts (routed)...")
    s30_prompt = build_prompt(
        case_id=case_id,
        routes=["section30_facts", "financial_data", "compliance_notes"],
        instructions=SECTION30_INSTRUCTIONS,
        context_label="Document sections",
    ) + combined_s30_text
    result_s30 = _call_gpt_json(client, model, s30_prompt)

    print(f"  Calling {model} for Section 29A eligibility facts (routed)...")
    s29a_prompt = build_prompt(
        case_id=case_id,
        routes=["section29A_facts"],
        instructions=SECTION29A_INSTRUCTIONS,
        context_label="Document sections",
    ) + s29a_text
    result_s29a = _call_gpt_json(client, model, s29a_prompt)

    return {
        "section30_facts": result_s30.get("section30_facts", {}),
        "section29A_facts": result_s29a.get("section29A_facts", {}),
        "financial_data": result_s30.get("financial_data", {}),
        "compliance_notes": result_s30.get("compliance_notes", []),
    }


def _extract_full(clean_md_path: Path, case_id: str, client, model: str) -> dict:
    """Single-call extraction over the full cleaned document."""
    with open(clean_md_path, 'r') as f:
        full_text = f.read()

    prompt = build_prompt(
        case_id=case_id,
        routes=["section30_facts", "section29A_facts", "financial_data", "compliance_notes"],
        instructions=FULL_INSTRUCTIONS,
        context_label="Document text",
    ) + full_text

    print(f"  Sending full document to {model} for extraction...")
    return _call_gpt_json(client, model, prompt)
