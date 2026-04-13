"""Step 6: Load structured facts into Memgraph as a knowledge graph."""
import json
import re
from pathlib import Path


def load_into_memgraph(facts_json_path: Path, case_id: str,
                       uri: str = "bolt://localhost:7687",
                       user: str = "", password: str = "",
                       vault_dir: Path = None) -> bool:
    """Load extracted facts into Memgraph as a knowledge graph.

    Creates nodes for: CorporateDebtor, ResolutionPlan, ResolutionApplicant,
    ConnectedPerson, ConditionPrecedent, ComplianceRule, ConfidenceScore, ProofTrace.
    Creates relationships between them.

    Returns True if successful.
    """
    from neo4j import GraphDatabase

    if vault_dir is None:
        vault_dir = facts_json_path.parent

    with open(facts_json_path, 'r') as f:
        data = json.load(f)

    s30 = data['section30_facts']
    s29 = data['section29A_facts']
    fin = data['financial_data']
    notes = data.get('compliance_notes', [])
    plan_id = s30['plan_id']

    driver = GraphDatabase.driver(uri, auth=(user, password))

    with driver.session() as session:
        # Clear previous data for this case
        session.run("MATCH (n) WHERE n.case_id = $case_id DETACH DELETE n",
                     case_id=case_id)

        # 1. Corporate Debtor
        session.run("""
            CREATE (cd:CorporateDebtor {
                name: 'Soni Realtors Private Limited',
                case_id: $case_id,
                cirp_commencement: '2018-02-27'
            })
        """, case_id=case_id)

        # 2. Resolution Plan
        session.run("""
            MATCH (cd:CorporateDebtor {case_id: $case_id})
            CREATE (rp:ResolutionPlan {
                plan_id: $plan_id,
                case_id: $case_id,
                cirp_cost_priority: $cirp_cost_priority,
                oc_payment_cr: $oc_payment,
                liquidation_value_oc_cr: $liq_val,
                waterfall_value_oc_cr: $wat_val,
                dissenting_fc_payment: $dissenting,
                management_post_approval: $mgmt,
                supervision_mechanism: $supervision,
                contravenes_any_law: $contravention,
                affidavit_29A_submitted: $affidavit,
                stakeholder_interest: $stakeholder,
                implementation_months: $impl_months,
                earnest_money_submitted: $earnest,
                conditions_precedent_listed: $cp_listed
            })
            CREATE (cd)-[:HAS_PLAN]->(rp)
        """, case_id=case_id, plan_id=plan_id,
             cirp_cost_priority=s30.get('cirp_cost_payment', 'unknown'),
             oc_payment=s30.get('oc_payment', 0),
             liq_val=s30.get('liquidation_value_oc', 0),
             wat_val=s30.get('waterfall_value_oc', 0),
             dissenting=s30.get('dissenting_fc_payment', 'unknown'),
             mgmt=s30.get('management_post_approval', 'unknown'),
             supervision=s30.get('supervision_mechanism', 'unknown'),
             contravention=s30.get('contravenes_any_law', 'unknown'),
             affidavit=s30.get('affidavit_29A_submitted', 'unknown'),
             stakeholder=s30.get('stakeholder_interest_statement', 'unknown'),
             impl_months=s30.get('implementation_timeline_months'),
             earnest=s30.get('earnest_money_submitted', 'unknown'),
             cp_listed=s30.get('conditions_precedent_listed', 'unknown'))

        # 3. Financial summary linked to plan
        session.run("""
            MATCH (rp:ResolutionPlan {case_id: $case_id})
            SET rp.total_claims_cr = $total,
                rp.home_buyer_claims_cr = $hb,
                rp.fc_claims_cr = $fc,
                rp.oc_claims_cr = $oc,
                rp.cirp_cost_cr = $cirp,
                rp.project_completion_cost_cr = $proj,
                rp.earnest_money_cr = $em,
                rp.dtcp_dues_cr = $dtcp,
                rp.fc_payment_pct = $fc_pct
        """, case_id=case_id,
             total=fin.get('total_claims_admitted_cr', 0),
             hb=fin.get('home_buyer_claims_cr', 0),
             fc=fin.get('financial_creditor_claims_cr', 0),
             oc=fin.get('operational_creditor_claims_cr', 0),
             cirp=fin.get('cirp_cost_cr', 0),
             proj=fin.get('project_completion_cost_cr', 0),
             em=fin.get('earnest_money_cr', 0),
             dtcp=fin.get('dtcp_dues_principal_cr', 0),
             fc_pct=fin.get('payment_to_other_fcs_percentage', 0))

        # 4. Resolution Applicants
        for i, ra in enumerate(s29.get('resolution_applicants', [])):
            ra_name = ra['name']
            ra_atom = ra_name.lower().replace(' ', '_').replace('.', '').replace(',', '')
            session.run("""
                MATCH (cd:CorporateDebtor {case_id: $case_id})
                CREATE (ra:ResolutionApplicant {
                    name: $name,
                    atom: $atom,
                    case_id: $case_id,
                    undischarged_insolvent: $ui,
                    wilful_defaulter: $wd,
                    npa_status: $npa,
                    convicted_offence: $co,
                    disqualified_director: $dd,
                    prohibited_by_sebi: $ps,
                    involved_in_fraud: $fraud,
                    guarantee_for_cd: $ge,
                    guarantee_invoked: $gi,
                    guarantee_unpaid: $gu
                })
                CREATE (ra)-[:PROPOSES_PLAN_FOR]->(cd)
            """, case_id=case_id, name=ra_name, atom=ra_atom,
                 ui=ra.get('undischarged_insolvent', 'unknown'),
                 wd=ra.get('wilful_defaulter', 'unknown'),
                 npa=ra.get('npa_status', 'unknown'),
                 co=ra.get('convicted_offence', 'unknown'),
                 dd=ra.get('disqualified_director', 'unknown'),
                 ps=ra.get('prohibited_by_sebi', 'unknown'),
                 fraud=ra.get('involved_in_fraudulent_transactions', 'unknown'),
                 ge=ra.get('guarantee_executed_for_cd', 'unknown'),
                 gi=ra.get('guarantee_invoked', 'unknown'),
                 gu=ra.get('guarantee_unpaid', 'unknown'))

        # 5. Connected Persons
        for cp in s29.get('connected_persons', []):
            cp_name = cp['name']
            cp_atom = cp_name.lower().replace(' ', '_').replace('.', '').replace(',', '')
            ra_name = cp.get('connected_to', '')
            ra_atom = ra_name.lower().replace(' ', '_').replace('.', '').replace(',', '')
            session.run("""
                MATCH (ra:ResolutionApplicant {atom: $ra_atom, case_id: $case_id})
                CREATE (cp:ConnectedPerson {
                    name: $name,
                    atom: $atom,
                    case_id: $case_id,
                    connected_to: $ra_name,
                    undischarged_insolvent: $ui,
                    wilful_defaulter: $wd,
                    npa_status: $npa,
                    convicted_offence: $co,
                    disqualified_director: $dd,
                    prohibited_by_sebi: $ps,
                    involved_in_fraud: $fraud
                })
                CREATE (ra)-[:HAS_CONNECTED_PERSON]->(cp)
            """, ra_atom=ra_atom, case_id=case_id,
                 name=cp_name, atom=cp_atom, ra_name=ra_name,
                 ui=cp.get('undischarged_insolvent', 'unknown'),
                 wd=cp.get('wilful_defaulter', 'unknown'),
                 npa=cp.get('npa_status', 'unknown'),
                 co=cp.get('convicted_offence', 'unknown'),
                 dd=cp.get('disqualified_director', 'unknown'),
                 ps=cp.get('prohibited_by_sebi', 'unknown'),
                 fraud=cp.get('involved_in_fraudulent_transactions', 'unknown'))

        # 6. Compliance Rules (each as a node with pass/fail)
        rules = [
            ('CIRP_cost_priority', 'Reg 38(1)', s30.get('cirp_cost_payment', 'unknown')),
            ('OC_fair_payment', 'Sec 30(2)(b)', s30.get('oc_payment', 'unknown')),
            ('dissenting_FC_payment', 'Sec 30(2)(b) proviso', s30.get('dissenting_fc_payment', 'unknown')),
            ('management_plan', 'Sec 30(2)(c)', s30.get('management_post_approval', 'unknown')),
            ('supervision_mechanism', 'Sec 30(2)(d)', s30.get('supervision_mechanism', 'unknown')),
            ('no_legal_contravention', 'Sec 30(2)(e)', s30.get('contravenes_any_law', 'unknown')),
            ('affidavit_29A', 'Sec 30(1)', s30.get('affidavit_29A_submitted', 'unknown')),
            ('stakeholder_interest', 'Reg 38(1A)', s30.get('stakeholder_interest_statement', 'unknown')),
        ]
        for rule_id, section, value in rules:
            status = 'PASS' if value in ('yes', 'priority', 0) else \
                     'CONDITIONAL' if value == 'conditional' else \
                     'NOT_ADDRESSED' if value == 'not_mentioned' else 'FAIL'
            session.run("""
                MATCH (rp:ResolutionPlan {case_id: $case_id})
                CREATE (cr:ComplianceRule {
                    rule_id: $rule_id,
                    section: $section,
                    value: $value,
                    status: $status,
                    case_id: $case_id
                })
                CREATE (rp)-[:MUST_SATISFY]->(cr)
            """, case_id=case_id, rule_id=rule_id, section=section,
                 value=str(value), status=status)

        # 7. Compliance Notes
        for i, note in enumerate(notes):
            session.run("""
                MATCH (rp:ResolutionPlan {case_id: $case_id})
                CREATE (cn:ComplianceNote {
                    note_id: $nid,
                    text: $text,
                    case_id: $case_id
                })
                CREATE (rp)-[:HAS_NOTE]->(cn)
            """, case_id=case_id, nid=i, text=note)

        # 8. Conditions Precedent (from facts)
        conditions = []
        if s30.get('conditions_precedent_listed') == 'yes':
            conditions.append('DTCP license renewal')
            conditions.append('Home buyer consent for upfront payment')
            conditions.append('NCLT approval of waivers and concessions')
            conditions.append('Invalidation of preferential transactions')
        if s30.get('contravenes_any_law') == 'conditional':
            if 'NCLT invalidation' not in str(conditions):
                conditions.append('NCLT invalidation of preferential transactions')

        for i, cond in enumerate(conditions):
            session.run("""
                MATCH (rp:ResolutionPlan {case_id: $case_id})
                CREATE (cp:ConditionPrecedent {
                    condition_id: $cid,
                    description: $desc,
                    case_id: $case_id,
                    fulfilled: 'pending'
                })
                CREATE (rp)-[:REQUIRES_FULFILLMENT_OF]->(cp)
            """, case_id=case_id, cid=i, desc=cond)

        # 9. Proof Traces & Confidence Scores (from results JSON)
        results_path = vault_dir / f"{case_id}_results.json"
        if results_path.exists():
            with open(results_path, 'r') as f:
                results = json.load(f)

            # Parse confidence scores from proof trace output
            proof_trace = results.get('proof_trace_output', '')
            for line in proof_trace.split('\n'):
                line = line.strip()
                # Parse lines like: "Sec 30(2)(b): OC fair payment: confidence = 0.5"
                conf_match = re.match(r'(.+?):\s+confidence\s+=\s+([0-9.]+)', line)
                if conf_match:
                    rule_name = conf_match.group(1).strip()
                    confidence = float(conf_match.group(2))
                    session.run("""
                        MATCH (rp:ResolutionPlan {case_id: $case_id})
                        CREATE (ct:ConfidenceScore {
                            rule: $rule,
                            confidence: $conf,
                            level: $level,
                            case_id: $case_id
                        })
                        CREATE (rp)-[:HAS_CONFIDENCE]->(ct)
                    """, case_id=case_id, rule=rule_name, conf=confidence,
                         level='HIGH' if confidence >= 0.8 else 'MEDIUM' if confidence >= 0.5 else 'LOW')

            # Parse proof traces
            for line in proof_trace.split('\n'):
                line = line.strip()
                if line.startswith('[PROOF]'):
                    proof_text = line.replace('[PROOF] ', '')
                    # Determine rule and outcome
                    outcome = 'PASS' if ' -> PASS' in proof_text else \
                              'FAIL' if ' -> FAIL' in proof_text else \
                              'CONDITIONAL' if ' -> CONDITIONAL' in proof_text else 'UNKNOWN'
                    rule_match = re.match(r'(.+?):\s', proof_text)
                    rule_name = rule_match.group(1) if rule_match else proof_text.split(' -> ')[0]
                    session.run("""
                        MATCH (rp:ResolutionPlan {case_id: $case_id})
                        CREATE (pt:ProofTrace {
                            rule: $rule,
                            outcome: $outcome,
                            explanation: $text,
                            case_id: $case_id
                        })
                        CREATE (rp)-[:HAS_PROOF_TRACE]->(pt)
                    """, case_id=case_id, rule=rule_name, outcome=outcome, text=proof_text)

            # Parse overall confidence
            for line in proof_trace.split('\n'):
                line = line.strip()
                if 'OVERALL CONFIDENCE:' in line:
                    conf_match = re.search(r'([0-9.]+)', line)
                    if conf_match:
                        overall_conf = float(conf_match.group(1))
                        session.run("""
                            MATCH (rp:ResolutionPlan {case_id: $case_id})
                            SET rp.overall_confidence = $conf
                        """, case_id=case_id, conf=overall_conf)
                    break

            # Parse 29A proof traces
            proof_29a = results.get('proof_trace_29a_output', '')
            for line in proof_29a.split('\n'):
                line = line.strip()
                if line.startswith('[PASS]') or line.startswith('[FAIL]') or line.startswith('[WARN]') or line.startswith('[INFO]'):
                    tag = line.split(']')[0].replace('[', '')
                    text = line.split(']', 1)[1].strip() if ']' in line else line
                    session.run("""
                        MATCH (ra:ResolutionApplicant {case_id: $case_id})
                        CREATE (pt:EligibilityTrace {
                            tag: $tag,
                            clause: $clause,
                            text: $text,
                            case_id: $case_id
                        })
                        CREATE (ra)-[:HAS_ELIGIBILITY_TRACE]->(pt)
                    """, case_id=case_id, tag=tag,
                         clause=text.split(' ')[0] if text.startswith('(') else '',
                         text=text)

    driver.close()
    print(f"  Knowledge graph loaded into Memgraph for case: {case_id}")
    return True