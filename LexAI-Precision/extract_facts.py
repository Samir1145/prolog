import os, json
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

client = OpenAI(api_key=os.environ['OPENAI_API_KEY'])

vault_dir = os.path.join(os.path.dirname(__file__), 'LexAI_Vault')

with open(os.path.join(vault_dir, 'SRPL_premium_parse.md'), 'r') as f:
    full_text = f.read()

prompt = """You are an expert in Indian Insolvency and Bankruptcy Code (IBC) 2016. I have parsed a Resolution Plan PDF for Soni Realtors Private Limited (SRPL).

Based on the document text below, extract ALL facts relevant to Section 30(2) compliance and Section 29A eligibility verification.

Return your output as a JSON object with this exact structure:

{
  "section30_facts": {
    "plan_id": "srpl_plan",
    "cirp_cost_payment": "priority" | "non_priority" | "not_mentioned",
    "oc_payment": <number>,
    "liquidation_value_oc": <number>,
    "waterfall_value_oc": <number>,
    "dissenting_fc_payment": "yes" | "no" | "not_mentioned",
    "management_post_approval": "yes" | "no" | "not_mentioned",
    "supervision_mechanism": "yes" | "no" | "not_mentioned",
    "contravenes_any_law": "no" | "yes" | "conditional",
    "affidavit_29A_submitted": "yes" | "no" | "not_mentioned",
    "stakeholder_interest_statement": "yes" | "no" | "not_mentioned",
    "implementation_timeline_months": <number | null>,
    "earnest_money_submitted": "yes" | "no",
    "conditions_precedent_listed": "yes" | "no"
  },
  "section29A_facts": {
    "resolution_applicants": [
      {
        "name": "<RA name>",
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
      }
    ],
    "connected_persons": [
      {
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
      }
    ]
  },
  "financial_data": {
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
  },
  "compliance_notes": [
    "Specific observations about compliance gaps, conditional requirements, or ambiguities"
  ]
}

Use "not_mentioned" when the document does not explicitly address a requirement.

Document text:
""" + full_text

print("Sending to OpenAI GPT-4o for structured extraction...")
response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": prompt}],
    response_format={"type": "json_object"},
    temperature=0,
)

result = json.loads(response.choices[0].message.content)

with open(os.path.join(vault_dir, 'SRPL_structured_facts.json'), 'w') as f:
    json.dump(result, f, indent=4)

print(json.dumps(result, indent=2)[:4000])