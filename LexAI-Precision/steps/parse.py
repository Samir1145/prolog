"""Step 1: Parse PDF with LlamaParse → raw markdown + JSON."""
import os
import asyncio
import json
from pathlib import Path


async def _llama_parse(pdf_path: str, api_key: str) -> dict:
    from llama_cloud_services import LlamaParse
    parser = LlamaParse(
        api_key=api_key,
        result_type='markdown',
        premium_mode=True,
    )
    docs = await parser.aget_json(pdf_path)
    return docs


def parse_pdf(pdf_path: str, case_id: str, vault_dir: Path, skip_memgraph: bool = False,
              neo4j_uri: str = "bolt://localhost:7687", neo4j_user: str = "", neo4j_pass: str = "") -> Path:
    """Parse PDF with LlamaParse, save raw markdown and JSON to vault.

    Returns path to raw markdown file.
    """
    api_key = os.environ.get('LLAMA_CLOUD_API_KEY')
    if not api_key:
        raise EnvironmentError("LLAMA_CLOUD_API_KEY not set in .env")

    print(f"  Uploading {pdf_path} ...")
    docs = asyncio.run(_llama_parse(pdf_path, api_key))

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

    print(f"  Parsed {len(pages)} pages, {sum(len(p) for p in all_md)} chars → {raw_md_path.name}")

    # Optional: load into Memgraph
    if not skip_memgraph:
        try:
            _load_into_memgraph(all_md, case_id, neo4j_uri, neo4j_user, neo4j_pass)
        except Exception as e:
            print(f"  WARNING: Memgraph load failed: {e} (continuing without graph)")

    return raw_md_path


def _load_into_memgraph(pages_md: list, case_id: str, uri: str, user: str, password: str):
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