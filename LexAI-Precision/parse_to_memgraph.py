import os
import asyncio
import json
from dotenv import load_dotenv
from llama_cloud import AsyncLlamaCloud
from neo4j import GraphDatabase

# Load environment variables from .env
load_dotenv()

API_KEY = os.environ.get("LLAMA_CLOUD_API_KEY")
NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.environ.get("NEO4J_USER", "")
NEO4J_PASS = os.environ.get("NEO4J_PASS", "")


async def parse_resolution_plan(file_path, page_indices=None):
    if not API_KEY:
        raise EnvironmentError("Set LLAMA_CLOUD_API_KEY in .env")

    client = AsyncLlamaCloud(api_key=API_KEY)

    print(f"--- Uploading {file_path} ---")
    with open(file_path, "rb") as f:
        file_obj = await client.files.create(file=f, purpose="parse")

    parse_kwargs = dict(
        file_id=file_obj.id,
        tier="agentic",
        version="latest",
        expand=["markdown", "json"],
    )
    if page_indices is not None:
        parse_kwargs["page_indices"] = page_indices

    print(f"--- Parsing (Agentic Mode) ---")
    result = await client.parsing.parse(**parse_kwargs)

    pages_md = []
    pages_json = []
    for page in result.markdown.pages:
        pages_md.append(page.markdown)

    json_data = result.json_content if hasattr(result, "json_content") else {}
    if not json_data:
        print("WARNING: No structured JSON returned from parse")

    # Save to LexAI_Vault
    os.makedirs("LexAI_Vault", exist_ok=True)

    base_name = os.path.splitext(os.path.basename(file_path))[0]

    md_path = f"LexAI_Vault/{base_name}.md"
    json_path = f"LexAI_Vault/{base_name}.json"

    with open(md_path, "w") as f:
        f.write("\n\n".join(pages_md))

    with open(json_path, "w") as f:
        json.dump(json_data, f, indent=4, default=str)

    print(f"\nMarkdown saved to: {md_path}")
    print(f"JSON saved to: {json_path}")

    return json_data


def load_into_memgraph(json_data, doc_name="unknown"):
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASS))

    with driver.session() as session:
        # Create document node
        session.run(
            "MERGE (d:Document {name: $name}) SET d.data = $data",
            name=doc_name,
            data=json.dumps(json_data, default=str),
        )
        print(f"Loaded document '{doc_name}' into Memgraph")

    driver.close()


async def main():
    PDF_PATH = os.environ.get("PDF_PATH", "soni_realtors_plan.pdf")

    if not os.path.exists(PDF_PATH):
        print(f"ERROR: File not found: {PDF_PATH}")
        return

    json_data = await parse_resolution_plan(PDF_PATH)
    base_name = os.path.splitext(os.path.basename(PDF_PATH))[0]
    load_into_memgraph(json_data, doc_name=base_name)

    print("\nDone! Parse -> Vault -> Memgraph pipeline complete.")


if __name__ == "__main__":
    asyncio.run(main())