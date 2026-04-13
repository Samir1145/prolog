"""Step 5: Generate compliance report markdown for Obsidian vault."""
import json
import re
from pathlib import Path


DEFICIENCY_TEMPLATES = {
    "dissenting_fc_payment": {
        "section": "Second proviso to Section 30(2)(b)",
        "finding": "The plan does not address the statutory requirement to pay dissenting financial creditors an amount not less than what they would receive in liquidation.",
        "remedy": "Include an explicit provision for payment to dissenting financial creditors, at minimum equal to their liquidation value.",
    },
    "supervision_mechanism": {
        "section": "Section 30(2)(d)",
        "finding": "No monitoring committee, implementation trustee, or supervision framework is described in the plan.",
        "remedy": "Include a Monitoring Committee structure (typically: RP, RA representative, creditor representatives) with defined reporting obligations.",
    },
    "contravenes_any_law": {
        "section": "Section 30(2)(e)",
        "finding": "The plan has conditional compliance — its legality depends on external NCLT orders or regulatory actions that are not guaranteed.",
        "remedy": "Flag to NCLT for consideration. The plan should comply independently, not conditionally.",
    },
    "affidavit_29A_submitted": {
        "section": "Section 30(1)",
        "finding": "The affidavit confirming RA eligibility under Section 29A was not found in the document.",
        "remedy": "Verify the physical document for the affidavit. If present, update the extraction and re-run.",
    },
}


def write_report(results_json_path: Path, facts_json_path: Path, case_id: str,
                 vault_dir: Path) -> Path:
    """Generate a markdown compliance report.

    Returns path to report file.
    """
    with open(results_json_path, 'r') as f:
        results = json.load(f)
    with open(facts_json_path, 'r') as f:
        facts = json.load(f)

    s30 = facts['section30_facts']
    s29 = facts['section29A_facts']
    fin = facts['financial_data']
    notes = facts.get('compliance_notes', [])

    s30_output = results.get('section30_output', '')
    s29_output = results.get('section29A_output', '')

    # Parse Prolog output for PASS/FAIL lines
    compliance_rows = _parse_compliance_output(s30_output)

    # Build report
    report = []
    report.append(f"# Compliance Verification Report — {case_id}")
    report.append("")
    report.append(f"**Plan ID:** {s30['plan_id']}")
    report.append(f"**Verification Pipeline:** LlamaParse → GPT-4o → Prolog")
    report.append(f"**Date:** {_today()}")
    report.append("")

    # Section 29A
    report.append("## Section 29A: Resolution Applicant Eligibility")
    report.append("")
    for ra in s29.get('resolution_applicants', []):
        report.append(f"- **{ra['name']}**: {s29_output.strip() or 'N/A'}")
    for cp in s29.get('connected_persons', []):
        report.append(f"- **{cp['name']}** (connected to {cp['connected_to']}): checked")
    report.append("")

    # Section 30 compliance table
    report.append("## Section 30(2) & Regulation 38: Plan Compliance")
    report.append("")
    report.append("| Rule | Status | Value | Detail |")
    report.append("|---|---|---|---|")
    for row in compliance_rows:
        report.append(f"| {row['rule']} | **{row['status']}** | `{row['value']}` | {row['detail']} |")
    report.append("")

    overall = "COMPLIANT" if all(r['status'] == 'PASS' for r in compliance_rows) else "NOT COMPLIANT"
    fail_count = sum(1 for r in compliance_rows if r['status'] == 'FAIL')
    pass_count = sum(1 for r in compliance_rows if r['status'] == 'PASS')
    report.append(f"**OVERALL: {overall}** ({pass_count} PASS, {fail_count} FAIL)")
    report.append("")

    # Regulation 38 detailed check
    reg38_output = results.get('reg38_output', '')
    if reg38_output.strip():
        reg38_rows = _parse_compliance_output(reg38_output)
        if reg38_rows:
            report.append("## Regulation 38: Detailed Compliance")
            report.append("")
            report.append("| Rule | Status | Value | Detail |")
            report.append("|---|---|---|---|")
            for row in reg38_rows:
                report.append(f"| {row['rule']} | **{row['status']}** | `{row['value']}` | {row['detail']} |")
            report.append("")

    # Conditional compliance analysis
    cond_output = results.get('conditional_compliance_output', '')
    if cond_output.strip():
        report.append("## Conditional Compliance Analysis")
        report.append("")
        for line in cond_output.strip().split('\n'):
            line = line.strip()
            if line and not line.startswith('='):
                if line.startswith('PASS') or line.startswith('FAIL') or line.startswith('CONDITIONAL') or line.startswith('NOT ADDRESSED'):
                    report.append(f"- {line}")
                elif line.startswith('OVERALL'):
                    report.append(f"**{line}**")
                elif line.startswith('- ') or line.startswith('* '):
                    report.append(f"  {line}")
                elif line.startswith('Conditions') or line.startswith('Compliance') or line.startswith('Rule-by-rule'):
                    report.append(f"**{line}**")
        report.append("")

    # Section 29A(j) connected persons
    s29j_output = results.get('section29A_connected_output', '')
    if s29j_output.strip():
        report.append("## Section 29A(j): Connected Person Analysis")
        report.append("")
        # Parse connected person output
        for line in s29j_output.split('\n'):
            line = line.strip()
            if line.startswith('PASS:') or line.startswith('FAIL:') or line.startswith('INFO:') or line.startswith('RESULT:'):
                report.append(f"- {line}")
            elif line.startswith('Categorized') or line.startswith('Direct'):
                report.append(f"- {line}")
        report.append("")

    # Financial & Timeline validation
    fin_output = results.get('financial_output', '')
    if fin_output.strip():
        report.append("## Financial & Timeline Validation")
        report.append("")
        for line in fin_output.strip().split('\n'):
            line = line.strip()
            if line and not line.startswith('='):
                if line.startswith('PASS') or line.startswith('FAIL') or line.startswith('WARN') or line.startswith('INFO'):
                    report.append(f"- {line}")
                elif line.startswith('---'):
                    report.append(f"**{line.replace('---', '').strip()}**")
        report.append("")

    # Deficiency analysis
    failed_rules = [r for r in compliance_rows if r['status'] == 'FAIL']
    if failed_rules:
        report.append("## Deficiency Analysis")
        report.append("")
        for i, row in enumerate(failed_rules, 1):
            field = row.get('field', '')
            template = DEFICIENCY_TEMPLATES.get(field, {})
            section = template.get('section', row['rule'])
            finding = template.get('finding', f"Plan value: {row['value']}")
            remedy = template.get('remedy', 'Address this requirement in the resolution plan.')
            report.append(f"### {i}. {row['rule']} [FAIL]")
            report.append(f"**Section:** {section}")
            report.append(f"**Finding:** {finding}")
            report.append(f"**Remedy:** {remedy}")
            report.append("")

    # Financial summary
    report.append("## Financial Summary")
    report.append("")
    report.append("| Item | Amount (INR Cr) |")
    report.append("|---|---|")
    for key, label in [('total_claims_admitted_cr', 'Total Claims Admitted'),
                       ('home_buyer_claims_cr', 'Home Buyer Claims'),
                       ('financial_creditor_claims_cr', 'Financial Creditor Claims'),
                       ('operational_creditor_claims_cr', 'Operational Creditor Claims'),
                       ('cirp_cost_cr', 'CIRP Cost'),
                       ('project_completion_cost_cr', 'Project Completion Cost'),
                       ('earnest_money_cr', 'Earnest Money')]:
        val = fin.get(key, 0)
        if val is not None:
            report.append(f"| {label} | {val} |")
    report.append("")

    # Compliance notes
    if notes:
        report.append("## Compliance Notes")
        report.append("")
        for note in notes:
            report.append(f"- {note}")
        report.append("")

    # Pipeline artifacts
    report.append("## Pipeline Artifacts")
    report.append("")
    report.append(f"| File | Description |")
    report.append(f"|---|---|")
    report.append(f"| `{case_id}_raw.md` | Raw LlamaParse extraction |")
    report.append(f"| `{case_id}_clean.md` | Cleaned markdown (OCR noise removed) |")
    report.append(f"| `{case_id}_facts.json` | Structured facts from GPT-4o |")
    report.append(f"| `{case_id}_results.json` | Prolog compliance query results |")
    report.append(f"| `prolog/{case_id}_facts.pl` | Auto-generated Prolog fact base |")
    report.append("")
    report.append("*Generated by LexAI Prolog Compliance Engine*")

    report_path = vault_dir / f"{case_id}_report.md"
    with open(report_path, 'w') as f:
        f.write('\n'.join(report))

    print(f"  Report → {report_path.name}")
    return report_path


def _parse_compliance_output(output: str) -> list:
    """Parse Prolog check_compliance output into structured rows."""
    rows = []
    for line in output.split('\n'):
        line = line.strip()
        if line.startswith('PASS:') or line.startswith('FAIL:'):
            status = 'PASS' if line.startswith('PASS:') else 'FAIL'
            # Format: "  PASS: Reg 38(1): CIRP cost priority" or "  FAIL: Sec 30(2)(b): Dissenting FC payment [value: no]"
            content = line.split(':', 1)[1].strip()
            # Check for [value: ...]
            value = ''
            detail = content
            match = re.search(r'\[value:\s*(.+?)\]', content)
            if match:
                value = match.group(1)
                detail = content[:match.start()].strip()
            rule = detail
            # Extract field name from rule text for deficiency lookup
            field = ''
            for key in DEFICIENCY_TEMPLATES:
                if key in value.lower() or key.replace('_', ' ') in detail.lower() or key in detail.lower().replace(' ', '_'):
                    field = key
                    break
            rows.append({'rule': rule, 'status': status, 'value': value, 'detail': detail, 'field': field})
    return rows


def _today() -> str:
    from datetime import date
    return date.today().isoformat()