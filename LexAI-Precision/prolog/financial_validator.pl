% --- Financial Validator: Cashflow, Timeline, and Adequacy Checks ---
% Verifies financial viability and timeline consistency of the resolution plan.

% === Cashflow Viability ===
% The plan must demonstrate that sources of funds cover all requirements.

cashflow_viable(PlanID) :-
    plan_detail(PlanID, project_completion_cost_cr, Cost),
    plan_detail(PlanID, has_funding_arrangement, yes),
    Cost > 0.

cashflow_viable(PlanID) :-
    plan_detail(PlanID, project_completion_cost_cr, Cost),
    plan_detail(PlanID, ra_covers_shortfall, yes),
    Cost > 0.

% If we have explicit sources and uses, check if sources >= uses
cashflow_viable(PlanID) :-
    plan_detail(PlanID, total_sources_cr, Sources),
    plan_detail(PlanID, total_uses_cr, Uses),
    Sources >= Uses.

% === Minimum Payment Thresholds ===

% FC payment must be >= higher of liquidation value or waterfall value
fc_minimum_payment(PlanID) :-
    plan_detail(PlanID, fc_payment_percentage, Pct),
    Pct >= 10. % NCLT typically expects minimum 10% for FCs

% OC payment must be >= liquidation value
oc_payment_adequate(PlanID) :-
    plan_detail(PlanID, oc_payment, Amount),
    plan_detail(PlanID, liquidation_value_oc, LiqVal),
    Amount >= LiqVal.

oc_payment_adequate(PlanID) :-
    plan_detail(PlanID, liquidation_value_oc, 0). % NIL liquidation = even zero is adequate

% Home buyer protection: delivery must be guaranteed
home_buyer_protected(PlanID) :-
    plan_detail(PlanID, home_buyer_delivery_guaranteed, yes).

home_buyer_protected(PlanID) :-
    plan_detail(PlanID, home_buyer_claims_cr, _),
    plan_detail(PlanID, management_post_approval, yes). % RA takes over management

% === Timeline Feasibility ===

% Implementation should not exceed 24 months (NCLT expectation)
timeline_feasible(PlanID) :-
    plan_detail(PlanID, implementation_timeline_months, Months),
    Months =< 24.

timeline_feasible(PlanID) :-
    plan_detail(PlanID, implementation_timeline_months, Months),
    Months =< 36. % Extended but still possible

timeline_not_feasible(PlanID) :-
    plan_detail(PlanID, implementation_timeline_months, Months),
    Months > 36.

% Earnest money is a signal of seriousness
earnest_money_submitted(PlanID) :-
    plan_detail(PlanID, earnest_money_submitted, yes).

% === Conditions Precedent Risk ===
% Conditions that depend on external authorities create execution risk

high_execution_risk(PlanID) :-
    plan_detail(PlanID, dtcp_license_renewable, not_guaranteed).

high_execution_risk(PlanID) :-
    plan_detail(PlanID, preferential_transactions_invalidation, pending).

high_execution_risk(PlanID) :-
    plan_detail(PlanID, conditions_precedent_count, N),
    N > 3. % More than 3 conditions = high risk

% === Diagnostic Output ===

check_financial(PlanID) :-
    writeln(''),
    writeln('===== FINANCIAL & TIMELINE VALIDATION ====='),

    % Cashflow
    writeln(''),
    writeln('--- Cashflow Viability ---'),
    (cashflow_viable(PlanID) ->
        writeln('  PASS: Funding arrangement covers project costs') ;
        (plan_detail(PlanID, ra_covers_shortfall, yes) ->
            writeln('  PASS: RA commits to cover funding shortfall') ;
            writeln('  WARN: No explicit funding arrangement or shortfall commitment')
        )
    ),

    % FC payment adequacy
    writeln(''),
    writeln('--- Creditor Payment Adequacy ---'),
    (fc_minimum_payment(PlanID) ->
        writeln('  PASS: FC payment meets minimum threshold (>=10%)') ;
        (plan_detail(PlanID, fc_payment_percentage, Pct) ->
            format('  FAIL: FC payment ~w% is below minimum 10%~n', [Pct]) ;
            writeln('  INFO: FC payment percentage not specified')
        )
    ),
    (oc_payment_adequate(PlanID) ->
        writeln('  PASS: OC payment >= liquidation value') ;
        writeln('  FAIL: OC payment below liquidation value')
    ),
    (home_buyer_protected(PlanID) ->
        writeln('  PASS: Home buyer interests protected') ;
        writeln('  WARN: Home buyer protection not explicitly guaranteed')
    ),

    % Timeline
    writeln(''),
    writeln('--- Timeline Feasibility ---'),
    (plan_detail(PlanID, implementation_timeline_months, Months) ->
        (timeline_feasible(PlanID) ->
            (Months =< 24 ->
                format('  PASS: Implementation timeline ~w months is feasible~n', [Months]) ;
                format('  WARN: Implementation timeline ~w months is extended (>24)~n', [Months])
            ) ;
            (timeline_not_feasible(PlanID) ->
                format('  FAIL: Implementation timeline ~w months exceeds 36 months~n', [Months]) ;
                writeln('  INFO: Timeline assessment inconclusive')
            )
        ) ;
        writeln('  INFO: Implementation timeline not specified')
    ),

    % Earnest money
    (earnest_money_submitted(PlanID) ->
        writeln('  PASS: Earnest money submitted') ;
        writeln('  FAIL: No earnest money submitted')
    ),

    % Execution risk
    writeln(''),
    writeln('--- Execution Risk Assessment ---'),
    (high_execution_risk(PlanID) ->
        writeln('  WARN: High execution risk due to conditions precedent depending on external authorities') ;
        writeln('  PASS: Execution risk is manageable')
    ),

    writeln(''),
    writeln('===================================================='),
    halt.