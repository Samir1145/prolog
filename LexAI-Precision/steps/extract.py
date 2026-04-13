"""Step 3: Extract structured facts from cleaned markdown using GPT-4o.

Supports two modes:
  1. Routed extraction: Uses PageIndex sections to make targeted GPT-4o calls
     per compliance category (Section 30, Section 29A, Financial).
  2. Full extraction: Sends entire document to GPT-4o in one call (original behavior).
"""
import json
import os
from pathlib import Path
from typing import Optional


# === Full-document prompt (original behavior) ===

PROMPT_TEMPLATE = """You are an expert in Indian Insolvency and Bankruptcy Code (IBC) 2016. I have parsed a Resolution Plan PDF (case: {case_id}).

Based on the document text below, extract ALL facts relevant to Section 30(2) compliance and Section 29A eligibility verification.

Return your output as a JSON object with this exact structure:

{{
  "section30_facts": {{
    "plan_id": "{case_id}",
    "cirp_cost_payment": "priority" | "non_priority" | "not_mentioned",
    "oc_payment": <number in Cr>,
    "liquidation_value_oc": <number in Cr>,
    "waterfall_value_oc": <number in Cr>,
    "dissenting_fc_payment": "yes" | "no" | "not_mentioned",
    "management_post_approval": "yes" | "no" | "not_mentioned",
    "supervision_mechanism": "yes" | "no" | "not_mentioned",
    "contravenes_any_law": "no" | "yes" | "conditional",
    "affidavit_29A_submitted": "yes" | "no" | "not_mentioned",
    "stakeholder_interest_statement": "yes" | "no" | "not_mentioned",
    "implementation_timeline_months": <number | null>,
    "earnest_money_submitted": "yes" | "no",
    "conditions_precedent_listed": "yes" | "no"
  }},
  "section29A_facts": {{
    "resolution_applicants": [
      {{
        "name": "<Resolution Applicant name from document>",
        "undischarged_insolvent": "yes" | "no",
        "wilful_defaulter": "yes" | "no",
        "npa_status": "none" | "over_one_year" | "under_one_year",
        "npa_overdue_paid": "yes" | "no" | "not_applicable",
        "convicted_offence": "yes" | "no",
        "disqualified_director": "yes" | "no",
        "prohibited_by_sebi": "yes" | "no",
        "involved_in_fraudulent_transactions": "yes" | "no",
        "guarantee_executed_for_cd": "yes" | "no",
        "guarantee_invoked": "yes" | "no",
        "guarantee_unpaid": "yes" | "no"
      }}
    ],
    "connected_persons": [
      {{
        "connected_to": "<RA name>",
        "name": "<connected person name>",
        "undischarged_insolvent": "yes" | "no",
        "wilful_defaulter": "yes" | "no",
        "npa_status": "none" | "over_one_year" | "under_one_year",
        "npa_overdue_paid": "yes" | "no" | "not_applicable",
        "convicted_offence": "yes" | "no",
        "disqualified_director": "yes" | "no",
        "prohibited_by_sebi": "yes" | "no",
        "involved_in_fraudulent_transactions": "yes" | "no"
      }}
    ]
  }},
  "financial_data": {{
    "total_claims_admitted_cr": <number>,
    "home_buyer_claims_cr": <number>,
    "financial_creditor_claims_cr": <number>,
    "operational_creditor_claims_cr": <number>,
    "cirp_cost_cr": <number>,
    "oc_liquidation_value_cr": <number>,
    "fc_liquidation_value_cr": <number>,
    "project_completion_cost_cr": <number>,
    "earnest_money_cr": <number>,
    "dtcp_dues_principal_cr": <number>,
    "payment_to_other_fcs_percentage": <number>,
    "fc_payment_percentage": <number or null>,
    "has_funding_arrangement": "yes" | "no" | "not_mentioned",
    "ra_covers_shortfall": "yes" | "no" | "not_mentioned",
    "home_buyer_delivery_guaranteed": "yes" | "no" | "not_mentioned",
    "implementation_timeline_months": <number or null>,
    "conditions_precedent_count": <number or null>,
    "dtcp_license_renewable": "yes" | "no" | "not_guaranteed" | "not_mentioned",
    "preferential_transactions_invalidation": "yes" | "pending" | "not_mentioned",
    "total_sources_cr": <number or null>,
    "total_uses_cr": <number or null>
  }},
  "compliance_notes": [
    "Specific observations about compliance gaps, conditional requirements, or ambiguities found in the document"
  ]
}}

IMPORTANT: Identify ALL connected persons, consortium partners, and related entities mentioned in the document. Include them in the connected_persons array even if full eligibility details are not explicitly stated.

Use "not_mentioned" when the document does not explicitly address a requirement.

Document text:
"""


# === Section-targeted prompts for routed extraction ===

SECTION30_PROMPT = """You are an expert in Indian Insolvency and Bankruptcy Code (IBC) 2016, specifically Section 30(2) compliance and Regulation 38.

I have extracted the RELEVANT SECTIONS from a Resolution Plan PDF (case: {case_id}) that address the terms of the resolution plan, conditions precedent, management restructuring, supervision mechanism, and financial arrangements.

Extract the following facts from the provided text. Use "not_mentioned" ONLY if the text genuinely does not address a requirement. If the text mentions something even partially, extract what you can.

Return a JSON object with this exact structure:

{{
  "section30_facts": {{
    "plan_id": "{case_id}",
    "cirp_cost_payment": "priority" | "non_priority" | "not_mentioned",
    "oc_payment": <number in Cr>,
    "liquidation_value_oc": <number in Cr>,
    "waterfall_value_oc": <number in Cr>,
    "dissenting_fc_payment": "yes" | "no" | "not_mentioned",
    "management_post_approval": "yes" | "no" | "not_mentioned",
    "supervision_mechanism": "yes" | "no" | "not_mentioned",
    "contravenes_any_law": "no" | "yes" | "conditional",
    "affidavit_29A_submitted": "yes" | "no" | "not_mentioned",
    "stakeholder_interest_statement": "yes" | "no" | "not_mentioned",
    "implementation_timeline_months": <number | null>,
    "earnest_money_submitted": "yes" | "no",
    "conditions_precedent_listed": "yes" | "no"
  }},
  "financial_data": {{
    "total_claims_admitted_cr": <number>,
    "home_buyer_claims_cr": <number>,
    "financial_creditor_claims_cr": <number>,
    "operational_creditor_claims_cr": <number>,
    "cirp_cost_cr": <number>,
    "oc_liquidation_value_cr": <number>,
    "fc_liquidation_value_cr": <number>,
    "project_completion_cost_cr": <number>,
    "earnest_money_cr": <number>,
    "dtcp_dues_principal_cr": <number>,
    "payment_to_other_fcs_percentage": <number>,
    "fc_payment_percentage": <number or null>,
    "has_funding_arrangement": "yes" | "no" | "not_mentioned",
    "ra_covers_shortfall": "yes" | "no" | "not_mentioned",
    "home_buyer_delivery_guaranteed": "yes" | "no" | "not_mentioned",
    "implementation_timeline_months": <number or null>,
    "conditions_precedent_count": <number or null>,
    "dtcp_license_renewable": "yes" | "no" | "not_guaranteed" | "not_mentioned",
    "preferential_transactions_invalidation": "yes" | "pending" | "not_mentioned",
    "total_sources_cr": <number or null>,
    "total_uses_cr": <number or null>
  }},
  "compliance_notes": [
    "Specific observations about compliance gaps, conditional requirements, or ambiguities found in these sections"
  ]
}}

Document sections:
"""


SECTION29A_PROMPT = """You are an expert in Indian Insolvency and Bankruptcy Code (IBC) 2016, specifically Section 29A eligibility verification.

I have extracted the RELEVANT SECTIONS from a Resolution Plan PDF (case: {case_id}) that describe the Resolution Applicant(s), Consortium Partners, and their eligibility information.

Extract ALL resolution applicants and connected persons with their Section 29A eligibility details. Be thorough — identify every entity mentioned in the context of the resolution applicant, including consortium members, group companies, and any persons or entities connected to the applicant.

IMPORTANT: Include consortium partners as connected persons even if the document does not provide full eligibility details for each. Use "no" for eligibility fields only when the document explicitly states the entity is not disqualified. If the document makes claims about eligibility (e.g., "the applicant is not a wilful defaulter"), extract those claims as stated.

Return a JSON object with this exact structure:

{{
  "section29A_facts": {{
    "resolution_applicants": [
      {{
        "name": "<Resolution Applicant name from document>",
        "undischarged_insolvent": "yes" | "no",
        "wilful_defaulter": "yes" | "no",
        "npa_status": "none" | "over_one_year" | "under_one_year",
        "npa_overdue_paid": "yes" | "no" | "not_applicable",
        "convicted_offence": "yes" | "no",
        "disqualified_director": "yes" | "no",
        "prohibited_by_sebi": "yes" | "no",
        "involved_in_fraudulent_transactions": "yes" | "no",
        "guarantee_executed_for_cd": "yes" | "no",
        "guarantee_invoked": "yes" | "no",
        "guarantee_unpaid": "yes" | "no"
      }}
    ],
    "connected_persons": [
      {{
        "connected_to": "<RA name>",
        "name": "<connected person name>",
        "undischarged_insolvent": "yes" | "no",
        "wilful_defaulter": "yes" | "no",
        "npa_status": "none" | "over_one_year" | "under_one_year",
        "npa_overdue_paid": "yes" | "no" | "not_applicable",
        "convicted_offence": "yes" | "no",
        "disqualified_director": "yes" | "no",
        "prohibited_by_sebi": "yes" | "no",
        "involved_in_fraudulent_transactions": "yes" | "no"
      }}
    ]
  }}
}}

Document sections:
"""


# === Main extraction function ===

def extract_facts(clean_md_path: Path, case_id: str, vault_dir: Path,
                  model: str = "gpt-4o",
                  sections_path: Optional[Path] = None) -> Path:
    """Extract structured IBC compliance facts using GPT-4o.

    If sections_path is provided and contains routed sections, makes
    2 focused GPT-4o calls (Section 30+Financial, Section 29A).
    Otherwise falls back to single full-document call.

    Returns path to facts JSON file.
    """
    api_key = os.environ.get('OPENAI_API_KEY')
    if not api_key:
        raise EnvironmentError("OPENAI_API_KEY not set in .env")

    from openai import OpenAI
    client = OpenAI(api_key=api_key)

    # Decide: routed or full extraction
    use_routed = False
    if sections_path and sections_path.exists():
        from steps.structure import gather_sections_for_route
        s30_text = gather_sections_for_route(sections_path, "section30")
        s29a_text = gather_sections_for_route(sections_path, "section29A")
        # Only use routed mode if we found sections for both routes
        if s30_text.strip() and s29a_text.strip():
            use_routed = True

    if use_routed:
        result = _extract_routed(clean_md_path, sections_path, case_id, client, model)
    else:
        result = _extract_full(clean_md_path, case_id, client, model)

    facts_path = vault_dir / f"{case_id}_facts.json"
    with open(facts_path, 'w') as f:
        json.dump(result, f, indent=4)

    ra_count = len(result.get('section29A_facts', {}).get('resolution_applicants', []))
    cp_count = len(result.get('section29A_facts', {}).get('connected_persons', []))
    mode = "routed" if use_routed else "full"
    print(f"  Extracted ({mode}): {ra_count} RAs, {cp_count} connected persons → {facts_path.name}")
    return facts_path


def _extract_routed(
    clean_md_path: Path,
    sections_path: Path,
    case_id: str,
    client,
    model: str,
) -> dict:
    """Make 2 focused GPT-4o calls using section-routed content."""
    from steps.structure import gather_sections_for_route

    # Gather section content for each route
    s30_text = gather_sections_for_route(sections_path, "section30")
    fin_text = gather_sections_for_route(sections_path, "financial")
    s29a_text = gather_sections_for_route(sections_path, "section29A")

    # Combine section30 + financial for the first call
    if s30_text and fin_text and s30_text != fin_text:
        combined_s30_text = s30_text + "\n\n---\n\n" + fin_text
    elif s30_text:
        combined_s30_text = s30_text
    elif fin_text:
        combined_s30_text = fin_text
    else:
        # Fallback: use full text if no sections matched
        with open(clean_md_path, 'r') as f:
            combined_s30_text = f.read()

    if not s29a_text.strip():
        with open(clean_md_path, 'r') as f:
            s29a_text = f.read()

    # Call 1: Section 30 + Financial data
    print(f"  Calling {model} for Section 30 + Financial facts (routed)...")
    s30_prompt = SECTION30_PROMPT.format(case_id=case_id) + combined_s30_text
    response_s30 = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": s30_prompt}],
        response_format={"type": "json_object"},
        temperature=0,
    )
    result_s30 = json.loads(response_s30.choices[0].message.content)

    # Call 2: Section 29A eligibility
    print(f"  Calling {model} for Section 29A eligibility facts (routed)...")
    s29a_prompt = SECTION29A_PROMPT.format(case_id=case_id) + s29a_text
    response_s29a = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": s29a_prompt}],
        response_format={"type": "json_object"},
        temperature=0,
    )
    result_s29a = json.loads(response_s29a.choices[0].message.content)

    # Merge results into standard schema
    merged = {
        "section30_facts": result_s30.get("section30_facts", {}),
        "section29A_facts": result_s29a.get("section29A_facts", {}),
        "financial_data": result_s30.get("financial_data", {}),
        "compliance_notes": result_s30.get("compliance_notes", []),
    }

    # Ensure plan_id is set
    if "plan_id" not in merged.get("section30_facts", {}):
        merged["section30_facts"]["plan_id"] = case_id

    return merged


def _extract_full(clean_md_path: Path, case_id: str, client, model: str) -> dict:
    """Original single-call extraction (unchanged from pre-PageIndex behavior)."""
    with open(clean_md_path, 'r') as f:
        full_text = f.read()

    prompt = PROMPT_TEMPLATE.format(case_id=case_id) + full_text

    print(f"  Sending full document to {model} for extraction...")
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0,
    )

    return json.loads(response.choices[0].message.content)