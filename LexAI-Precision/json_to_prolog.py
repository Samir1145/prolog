import json, os, subprocess

vault_dir = os.path.join(os.path.dirname(__file__), 'LexAI_Vault')
prolog_dir = os.path.join(os.path.dirname(__file__), 'prolog')

with open(os.path.join(vault_dir, 'SRPL_structured_facts.json'), 'r') as f:
    data = json.load(f)

s30 = data['section30_facts']
s29 = data['section29A_facts']
fin = data['financial_data']
notes = data['compliance_notes']

plan_id = s30['plan_id']

# Map JSON values to Prolog atoms
def pval(val):
    if val == "not_mentioned":
        return "not_mentioned"
    if isinstance(val, str):
        return val
    return val

lines = []
lines.append("% --- Auto-generated facts from SRPL Resolution Plan ---")
lines.append("% Source: SRPL_Resolution_Plan_Final.pdf via LlamaParse + GPT-4o")
lines.append("% Corporate Debtor: Soni Realtors Private Limited")
lines.append("% CIRP Commencement: February 27, 2018")
lines.append("")
for pred in ['undischarged_insolvent', 'wilful_defaulter', 'npa_status',
             'convicted_offence', 'disqualified_director', 'prohibited_by_sebi',
             'involved_in_fraudulent_transactions', 'guarantee_invoked', 'guarantee_unpaid']:
    lines.append(f":- discontiguous {pred}/2.")
lines.append(":- discontiguous guarantee_executed/3.")
lines.append("")

# Section 30 facts
lines.append("% ===== SECTION 30(2) & REGULATION 38 =====")
lines.append("")
lines.append(f"plan_detail({plan_id}, cirp_cost_payment, {pval(s30['cirp_cost_payment'])}).")
lines.append(f"plan_detail({plan_id}, oc_payment, {int(s30['oc_payment'] * 10000000)}).")
lines.append(f"plan_detail({plan_id}, liquidation_value_oc, {int(s30['liquidation_value_oc'] * 10000000)}).")
lines.append(f"plan_detail({plan_id}, waterfall_value_oc, {int(s30['waterfall_value_oc'] * 10000000)}).")
lines.append(f"plan_detail({plan_id}, dissenting_fc_payment, {pval(s30['dissenting_fc_payment'])}).")
lines.append(f"plan_detail({plan_id}, management_post_approval, {pval(s30['management_post_approval'])}).")
lines.append(f"plan_detail({plan_id}, supervision_mechanism, {pval(s30['supervision_mechanism'])}).")
lines.append(f"plan_detail({plan_id}, contravenes_any_law, {pval(s30['contravenes_any_law'])}).")
lines.append(f"plan_detail({plan_id}, affidavit_29A_submitted, {pval(s30['affidavit_29A_submitted'])}).")
lines.append(f"plan_detail({plan_id}, stakeholder_interest_statement, {pval(s30['stakeholder_interest_statement'])}).")
lines.append(f"plan_detail({plan_id}, implementation_timeline, {s30['implementation_timeline_months']}).")
lines.append(f"plan_detail({plan_id}, earnest_money_submitted, {pval(s30['earnest_money_submitted'])}).")
lines.append(f"plan_detail({plan_id}, conditions_precedent_listed, {pval(s30['conditions_precedent_listed'])}).")
lines.append("")

# Section 29A facts
lines.append("% ===== SECTION 29A ELIGIBILITY =====")
for ra in s29['resolution_applicants']:
    name = ra['name'].lower().replace(' ', '_').replace('.', '').replace(',', '')
    lines.append(f"% Resolution Applicant: {ra['name']}")
    lines.append(f"undischarged_insolvent({name}, {ra['undischarged_insolvent']}).")
    lines.append(f"wilful_defaulter({name}, {ra['wilful_defaulter']}).")
    lines.append(f"npa_status({name}, {ra['npa_status']}).")
    lines.append(f"convicted_offence({name}, {ra['convicted_offence']}).")
    lines.append(f"disqualified_director({name}, {ra['disqualified_director']}).")
    lines.append(f"prohibited_by_sebi({name}, {ra['prohibited_by_sebi']}).")
    lines.append(f"involved_in_fraudulent_transactions({name}, {ra['involved_in_fraudulent_transactions']}).")
    lines.append(f"guarantee_executed({name}, corporate_debtor, {ra['guarantee_executed_for_cd']}).")
    lines.append(f"guarantee_invoked({name}, {ra['guarantee_invoked']}).")
    lines.append(f"guarantee_unpaid({name}, {ra['guarantee_unpaid']}).")
    lines.append("")

for cp in s29['connected_persons']:
    ra_name = cp['connected_to'].lower().replace(' ', '_').replace('.', '').replace(',', '')
    cp_name = cp['name'].lower().replace(' ', '_').replace('.', '').replace(',', '')
    lines.append(f"connected_person({ra_name}, {cp_name}).")
    lines.append(f"undischarged_insolvent({cp_name}, {cp['undischarged_insolvent']}).")
    lines.append(f"wilful_defaulter({cp_name}, {cp['wilful_defaulter']}).")
    lines.append(f"npa_status({cp_name}, {cp['npa_status']}).")
    lines.append(f"convicted_offence({cp_name}, {cp['convicted_offence']}).")
    lines.append(f"disqualified_director({cp_name}, {cp['disqualified_director']}).")
    lines.append(f"prohibited_by_sebi({cp_name}, {cp['prohibited_by_sebi']}).")
    lines.append(f"involved_in_fraudulent_transactions({cp_name}, {cp['involved_in_fraudulent_transactions']}).")
    lines.append("")

# Consortium partners (from document, supplementing GPT extraction)
lines.append("% Consortium partners (from document)")
lines.append("connected_person(srijan_infra_llp, nimai_group).")
lines.append("connected_person(srijan_infra_llp, somex_india).")
lines.append("")
lines.append("undischarged_insolvent(nimai_group, no).")
lines.append("wilful_defaulter(nimai_group, no).")
lines.append("npa_status(nimai_group, none).")
lines.append("convicted_offence(nimai_group, no).")
lines.append("disqualified_director(nimai_group, no).")
lines.append("prohibited_by_sebi(nimai_group, no).")
lines.append("involved_in_fraudulent_transactions(nimai_group, no).")
lines.append("guarantee_executed(nimai_group, corporate_debtor, no).")
lines.append("guarantee_invoked(nimai_group, no).")
lines.append("guarantee_unpaid(nimai_group, no).")
lines.append("")
lines.append("undischarged_insolvent(somex_india, no).")
lines.append("wilful_defaulter(somex_india, no).")
lines.append("npa_status(somex_india, none).")
lines.append("convicted_offence(somex_india, no).")
lines.append("disqualified_director(somex_india, no).")
lines.append("prohibited_by_sebi(somex_india, no).")
lines.append("involved_in_fraudulent_transactions(somex_india, no).")
lines.append("guarantee_executed(somex_india, corporate_debtor, no).")
lines.append("guarantee_invoked(somex_india, no).")
lines.append("guarantee_unpaid(somex_india, no).")
lines.append("")

# Financial data
lines.append("% ===== FINANCIAL DATA =====")
lines.append(f"plan_detail({plan_id}, total_claims_cr, {fin['total_claims_admitted_cr']}).")
lines.append(f"plan_detail({plan_id}, home_buyer_claims_cr, {fin['home_buyer_claims_cr']}).")
lines.append(f"plan_detail({plan_id}, fc_claims_cr, {fin['financial_creditor_claims_cr']}).")
lines.append(f"plan_detail({plan_id}, oc_claims_cr, {fin['operational_creditor_claims_cr']}).")
lines.append(f"plan_detail({plan_id}, cirp_cost_cr, {fin['cirp_cost_cr']}).")
lines.append(f"plan_detail({plan_id}, project_completion_cost_cr, {fin['project_completion_cost_cr']}).")
lines.append(f"plan_detail({plan_id}, earnest_money_cr, {fin['earnest_money_cr']}).")
lines.append(f"plan_detail({plan_id}, dtcp_dues_principal_cr, {fin['dtcp_dues_principal_cr']}).")
lines.append(f"plan_detail({plan_id}, payment_to_other_fcs_pct, {fin['payment_to_other_fcs_percentage']}).")
lines.append("")
lines.append("% ===== COMPLIANCE NOTES =====")
for i, note in enumerate(notes, 1):
    lines.append(f"% Note {i}: {note}")

facts_path = os.path.join(prolog_dir, 'srpl_plan_facts.pl')
with open(facts_path, 'w') as f:
    f.write('\n'.join(lines))

print(f"Prolog facts written to: {facts_path}")

# Run Section 30 compliance
result_s30 = subprocess.run(
    ['swipl', '-s', os.path.join(prolog_dir, 'section30_compliance.pl'),
     '-s', facts_path, '-g', 'check_compliance(srpl_plan)'],
    capture_output=True, text=True
)
print("\n=== SECTION 30(2) COMPLIANCE ===")
print(result_s30.stdout)
if result_s30.stderr:
    for line in result_s30.stderr.split('\n'):
        if 'ERROR' in line:
            print(line)

# Run Section 29A eligibility
s29_goal = "ignore((is_eligible_29A(srijan_infra_llp) -> writeln('ELIGIBLE') ; writeln('NOT ELIGIBLE'))), halt."
result_s29 = subprocess.run(
    ['swipl', '-s', os.path.join(prolog_dir, 'section29A_eligibility.pl'),
     '-s', facts_path, '-g', s29_goal],
    capture_output=True, text=True
)
print("\n=== SECTION 29A ELIGIBILITY ===")
print(result_s29.stdout)

# Save results
results = {
    "section30_output": result_s30.stdout,
    "section29A_output": result_s29.stdout,
}
with open(os.path.join(vault_dir, 'SRPL_prolog_results.json'), 'w') as f:
    json.dump(results, f, indent=4)

print("\nResults saved to LexAI_Vault/SRPL_prolog_results.json")