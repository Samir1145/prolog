% --- Regulation 38(1A): Stakeholder Interest Statement ---
% "The resolution plan shall contain a statement as to how it has dealt
%  with the interests of all stakeholders including financial creditors
%  and operational creditors."

reg38_1a_satisfied(PlanID) :-
    plan_detail(PlanID, stakeholder_interest_statement, yes).

% --- Regulation 38(2): Viability of Resolution Plan ---
% The resolution professional must examine the viability of the plan.
% Key indicators:
%   - Sufficient funding for completion
%   - Credible sources of funds
%   - No unexplained cashflow gaps

plan_viable(PlanID) :-
    plan_detail(PlanID, earnest_money_submitted, yes),
    plan_detail(PlanID, conditions_precedent_listed, yes),
    has_completion_funding(PlanID),
    \+ has_unexplained_cashflow_gap(PlanID).

has_completion_funding(PlanID) :-
    plan_detail(PlanID, project_completion_cost_cr, Cost),
    plan_detail(PlanID, has_funding_arrangement, yes).

% Fallback: if funding arrangement not explicitly mentioned,
% check if RA has committed to cover shortfall
has_completion_funding(PlanID) :-
    plan_detail(PlanID, ra_covers_shortfall, yes).

has_unexplained_cashflow_gap(PlanID) :-
    plan_detail(PlanID, cashflow_gap_exists, yes).

% --- Regulation 38(1)(b): Liquidation value payment to operational creditors ---
% The plan must provide that operational creditors receive an amount
% not less than the amount they would receive in liquidation.

oc_minimum_payment(PlanID) :-
    plan_detail(PlanID, oc_payment, Amount),
    plan_detail(PlanID, liquidation_value_oc, LiqVal),
    Amount >= LiqVal.

% If liquidation value to OCs is NIL, even zero payment satisfies the rule
oc_minimum_payment(PlanID) :-
    plan_detail(PlanID, liquidation_value_oc, 0).

% --- Regulation 38(1)(b) second proviso: Dissenting operational creditors ---
dissenting_oc_payment(PlanID) :-
    plan_detail(PlanID, dissenting_oc_payment, yes).

dissenting_oc_payment(PlanID) :-
    plan_detail(PlanID, dissenting_oc_payment, not_mentioned).

% If there are no dissenting OCs, this is automatically satisfied
dissenting_oc_payment(PlanID) :-
    plan_detail(PlanID, liquidation_value_oc, 0),
    plan_detail(PlanID, oc_payment, 0).

% --- Full Regulation 38 check ---
reg38_compliant(PlanID) :-
    reg38_1a_satisfied(PlanID),
    plan_viable(PlanID),
    oc_minimum_payment(PlanID).

% --- Diagnostic output ---
check_reg38(PlanID) :-
    writeln(''),
    writeln('===== REGULATION 38 COMPLIANCE REPORT ====='),
    check_rule(PlanID, stakeholder_interest_statement, reg38_1a_satisfied, 'Reg 38(1A): Stakeholder interest statement'),
    check_rule(PlanID, has_funding_arrangement, plan_viable, 'Reg 38(2): Plan viability'),
    check_rule(PlanID, oc_payment, oc_minimum_payment, 'Reg 38(1)(b): OC minimum payment'),
    check_rule(PlanID, dissenting_oc_payment, dissenting_oc_payment, 'Reg 38(1)(b) proviso: Dissenting OC payment'),
    writeln(''),
    (reg38_compliant(PlanID) -> writeln('OVERALL: REG 38 COMPLIANT') ; writeln('OVERALL: REG 38 NOT COMPLIANT')),
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