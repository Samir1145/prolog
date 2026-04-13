"""Step 3: Extract structured facts from cleaned markdown using GPT-4o."""
import os
import json
from pathlib import Path


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
    "payment_to_other_fcs_percentage": <number>
  }},
  "compliance_notes": [
    "Specific observations about compliance gaps, conditional requirements, or ambiguities found in the document"
  ]
}}

IMPORTANT: Identify ALL connected persons, consortium partners, and related entities mentioned in the document. Include them in the connected_persons array even if full eligibility details are not explicitly stated.

Use "not_mentioned" when the document does not explicitly address a requirement.

Document text:
"""


def extract_facts(clean_md_path: Path, case_id: str, vault_dir: Path,
                  model: str = "gpt-4o") -> Path:
    """Extract structured IBC compliance facts using GPT-4o.

    Returns path to facts JSON file.
    """
    api_key = os.environ.get('OPENAI_API_KEY')
    if not api_key:
        raise EnvironmentError("OPENAI_API_KEY not set in .env")

    from openai import OpenAI
    client = OpenAI(api_key=api_key)

    with open(clean_md_path, 'r') as f:
        full_text = f.read()

    prompt = PROMPT_TEMPLATE.format(case_id=case_id) + full_text

    print(f"  Sending to {model} for structured extraction...")
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0,
    )

    result = json.loads(response.choices[0].message.content)

    facts_path = vault_dir / f"{case_id}_facts.json"
    with open(facts_path, 'w') as f:
        json.dump(result, f, indent=4)

    ra_count = len(result.get('section29A_facts', {}).get('resolution_applicants', []))
    cp_count = len(result.get('section29A_facts', {}).get('connected_persons', []))
    print(f"  Extracted: {ra_count} RAs, {cp_count} connected persons → {facts_path.name}")
    return facts_path