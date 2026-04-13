"""Step 1: Parse PDF with LlamaParse V2 → raw markdown + JSON + classification.

Supports V2 agent-mode parsing for higher fidelity, with automatic
fallback to V1 premium mode if V2 is unavailable.

Also supports document classification and PDF splitting via LlamaCloud APIs.
"""
import os
import json
import time
import asyncio
from pathlib import Path
from typing import Optional

from steps.schemas import IBC_CLASSIFY_RULES, IBC_SPLIT_CATEGORIES


_TERMINAL_OK = {"SUCCESS", "COMPLETED"}
_TERMINAL_ERR = {"FAILED", "ERROR", "CANCELLED"}


def _normalize_status(status) -> str:
    """Normalize a job status enum/string to upper-case for comparison."""
    s = str(status)
    if "." in s:
        s = s.rsplit(".", 1)[-1]
    return s.upper()


async def _llama_parse_v2(pdf_path: str, api_key: str, parse_mode: str = "parse_page_with_agent") -> dict:
    """Parse PDF using LlamaParse V2 SDK with agent mode."""
    from llama_parse import LlamaParse

    parser = LlamaParse(
        api_key=api_key,
        result_type="markdown",
        parse_mode=parse_mode,
    )
    docs = await parser.aget_json(pdf_path)
    return docs


async def _llama_parse_v1(pdf_path: str, api_key: str) -> dict:
    """Parse PDF using LlamaParse V1 SDK (premium mode fallback)."""
    from llama_cloud_services import LlamaParse

    parser = LlamaParse(
        api_key=api_key,
        result_type="markdown",
        premium_mode=True,
    )
    docs = await parser.aget_json(pdf_path)
    return docs


def _classify_document(pdf_path: str, api_key: str, rules: list) -> dict:
    """Classify document type using LlamaCloud Classify API."""
    from llama_cloud.client import LlamaCloud
    from llama_cloud import ClassifierRule

    client = LlamaCloud(token=api_key)

    with open(pdf_path, "rb") as f:
        file_obj = client.files.upload_file(upload_file=f)
    file_id = file_obj.id

    job = client.classifier.create_classify_job(
        file_ids=[file_id],
        rules=[ClassifierRule(**r) for r in rules],
        mode="FAST",
    )

    status = "PENDING"
    for _ in range(60):
        job_status = client.classifier.get_classify_job(job.id)
        status = _normalize_status(job_status.status)
        if status in _TERMINAL_OK or status in _TERMINAL_ERR:
            break
        time.sleep(2)

    if status not in _TERMINAL_OK:
        raise RuntimeError(f"Classify job {job.id} did not succeed: status={status}")

    results = client.classifier.get_classification_job_results(job.id)

    doc_type = "other"
    confidence = 0.0
    reasoning = ""

    if results.items:
        best = results.items[0]
        if best.result:
            doc_type = best.result.type or "other"
            confidence = best.result.confidence or 0.0
            reasoning = best.result.reasoning or ""

    return {
        "file_id": file_id,
        "type": doc_type,
        "confidence": confidence,
        "reasoning": reasoning,
    }


def _split_document(pdf_path: str, api_key: str, categories: list) -> dict:
    """Split concatenated PDF into logical document segments."""
    from llama_cloud.client import LlamaCloud
    from llama_cloud import SplitCategory, SplitDocumentInput

    client = LlamaCloud(token=api_key)

    with open(pdf_path, "rb") as f:
        file_obj = client.beta.upload_file(file=f, purpose="split")
    file_id = file_obj.id

    job = client.beta.create_split_job(
        categories=[SplitCategory(name=c["name"], description=c.get("description", "")) for c in categories],
        document_input=SplitDocumentInput(type="file_id", value=file_id),
    )

    status = "PENDING"
    job_result = None
    for _ in range(60):
        job_result = client.beta.get_split_job(job.id)
        status = _normalize_status(job_result.status)
        if status in _TERMINAL_OK or status in _TERMINAL_ERR:
            break
        time.sleep(2)

    if status not in _TERMINAL_OK:
        raise RuntimeError(f"Split job {job.id} did not succeed: status={status}")

    segments = []
    if job_result and job_result.result and job_result.result.segments:
        for seg in job_result.result.segments:
            pages = seg.pages or []
            segments.append({
                "category": seg.category,
                "pages": pages,
                "start_page": min(pages) if pages else None,
                "end_page": max(pages) if pages else None,
                "confidence_category": getattr(seg, "confidence_category", "high"),
            })

    return {
        "file_id": file_id,
        "segments": segments,
    }


def parse_pdf(pdf_path: str, case_id: str, vault_dir: Path,
              skip_memgraph: bool = False,
              neo4j_uri: str = "bolt://localhost:7687",
              neo4j_user: str = "", neo4j_pass: str = "",
              parse_mode: str = "parse_page_with_agent",
              do_classify: bool = True,
              do_split: bool = False) -> Path:
    """Parse PDF with LlamaParse, optionally classify and split.

    Args:
        pdf_path: Path to the PDF file.
        case_id: Case identifier.
        vault_dir: Output directory.
        skip_memgraph: Skip Memgraph load.
        neo4j_uri/user/pass: Memgraph credentials.
        parse_mode: LlamaParse V2 mode (default: parse_page_with_agent).
            Options: parse_page_with_agent, parse_document_with_agent,
            parse_page_with_llm, parse_page_with_lvm, premium (V1).
        do_classify: Run document classification (default: True).
        do_split: Run PDF splitting (default: False).

    Returns:
        Path to raw markdown file.
    """
    api_key = os.environ.get('LLAMA_CLOUD_API_KEY')
    if not api_key:
        raise EnvironmentError("LLAMA_CLOUD_API_KEY not set in .env")

    # === Parse ===
    print(f"  Uploading {pdf_path} ...")

    if parse_mode == "premium":
        # V1 fallback
        docs = asyncio.run(_llama_parse_v1(pdf_path, api_key))
    else:
        # V2 with specified mode
        try:
            docs = asyncio.run(_llama_parse_v2(pdf_path, api_key, parse_mode))
        except Exception as e:
            print(f"  [PARSE] V2 mode '{parse_mode}' failed ({e}), falling back to V1 premium")
            docs = asyncio.run(_llama_parse_v1(pdf_path, api_key))

    # Extract pages
    if isinstance(docs, list) and len(docs) > 0 and 'pages' in docs[0]:
        pages = docs[0]['pages']
    else:
        raise RuntimeError(f"Unexpected LlamaParse output format: {type(docs)}")

    all_md = []
    for page in pages:
        md = page.get('text', '') or page.get('md', '')
        all_md.append(md)

    raw_md_path = vault_dir / f"{case_id}_raw.md"
    raw_json_path = vault_dir / f"{case_id}_raw.json"

    with open(raw_md_path, 'w') as f:
        f.write('\n\n---\n\n'.join(all_md))

    with open(raw_json_path, 'w') as f:
        json.dump(docs, f, indent=4, default=str)

    total_chars = sum(len(p) for p in all_md)
    print(f"  Parsed {len(pages)} pages, {total_chars} chars → {raw_md_path.name}")

    # === Classify ===
    classification = None
    if do_classify:
        classification = _run_classify(pdf_path, api_key, vault_dir, case_id)

    # === Split (optional) ===
    split_result = None
    if do_split:
        split_result = _run_split(pdf_path, api_key, vault_dir, case_id)

    # === Save metadata ===
    metadata = {
        "case_id": case_id,
        "parse_mode": parse_mode,
        "pages": len(pages),
        "total_chars": total_chars,
        "classification": classification,
        "split": split_result,
    }
    metadata_path = vault_dir / f"{case_id}_metadata.json"
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2, default=str)

    # Optional: load into Memgraph
    if not skip_memgraph:
        try:
            _load_into_memgraph(all_md, case_id, neo4j_uri, neo4j_user, neo4j_pass)
        except Exception as e:
            print(f"  WARNING: Memgraph load failed: {e} (continuing without graph)")

    return raw_md_path


def _run_classify(pdf_path: str, api_key: str, vault_dir: Path, case_id: str) -> Optional[dict]:
    """Classify document using LlamaCloud Classify API."""
    try:
        result = _classify_document(pdf_path, api_key, IBC_CLASSIFY_RULES)

        class_data = {
            "document_type": result.get("type", "unknown"),
            "confidence": result.get("confidence", 0.0),
            "reasoning": result.get("reasoning", ""),
            "file_id": result.get("file_id"),
        }
        class_path = vault_dir / f"{case_id}_classification.json"
        with open(class_path, 'w') as f:
            json.dump(class_data, f, indent=2, default=str)

        print(f"  Classified as: {class_data['document_type']} (confidence: {class_data['confidence']:.2f})")
        return class_data

    except Exception as e:
        print(f"  [CLASSIFY] WARNING: Classification failed ({e}), continuing without classification")
        return None


def _run_split(pdf_path: str, api_key: str, vault_dir: Path, case_id: str) -> Optional[dict]:
    """Split concatenated PDF using LlamaCloud Split API."""
    try:
        result = _split_document(pdf_path, api_key, IBC_SPLIT_CATEGORIES)

        segments = result.get("segments", [])
        split_path = vault_dir / f"{case_id}_split.json"
        with open(split_path, 'w') as f:
            json.dump(result, f, indent=2, default=str)

        print(f"  Split: {len(segments)} segments → {split_path.name}")
        for seg in segments:
            sp = seg.get('start_page', '?')
            ep = seg.get('end_page', '?')
            cat_conf = seg.get('confidence_category', 'unknown')
            print(f"    {seg['category']}: pages {sp}-{ep} (conf: {cat_conf})")
        return result

    except Exception as e:
        print(f"  [SPLIT] WARNING: Split failed ({e}), continuing without splitting")
        return None


def _load_into_memgraph(pages_md: list, case_id: str, uri: str, user: str, password: str):
    """Load parsed text into Memgraph as a Document node."""
    from neo4j import GraphDatabase
    driver = GraphDatabase.driver(uri, auth=(user, password))
    full_text = '\n\n'.join(pages_md)
    with driver.session() as session:
        session.run(
            "MERGE (d:Document {name: $name}) SET d.text = $text",
            name=case_id, text=full_text,
        )
    driver.close()
    print(f"  Loaded into Memgraph as Document('{case_id}')")


def get_document_type(vault_dir: Path, case_id: str) -> str:
    """Read document classification result. Returns 'resolution-plan' as default."""
    class_path = vault_dir / f"{case_id}_classification.json"
    if class_path.exists():
        with open(class_path, 'r') as f:
            data = json.load(f)
        return data.get("document_type", "resolution-plan")
    return "resolution-plan"


def get_split_segments(vault_dir: Path, case_id: str) -> list:
    """Read PDF split segments. Returns empty list if no split was done."""
    split_path = vault_dir / f"{case_id}_split.json"
    if split_path.exists():
        with open(split_path, 'r') as f:
            data = json.load(f)
        return data.get("segments", [])
    return []
