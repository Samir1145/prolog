% --- Legal Rules based on Section 30(2) and Regulation 38 ---

is_compliant(PlanID) :-
    provides_cirp_priority(PlanID),
    provides_oc_fair_payment(PlanID),
    provides_dissenting_fc_payment(PlanID),
    provides_management_plan(PlanID),
    provides_supervision_mechanism(PlanID),
    no_legal_contravention(PlanID),
    has_affidavit_sec29A(PlanID).

% --- Detailed Validation Rules ---

% Regulation 38(1): CIRP costs must be paid in priority
provides_cirp_priority(PlanID) :-
    plan_detail(PlanID, cirp_cost_payment, priority).

% Section 30(2)(b): OC payment >= higher of Liquidation Value or Waterfall Value
provides_oc_fair_payment(PlanID) :-
    plan_detail(PlanID, oc_payment, Amount),
    plan_detail(PlanID, liquidation_value_oc, LiqVal),
    plan_detail(PlanID, waterfall_value_oc, WatVal),
    max_list([LiqVal, WatVal], MinRequired),
    Amount >= MinRequired.

% Section 30(2)(c): Management plan post-approval
provides_management_plan(PlanID) :-
    plan_detail(PlanID, management_post_approval, yes).

% Section 30(2)(d): Supervision/implementation mechanism
provides_supervision_mechanism(PlanID) :-
    plan_detail(PlanID, supervision_mechanism, yes).

% Section 30(2)(e): No contravention of any law
no_legal_contravention(PlanID) :-
    plan_detail(PlanID, contravenes_any_law, no).

% Section 30(1): Affidavit under Section 29A
has_affidavit_sec29A(PlanID) :-
    plan_detail(PlanID, affidavit_29A_submitted, yes).

% Dissenting FC payment (Section 30(2)(b) second proviso)
provides_dissenting_fc_payment(PlanID) :-
    plan_detail(PlanID, dissenting_fc_payment, yes).

% --- Utility ---
max_list([A, B], A) :- A >= B.
max_list([A, B], B) :- B > A.

% --- Diagnostic: check each rule individually ---
check_compliance(PlanID) :-
    writeln(''),
    writeln('===== SECTION 30(2) & REG 38 COMPLIANCE REPORT ====='),
    check_rule(PlanID, cirp_cost_payment, provides_cirp_priority, 'Reg 38(1): CIRP cost priority'),
    check_rule(PlanID, oc_payment, provides_oc_fair_payment, 'Sec 30(2)(b): OC fair payment'),
    check_rule(PlanID, dissenting_fc_payment, provides_dissenting_fc_payment, 'Sec 30(2)(b): Dissenting FC payment'),
    check_rule(PlanID, management_post_approval, provides_management_plan, 'Sec 30(2)(c): Management plan'),
    check_rule(PlanID, supervision_mechanism, provides_supervision_mechanism, 'Sec 30(2)(d): Supervision mechanism'),
    check_rule_value(PlanID, contravenes_any_law, no_legal_contravention, 'Sec 30(2)(e): No legal contravention'),
    check_rule_value(PlanID, affidavit_29A_submitted, has_affidavit_sec29A, 'Sec 30(1): Affidavit Sec 29A'),
    writeln(''),
    (is_compliant(PlanID) -> writeln('OVERALL: COMPLIANT') ; writeln('OVERALL: NOT COMPLIANT')),
    writeln('===================================================='),
    halt.

check_rule(PlanID, Field, Rule, Label) :-
    (call(Rule, PlanID) ->
        format('  PASS: ~w~n', [Label]) ;
        (plan_detail(PlanID, Field, Val) ->
            format('  FAIL: ~w [value: ~w]~n', [Label, Val]) ;
            format('  FAIL: ~w [MISSING DATA]~n', [Label])
        )
    ).

check_rule_value(PlanID, Field, Rule, Label) :-
    (call(Rule, PlanID) ->
        format('  PASS: ~w~n', [Label]) ;
        (plan_detail(PlanID, Field, Val) ->
            format('  FAIL: ~w [value: ~w]~n', [Label, Val]) ;
            format('  FAIL: ~w [MISSING DATA]~n', [Label])
        )
    ).