"""Single source of truth for IBC compliance facts schema.

This module defines:

1. Pydantic models for the facts payload returned by extraction backends.
2. The JSON Schema derived from those models (fed to LlamaExtract).
3. Classifier rules and split categories used by LlamaCloud.
4. A ``build_prompt`` helper that generates GPT-4o prompts from the same
   schema, so both extraction paths target the identical shape.
"""
from __future__ import annotations

import json
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


# === Enum aliases ==========================================================

YesNo = Literal["yes", "no"]
YesNoNotMentioned = Literal["yes", "no", "not_mentioned"]
YesNoNotApplicable = Literal["yes", "no", "not_applicable"]
NPAStatus = Literal["none", "over_one_year", "under_one_year"]
CirpCostPayment = Literal["priority", "non_priority", "not_mentioned"]
ContravenesLaw = Literal["no", "yes", "conditional"]
DtcpLicenseRenewable = Literal["yes", "no", "not_guaranteed", "not_mentioned"]
PreferentialTxInvalidation = Literal["yes", "pending", "not_mentioned"]


class _IBCModel(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)


# === Section 30(2) / Regulation 38 =========================================

class Section30Facts(_IBCModel):
    """Facts relevant to Section 30(2) compliance and Regulation 38."""

    plan_id: str = Field(description="Case identifier")
    cirp_cost_payment: Optional[CirpCostPayment] = Field(
        default=None,
        description="Whether CIRP costs are paid on a priority basis",
    )
    oc_payment: Optional[float] = Field(
        default=None, description="Amount payable to operational creditors in Cr"
    )
    liquidation_value_oc: Optional[float] = Field(
        default=None, description="Liquidation value for operational creditors in Cr"
    )
    waterfall_value_oc: Optional[float] = Field(
        default=None, description="Waterfall distribution value for OCs in Cr"
    )
    dissenting_fc_payment: Optional[YesNoNotMentioned] = Field(
        default=None, description="Whether dissenting financial creditors are paid"
    )
    management_post_approval: Optional[YesNoNotMentioned] = Field(
        default=None,
        description="Whether a post-approval management restructuring plan exists",
    )
    supervision_mechanism: Optional[YesNoNotMentioned] = Field(
        default=None, description="Whether a supervision/monitoring mechanism is in place"
    )
    contravenes_any_law: Optional[ContravenesLaw] = Field(
        default=None, description="Whether the plan contravenes any law"
    )
    affidavit_29A_submitted: Optional[YesNoNotMentioned] = Field(
        default=None, description="Whether a Section 29A affidavit has been submitted"
    )
    stakeholder_interest_statement: Optional[YesNoNotMentioned] = Field(
        default=None, description="Whether a stakeholder interest statement is provided"
    )
    implementation_timeline_months: Optional[float] = Field(
        default=None, description="Implementation timeline in months"
    )
    earnest_money_submitted: Optional[YesNo] = Field(
        default=None, description="Whether earnest money has been submitted"
    )
    conditions_precedent_listed: Optional[YesNo] = Field(
        default=None, description="Whether conditions precedent are listed"
    )


# === Section 29A eligibility ==============================================

class ResolutionApplicant(_IBCModel):
    name: str = Field(description="Resolution Applicant name")
    undischarged_insolvent: Optional[YesNo] = None
    wilful_defaulter: Optional[YesNo] = None
    npa_status: Optional[NPAStatus] = None
    npa_overdue_paid: Optional[YesNoNotApplicable] = None
    convicted_offence: Optional[YesNo] = None
    disqualified_director: Optional[YesNo] = None
    prohibited_by_sebi: Optional[YesNo] = None
    involved_in_fraudulent_transactions: Optional[YesNo] = None
    guarantee_executed_for_cd: Optional[YesNo] = None
    guarantee_invoked: Optional[YesNo] = None
    guarantee_unpaid: Optional[YesNo] = None


class ConnectedPerson(_IBCModel):
    connected_to: str = Field(description="Name of the RA this person is connected to")
    name: str = Field(description="Connected person name")
    undischarged_insolvent: Optional[YesNo] = None
    wilful_defaulter: Optional[YesNo] = None
    npa_status: Optional[NPAStatus] = None
    npa_overdue_paid: Optional[YesNoNotApplicable] = None
    convicted_offence: Optional[YesNo] = None
    disqualified_director: Optional[YesNo] = None
    prohibited_by_sebi: Optional[YesNo] = None
    involved_in_fraudulent_transactions: Optional[YesNo] = None


class Section29AFacts(_IBCModel):
    """Facts relevant to Section 29A eligibility verification."""

    resolution_applicants: List[ResolutionApplicant] = Field(default_factory=list)
    connected_persons: List[ConnectedPerson] = Field(default_factory=list)


# === Financial data ========================================================

class FinancialData(_IBCModel):
    """Financial data from the resolution plan."""

    total_claims_admitted_cr: Optional[float] = None
    home_buyer_claims_cr: Optional[float] = None
    financial_creditor_claims_cr: Optional[float] = None
    operational_creditor_claims_cr: Optional[float] = None
    cirp_cost_cr: Optional[float] = None
    oc_liquidation_value_cr: Optional[float] = None
    fc_liquidation_value_cr: Optional[float] = None
    project_completion_cost_cr: Optional[float] = None
    earnest_money_cr: Optional[float] = None
    dtcp_dues_principal_cr: Optional[float] = None
    payment_to_other_fcs_percentage: Optional[float] = None
    fc_payment_percentage: Optional[float] = None
    has_funding_arrangement: Optional[YesNoNotMentioned] = None
    ra_covers_shortfall: Optional[YesNoNotMentioned] = None
    home_buyer_delivery_guaranteed: Optional[YesNoNotMentioned] = None
    implementation_timeline_months: Optional[float] = None
    conditions_precedent_count: Optional[float] = None
    dtcp_license_renewable: Optional[DtcpLicenseRenewable] = None
    preferential_transactions_invalidation: Optional[PreferentialTxInvalidation] = None
    total_sources_cr: Optional[float] = None
    total_uses_cr: Optional[float] = None


# === Root model ============================================================

class IBCFacts(_IBCModel):
    """Structured extraction of IBC Section 30(2), Section 29A eligibility, and
    financial facts from a Resolution Plan."""

    section30_facts: Section30Facts
    section29A_facts: Section29AFacts = Field(default_factory=Section29AFacts)
    financial_data: FinancialData = Field(default_factory=FinancialData)
    compliance_notes: List[str] = Field(
        default_factory=list,
        description="Specific observations about compliance gaps, conditional "
        "requirements, or ambiguities found in the document",
    )


# Derived artefacts used by the extraction backends.
IBC_FACTS_SCHEMA: dict = IBCFacts.model_json_schema()


# === LlamaCloud classify rules ============================================

IBC_CLASSIFY_RULES: list[dict] = [
    {
        "type": "resolution-plan",
        "description": (
            "A resolution plan under IBC Section 30(2) proposing revival and "
            "rehabilitation of a corporate debtor. Contains terms of plan, "
            "payment waterfall, conditions precedent, management restructuring, "
            "and earnest money details."
        ),
    },
    {
        "type": "information-memorandum",
        "description": (
            "An information memorandum (IM) or prospectus prepared by the "
            "resolution professional providing detailed information about the "
            "corporate debtor's financial position, assets, liabilities, and "
            "CIRP status for potential resolution applicants."
        ),
    },
    {
        "type": "valuation-report",
        "description": (
            "A valuation report under IBC Regulation 35 containing fair value "
            "and liquidation value assessments of the corporate debtor's "
            "assets, prepared by registered valuers."
        ),
    },
    {
        "type": "claim-form",
        "description": (
            "A claim form filed by creditors (financial, operational, or "
            "other) under IBC Section 9/15 asserting claims against the "
            "corporate debtor in the CIRP process."
        ),
    },
    {
        "type": "asset-memorandum",
        "description": (
            "An asset memorandum detailing the corporate debtor's properties, "
            "encumbrances, and asset status, often part of the information "
            "package for resolution applicants."
        ),
    },
    {
        "type": "litigation-memorandum",
        "description": (
            "A litigation memorandum listing pending and threatened legal "
            "proceedings involving the corporate debtor, prepared by the "
            "resolution professional."
        ),
    },
    {
        "type": "other",
        "description": (
            "Any other document not fitting the above categories, such as "
            "correspondence, orders, affidavits, or general filing documents."
        ),
    },
]


# === LlamaCloud split categories ==========================================

IBC_SPLIT_CATEGORIES: list[dict] = [
    {"name": "resolution-plan", "description": "Resolution plan under IBC Section 30(2)"},
    {"name": "information-memorandum", "description": "Information memorandum for resolution applicants"},
    {"name": "valuation-report", "description": "Valuation report under IBC Regulation 35"},
    {"name": "claim-forms", "description": "Claim forms filed by creditors"},
    {"name": "annexure", "description": "Annexures, appendices, or supplementary documents"},
    {"name": "correspondence", "description": "Letters, orders, notices, or general correspondence"},
]


# === Prompt construction ==================================================

_BASE_SYSTEM = (
    "You are an expert in Indian Insolvency and Bankruptcy Code (IBC) 2016. "
    "Extract structured compliance facts from the provided document text."
)

_SECTION_SCHEMAS = {
    "full": IBC_FACTS_SCHEMA,
    "section30": IBCFacts.model_json_schema()["$defs"].get("Section30Facts")
        if "$defs" in IBC_FACTS_SCHEMA
        else IBCFacts.model_json_schema(),
}


def _schema_for(routes: list[str]) -> dict:
    """Return a pruned JSON schema containing only the requested top-level routes.

    Routes are sub-keys of the root object: ``section30_facts``,
    ``section29A_facts``, ``financial_data``, ``compliance_notes``.
    """
    full = IBCFacts.model_json_schema()
    props = full.get("properties", {})
    pruned_props = {k: props[k] for k in routes if k in props}
    pruned_required = [k for k in full.get("required", []) if k in routes]

    return {
        "type": "object",
        "title": full.get("title", "IBCFactsSubset"),
        "properties": pruned_props,
        "required": pruned_required,
        "$defs": full.get("$defs", {}),
    }


def build_prompt(
    *,
    case_id: str,
    routes: list[str],
    instructions: str,
    context_label: str = "Document text",
) -> str:
    """Build a GPT-4o extraction prompt for the given routes.

    The prompt embeds the JSON Schema pruned to the requested routes, so the
    LLM is instructed against the exact same shape LlamaExtract uses.
    """
    schema = _schema_for(routes)
    schema_json = json.dumps(schema, indent=2)
    return (
        f"{_BASE_SYSTEM}\n\n"
        f"Case ID: {case_id}\n\n"
        f"{instructions}\n\n"
        f"Return a single JSON object that validates against this JSON Schema. "
        f"Use \"not_mentioned\" for string enum fields only when the document "
        f"genuinely does not address the requirement. Use null for numeric "
        f"fields when no value is stated.\n\n"
        f"JSON Schema:\n{schema_json}\n\n"
        f"{context_label}:\n"
    )


# Canned instruction blocks for the three prompt variants used by extract.py.

FULL_INSTRUCTIONS = (
    "Based on the document text below, extract ALL facts relevant to Section "
    "30(2) compliance and Section 29A eligibility verification. Identify every "
    "resolution applicant, consortium partner, and connected person mentioned "
    "in the document."
)

SECTION30_INSTRUCTIONS = (
    "The text below contains the sections of the Resolution Plan that address "
    "the terms of the plan, conditions precedent, management restructuring, "
    "supervision mechanism, and financial arrangements. Extract the Section "
    "30(2) / Regulation 38 facts and all financial data. If the text mentions "
    "something even partially, extract what you can."
)

SECTION29A_INSTRUCTIONS = (
    "The text below contains the sections of the Resolution Plan that "
    "describe the Resolution Applicant(s), Consortium Partners, and their "
    "eligibility information. Extract ALL resolution applicants and connected "
    "persons with their Section 29A eligibility details. Include consortium "
    "partners as connected persons even if full eligibility details are not "
    "explicitly stated."
)
