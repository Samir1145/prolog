% --- Conditional Compliance Engine ---
% Extends Section 30(2) checks with 3-state model:
%   - compliant      (unconditionally passes)
%   - conditional     (passes only if conditions precedent are met)
%   - not_compliant  (fails regardless of conditions)

% === Three-State Compliance ===

% Unconditional compliance: all rules pass without conditions
unconditionally_compliant(PlanID) :-
    provides_cirp_priority(PlanID),
    provides_oc_fair_payment(PlanID),
    provides_dissenting_fc_payment(PlanID),
    provides_management_plan(PlanID),
    provides_supervision_mechanism(PlanID),
    no_legal_contravention(PlanID),
    has_affidavit_sec29A(PlanID).

% Conditional compliance: core rules pass but some depend on
% conditions precedent being fulfilled
conditionally_compliant(PlanID, Conditions) :-
    provides_cirp_priority(PlanID),
    provides_oc_fair_payment(PlanID),
    provides_management_plan(PlanID),
    findall(Cond, compliance_condition(PlanID, Cond), Conditions),
    Conditions \= [].

% Not compliant: core mandatory rules fail outright
not_compliant(PlanID) :-
    \+ provides_cirp_priority(PlanID).
not_compliant(PlanID) :-
    \+ provides_oc_fair_payment(PlanID).
not_compliant(PlanID) :-
    \+ provides_management_plan(PlanID).

% === Conditions That Can Be Conditional ===
% Some rules are satisfied conditionally (dependent on NCLT orders, etc.)

compliance_condition(PlanID, 'Dissenting FC payment not addressed') :-
    \+ provides_dissenting_fc_payment(PlanID),
    plan_detail(PlanID, dissenting_fc_payment, not_mentioned).

compliance_condition(PlanID, 'No supervision/monitoring mechanism described') :-
    \+ provides_supervision_mechanism(PlanID),
    plan_detail(PlanID, supervision_mechanism, not_mentioned).

compliance_condition(PlanID, 'Plan contingent on NCLT invalidation of preferential transactions') :-
    \+ no_legal_contravention(PlanID),
    plan_detail(PlanID, contravenes_any_law, conditional).

compliance_condition(PlanID, 'Section 29A affidavit not found in document') :-
    \+ has_affidavit_sec29A(PlanID),
    plan_detail(PlanID, affidavit_29A_submitted, not_mentioned).

% === Overall Status Determination ===
% 3-state: compliant | conditional | not_compliant

plan_status(PlanID, compliant) :-
    unconditionally_compliant(PlanID).

plan_status(PlanID, conditional) :-
    \+ unconditionally_compliant(PlanID),
    \+ not_compliant(PlanID),
    conditionally_compliant(PlanID, _).

plan_status(PlanID, not_compliant) :-
    not_compliant(PlanID).

% === Conditions Precedent Tracking ===
% Conditions from the plan that must be fulfilled

condition_precedent(PlanID, 'DTCP license renewal') :-
    plan_detail(PlanID, conditions_precedent_listed, yes),
    plan_detail(PlanID, dtcp_license_renewable, _).

condition_precedent(PlanID, 'Invalidation of preferential transactions by NCLT') :-
    plan_detail(PlanID, conditions_precedent_listed, yes),
    plan_detail(PlanID, contravenes_any_law, conditional).

condition_precedent(PlanID, 'Home buyer consent for upfront INR 3 Cr payment') :-
    plan_detail(PlanID, conditions_precedent_listed, yes).

condition_precedent(PlanID, 'NCLT approval of waivers, reliefs and concessions') :-
    plan_detail(PlanID, conditions_precedent_listed, yes).

% === Diagnostic Output ===

check_conditional_compliance(PlanID) :-
    writeln(''),
    writeln('===== CONDITIONAL COMPLIANCE ANALYSIS ====='),

    % Individual rule checks with state
    writeln(''),
    writeln('Rule-by-rule status:'),
    check_rule_state(PlanID, cirp_cost_payment, provides_cirp_priority, 'Reg 38(1): CIRP cost priority'),
    check_rule_state(PlanID, oc_payment, provides_oc_fair_payment, 'Sec 30(2)(b): OC fair payment'),
    check_rule_state(PlanID, dissenting_fc_payment, provides_dissenting_fc_payment, 'Sec 30(2)(b): Dissenting FC payment'),
    check_rule_state(PlanID, management_post_approval, provides_management_plan, 'Sec 30(2)(c): Management plan'),
    check_rule_state(PlanID, supervision_mechanism, provides_supervision_mechanism, 'Sec 30(2)(d): Supervision mechanism'),
    check_rule_state(PlanID, contravenes_any_law, no_legal_contravention, 'Sec 30(2)(e): No legal contravention'),
    check_rule_state(PlanID, affidavit_29A_submitted, has_affidavit_sec29A, 'Sec 30(1): Affidavit Sec 29A'),

    % Overall status
    writeln(''),
    (plan_status(PlanID, compliant) ->
        writeln('OVERALL: COMPLIANT (all rules pass unconditionally)') ;
     (plan_status(PlanID, not_compliant) ->
        writeln('OVERALL: NOT COMPLIANT (core mandatory rules fail)') ;
        (plan_status(PlanID, conditional) ->
            writeln('OVERALL: CONDITIONALLY COMPLIANT (passes if conditions precedent are met)')
        )
     )
    ),

    % List conditions precedent
    writeln(''),
    writeln('Conditions precedent that must be fulfilled:'),
    findall(CP, condition_precedent(PlanID, CP), CPs),
    (CPs = [] ->
        writeln('  (none identified)') ;
        forall(member(CP, CPs), format('  - ~w~n', [CP]))
    ),

    % List compliance conditions
    findall(Cond, compliance_condition(PlanID, Cond), Conds),
    (Conds \= [] ->
        writeln(''),
        writeln('Compliance conditions (rules that pass only if conditions are met):'),
        forall(member(Cond, Conds), format('  * ~w~n', [Cond]))
    ; true),

    writeln(''),
    writeln('===================================================='),
    halt.

% Check individual rule and determine state
check_rule_state(PlanID, Field, Rule, Label) :-
    (call(Rule, PlanID) ->
        format('  PASS:          ~w~n', [Label])
    ;   plan_detail(PlanID, Field, conditional) ->
        format('  CONDITIONAL:   ~w [depends on NCLT/external approval]~n', [Label])
    ;   plan_detail(PlanID, Field, not_mentioned) ->
        format('  NOT ADDRESSED: ~w [document does not address this]~n', [Label])
    ;   plan_detail(PlanID, Field, Val) ->
        format('  FAIL:          ~w [value: ~w]~n', [Label, Val])
    ;   format('  FAIL:          ~w [MISSING DATA]~n', [Label])
    ).