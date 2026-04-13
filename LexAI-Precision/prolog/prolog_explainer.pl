% --- Prolog Proof Trace & Confidence Scoring Engine ---
% Generates detailed proof traces for each compliance rule and
% assigns confidence scores based on data quality.

% === Confidence Scoring ===
% Confidence reflects how reliable the compliance determination is,
% based on whether data was explicitly stated, inferred, or missing.
%
%   HIGH      (0.9)  — explicitly stated in the document
%   MEDIUM    (0.6)  — inferred from context or partial information
%   LOW       (0.3)  — not mentioned, defaulted, or ambiguous
%   UNCERTAIN (0.1)  — conflicting signals or extraction uncertainty

% Confidence for each data point
data_confidence(PlanID, cirp_cost_payment, 0.9) :-
    plan_detail(PlanID, cirp_cost_payment, priority).
data_confidence(PlanID, cirp_cost_payment, 0.6) :-
    plan_detail(PlanID, cirp_cost_payment, non_priority).
data_confidence(PlanID, cirp_cost_payment, 0.3) :-
    plan_detail(PlanID, cirp_cost_payment, not_mentioned).

data_confidence(PlanID, oc_payment, 0.9) :-
    plan_detail(PlanID, oc_payment, Amt), Amt > 0.
data_confidence(PlanID, oc_payment, 0.5) :-
    plan_detail(PlanID, oc_payment, 0).  % Zero could mean NIL or not stated

data_confidence(PlanID, dissenting_fc_payment, 0.9) :-
    plan_detail(PlanID, dissenting_fc_payment, yes).
data_confidence(PlanID, dissenting_fc_payment, 0.7) :-
    plan_detail(PlanID, dissenting_fc_payment, no).
data_confidence(PlanID, dissenting_fc_payment, 0.3) :-
    plan_detail(PlanID, dissenting_fc_payment, not_mentioned).

data_confidence(PlanID, management_post_approval, 0.9) :-
    plan_detail(PlanID, management_post_approval, yes).
data_confidence(PlanID, management_post_approval, 0.7) :-
    plan_detail(PlanID, management_post_approval, no).
data_confidence(PlanID, management_post_approval, 0.3) :-
    plan_detail(PlanID, management_post_approval, not_mentioned).

data_confidence(PlanID, supervision_mechanism, 0.9) :-
    plan_detail(PlanID, supervision_mechanism, yes).
data_confidence(PlanID, supervision_mechanism, 0.7) :-
    plan_detail(PlanID, supervision_mechanism, no).
data_confidence(PlanID, supervision_mechanism, 0.3) :-
    plan_detail(PlanID, supervision_mechanism, not_mentioned).

data_confidence(PlanID, contravenes_any_law, 0.9) :-
    plan_detail(PlanID, contravenes_any_law, no).
data_confidence(PlanID, contravenes_any_law, 0.7) :-
    plan_detail(PlanID, contravenes_any_law, conditional).
data_confidence(PlanID, contravenes_any_law, 0.4) :-
    plan_detail(PlanID, contravenes_any_law, yes).

data_confidence(PlanID, affidavit_29A_submitted, 0.9) :-
    plan_detail(PlanID, affidavit_29A_submitted, yes).
data_confidence(PlanID, affidavit_29A_submitted, 0.7) :-
    plan_detail(PlanID, affidavit_29A_submitted, no).
data_confidence(PlanID, affidavit_29A_submitted, 0.3) :-
    plan_detail(PlanID, affidavit_29A_submitted, not_mentioned).

data_confidence(PlanID, stakeholder_interest_statement, 0.9) :-
    plan_detail(PlanID, stakeholder_interest_statement, yes).
data_confidence(PlanID, stakeholder_interest_statement, 0.3) :-
    plan_detail(PlanID, stakeholder_interest_statement, not_mentioned).

% Section 29A confidence scores
data_confidence_29A(RA, undischarged_insolvent, 0.9) :- undischarged_insolvent(RA, no).
data_confidence_29A(RA, undischarged_insolvent, 0.9) :- undischarged_insolvent(RA, yes).
data_confidence_29A(RA, wilful_defaulter, 0.9) :- wilful_defaulter(RA, no).
data_confidence_29A(RA, wilful_defaulter, 0.9) :- wilful_defaulter(RA, yes).
data_confidence_29A(RA, npa_status, 0.9) :- npa_status(RA, none).
data_confidence_29A(RA, npa_status, 0.9) :- npa_status(RA, over_one_year).
data_confidence_29A(RA, npa_status, 0.7) :- npa_status(RA, under_one_year).
data_confidence_29A(RA, convicted_offence, 0.9) :- convicted_offence(RA, no).
data_confidence_29A(RA, convicted_offence, 0.9) :- convicted_offence(RA, yes).
data_confidence_29A(RA, disqualified_director, 0.9) :- disqualified_director(RA, no).
data_confidence_29A(RA, disqualified_director, 0.9) :- disqualified_director(RA, yes).
data_confidence_29A(RA, prohibited_by_sebi, 0.9) :- prohibited_by_sebi(RA, no).
data_confidence_29A(RA, prohibited_by_sebi, 0.9) :- prohibited_by_sebi(RA, yes).
data_confidence_29A(RA, involved_in_fraud, 0.9) :- involved_in_fraudulent_transactions(RA, no).
data_confidence_29A(RA, involved_in_fraud, 0.9) :- involved_in_fraudulent_transactions(RA, yes).
data_confidence_29A(RA, guarantee, 0.9) :- guarantee_executed(RA, corporate_debtor, no).
data_confidence_29A(RA, guarantee, 0.9) :- guarantee_executed(RA, corporate_debtor, yes).

% === Overall Confidence Score ===
% Minimum confidence across all checked rules (weakest link principle)
% Returns a list of (Rule, Confidence) pairs and the minimum

rule_confidences(PlanID, Confidences) :-
    findall((Rule, Conf),
        (   rule_field(Rule, Field),
            data_confidence(PlanID, Field, Conf)
        ),
        Confidences).

min_confidence(PlanID, MinConf) :-
    rule_confidences(PlanID, Confidences),
    findall(C, member((_, C), Confidences), Values),
    min_list(Values, MinConf).

% Field-to-rule mapping
rule_field('Reg 38(1): CIRP cost priority', cirp_cost_payment).
rule_field('Sec 30(2)(b): OC fair payment', oc_payment).
rule_field('Sec 30(2)(b): Dissenting FC payment', dissenting_fc_payment).
rule_field('Sec 30(2)(c): Management plan', management_post_approval).
rule_field('Sec 30(2)(d): Supervision mechanism', supervision_mechanism).
rule_field('Sec 30(2)(e): No legal contravention', contravenes_any_law).
rule_field('Sec 30(1): Affidavit Sec 29A', affidavit_29A_submitted).
rule_field('Reg 38(1A): Stakeholder interest', stakeholder_interest_statement).

% === Proof Trace Generation ===
% For each rule, explain WHY it passes or fails by tracing the logic

proof_trace_cirp_cost(PlanID) :-
    plan_detail(PlanID, cirp_cost_payment, Val),
    (Val = priority ->
        format('  [PROOF] Reg 38(1): CIRP cost payment is "~w" -> CIRP costs given priority -> PASS~n', [Val]) ;
     Val = non_priority ->
        format('  [PROOF] Reg 38(1): CIRP cost payment is "~w" -> CIRP costs NOT given priority -> FAIL~n', [Val]) ;
        format('  [PROOF] Reg 38(1): CIRP cost payment is "~w" -> Not addressed -> FAIL~n', [Val])
    ).

proof_trace_oc_payment(PlanID) :-
    plan_detail(PlanID, oc_payment, Amt),
    plan_detail(PlanID, liquidation_value_oc, LiqVal),
    plan_detail(PlanID, waterfall_value_oc, WatVal),
    max_list([LiqVal, WatVal], MinRequired),
    (Amt >= MinRequired ->
        format('  [PROOF] Sec 30(2)(b): OC payment ~w >= max(liquidation=~w, waterfall=~w) = ~w -> PASS~n', [Amt, LiqVal, WatVal, MinRequired]) ;
        format('  [PROOF] Sec 30(2)(b): OC payment ~w < max(liquidation=~w, waterfall=~w) = ~w -> FAIL~n', [Amt, LiqVal, WatVal, MinRequired])
    ).

proof_trace_dissenting_fc(PlanID) :-
    plan_detail(PlanID, dissenting_fc_payment, Val),
    (Val = yes ->
        format('  [PROOF] Sec 30(2)(b) proviso: Dissenting FC payment = "~w" -> Payment provided -> PASS~n', [Val]) ;
     Val = no ->
        format('  [PROOF] Sec 30(2)(b) proviso: Dissenting FC payment = "~w" -> Payment not provided -> FAIL~n', [Val]) ;
        format('  [PROOF] Sec 30(2)(b) proviso: Dissenting FC payment = "~w" -> Not addressed -> FAIL~n', [Val])
    ).

proof_trace_management(PlanID) :-
    plan_detail(PlanID, management_post_approval, Val),
    (Val = yes ->
        format('  [PROOF] Sec 30(2)(c): Management post-approval = "~w" -> Management plan described -> PASS~n', [Val]) ;
        format('  [PROOF] Sec 30(2)(c): Management post-approval = "~w" -> No management plan -> FAIL~n', [Val])
    ).

proof_trace_supervision(PlanID) :-
    plan_detail(PlanID, supervision_mechanism, Val),
    (Val = yes ->
        format('  [PROOF] Sec 30(2)(d): Supervision mechanism = "~w" -> Monitoring/supervision described -> PASS~n', [Val]) ;
     Val = not_mentioned ->
        format('  [PROOF] Sec 30(2)(d): Supervision mechanism = "~w" -> Not addressed in plan -> FAIL~n', [Val]) ;
        format('  [PROOF] Sec 30(2)(d): Supervision mechanism = "~w" -> Not described -> FAIL~n', [Val])
    ).

proof_trace_contravention(PlanID) :-
    plan_detail(PlanID, contravenes_any_law, Val),
    (Val = no ->
        format('  [PROOF] Sec 30(2)(e): Legal contravention = "~w" -> No contravention -> PASS~n', [Val]) ;
     Val = conditional ->
        format('  [PROOF] Sec 30(2)(e): Legal contravention = "~w" -> Contravention conditional on NCLT order -> CONDITIONAL~n', [Val]) ;
        format('  [PROOF] Sec 30(2)(e): Legal contravention = "~w" -> Plan contravenes law -> FAIL~n', [Val])
    ).

proof_trace_affidavit(PlanID) :-
    plan_detail(PlanID, affidavit_29A_submitted, Val),
    (Val = yes ->
        format('  [PROOF] Sec 30(1): Affidavit 29A = "~w" -> Affidavit submitted -> PASS~n', [Val]) ;
     Val = not_mentioned ->
        format('  [PROOF] Sec 30(1): Affidavit 29A = "~w" -> Not found in document -> FAIL (verify physical copy)~n', [Val]) ;
        format('  [PROOF] Sec 30(1): Affidavit 29A = "~w" -> Not submitted -> FAIL~n', [Val])
    ).

proof_trace_stakeholder(PlanID) :-
    plan_detail(PlanID, stakeholder_interest_statement, Val),
    (Val = yes ->
        format('  [PROOF] Reg 38(1A): Stakeholder interest = "~w" -> Statement provided -> PASS~n', [Val]) ;
        format('  [PROOF] Reg 38(1A): Stakeholder interest = "~w" -> Not provided -> FAIL~n', [Val])
    ).

% === Section 29A Proof Traces ===

proof_trace_29A(RA) :-
    format('  [PROOF] Section 29A eligibility for ~w:~n', [RA]),
    trace_29A_clause(RA, '(a) Undischarged insolvent', undischarged_insolvent(RA, yes)),
    trace_29A_clause(RA, '(b) Wilful defaulter', wilful_defaulter(RA, yes)),
    trace_29A_clause_npa(RA),
    trace_29A_clause(RA, '(d) Convicted offence', convicted_offence(RA, yes)),
    trace_29A_clause(RA, '(e) Disqualified director', disqualified_director(RA, yes)),
    trace_29A_clause(RA, '(f) Prohibited by SEBI', prohibited_by_sebi(RA, yes)),
    trace_29A_clause(RA, '(g) Fraudulent transactions', involved_in_fraudulent_transactions(RA, yes)),
    trace_29A_guarantee(RA),
    trace_29A_connected(RA).

trace_29A_clause(RA, Label, Condition) :-
    (Condition ->
        format('    [FAIL] ~w -> DISQUALIFIED~n', [Label]) ;
        format('    [PASS] ~w -> Not disqualified under this clause~n', [Label])
    ).

trace_29A_clause_npa(RA) :-
    (npa_status(RA, over_one_year) ->
        (npa_overdue_paid(RA, yes) ->
            format('    [PASS] (c) NPA >1yr but overdue paid -> Not disqualified~n') ;
            format('    [FAIL] (c) NPA >1yr and overdue unpaid -> DISQUALIFIED~n')
        ) ;
     npa_status(RA, under_one_year) ->
        format('    [WARN] (c) NPA <1yr -> Eligible but monitor~n') ;
        format('    [PASS] (c) No NPA -> Not disqualified under this clause~n')
    ).

trace_29A_guarantee(RA) :-
    (guarantee_executed(RA, corporate_debtor, yes) ->
        (guarantee_invoked(RA, yes) ->
            (guarantee_unpaid(RA, yes) ->
                format('    [FAIL] (h) Guarantee executed, invoked, and unpaid -> DISQUALIFIED~n') ;
                format('    [PASS] (h) Guarantee invoked but paid -> Not disqualified~n')
            ) ;
            format('    [PASS] (h) Guarantee executed but not invoked -> Not disqualified~n')
        ) ;
        format('    [PASS] (h) No guarantee for CD -> Not disqualified under this clause~n')
    ).

trace_29A_connected(RA) :-
    findall(CP, connected_person(RA, CP), CPs),
    (CPs = [] ->
        format('    [PASS] (j) No connected persons identified -> Not applicable~n') ;
        format('    [INFO] (j) Connected persons: ~w~n', [CPs]),
        forall(member(CP, CPs),
            (is_disqualified(CP) ->
                format('      [FAIL] ~w is disqualified -> RA DISQUALIFIED via connected person~n', [CP]) ;
                format('      [PASS] ~w is not disqualified~n', [CP])
            )
        )
    ).

% === Main Diagnostic ===

explain_compliance(PlanID) :-
    writeln(''),
    writeln('===== PROOF TRACE & CONFIDENCE REPORT ====='),
    writeln(''),

    % Section 30(2) proof traces
    writeln('--- Section 30(2) Proof Traces ---'),
    proof_trace_cirp_cost(PlanID),
    proof_trace_oc_payment(PlanID),
    proof_trace_dissenting_fc(PlanID),
    proof_trace_management(PlanID),
    proof_trace_supervision(PlanID),
    proof_trace_contravention(PlanID),
    proof_trace_affidavit(PlanID),
    proof_trace_stakeholder(PlanID),

    % Confidence scores
    writeln(''),
    writeln('--- Confidence Scores ---'),
    forall(rule_field(Rule, Field),
        (data_confidence(PlanID, Field, Conf) ->
            format('  ~w: confidence = ~1f~n', [Rule, Conf]) ;
            format('  ~w: confidence = N/A~n', [Rule])
        )
    ),

    % Overall confidence
    (min_confidence(PlanID, MinConf) ->
        format('~n  OVERALL CONFIDENCE: ~1f (weakest-link minimum)~n', [MinConf]) ;
        writeln('  OVERALL CONFIDENCE: Unable to compute')
    ),

    % Conditional compliance status
    writeln(''),
    writeln('--- Overall Status ---'),
    (plan_status(PlanID, compliant) ->
        writeln('  STATUS: COMPLIANT (all rules pass unconditionally)')
    ; plan_status(PlanID, not_compliant) ->
        writeln('  STATUS: NOT COMPLIANT (core mandatory rules fail)')
    ; plan_status(PlanID, conditional) ->
        writeln('  STATUS: CONDITIONALLY COMPLIANT (passes if conditions precedent are met)')
    ; writeln('  STATUS: Unable to determine')
    ),

    writeln(''),
    writeln('===================================================='),
    halt.

% Explain Section 29A for a specific RA
explain_29A(RA) :-
    writeln(''),
    writeln('===== SECTION 29A PROOF TRACE ====='),
    writeln(''),
    proof_trace_29A(RA),
    (is_eligible_29A(RA) ->
        format('~n  OVERALL: ~w is ELIGIBLE under Section 29A~n', [RA]) ;
        format('~n  OVERALL: ~w is NOT ELIGIBLE under Section 29A~n', [RA])
    ),
    % 29A confidence
    writeln(''),
    writeln('--- 29A Confidence ---'),
    forall(data_confidence_29A(RA, Clause, Conf),
        format('  Clause ~w: confidence = ~1f~n', [Clause, Conf])
    ),
    writeln(''),
    writeln('===================================================='),
    halt.