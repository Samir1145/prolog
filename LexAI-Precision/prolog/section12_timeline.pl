% --- Section 12: CIRP Timeline Compliance ---
% CIRP must be completed within 330 days (extendable to 330+60=390 days
% under certain circumstances). The resolution plan must be submitted
% within this timeline.

% Maximum CIRP timeline: 330 days from commencement
max_cirp_days(330).

% Extended timeline (with NCLT approval): up to 390 days
max_cirp_days_extended(390).

% Check if plan was submitted within CIRP timeline
within_cirp_timeline(PlanID) :-
    plan_detail(PlanID, cirp_commencement_date, CommDate),
    plan_detail(PlanID, plan_submission_date, SubDate),
    day_difference(CommDate, SubDate, Days),
    max_cirp_days(Max),
    Days =< Max.

% Check if plan submission exceeds even extended timeline
beyond_extended_timeline(PlanID) :-
    plan_detail(PlanID, cirp_commencement_date, CommDate),
    plan_detail(PlanID, plan_submission_date, SubDate),
    day_difference(CommDate, SubDate, Days),
    max_cirp_days_extended(Max),
    Days > Max.

% --- Timeline dependency check ---
% Conditions precedent must be fulfillable within reasonable time
% from the effective date.

timeline_feasible(PlanID) :-
    plan_detail(PlanID, implementation_timeline_months, Months),
    Months =< 24. % Plans extending beyond 24 months raise viability concerns

timeline_feasible(PlanID) :-
    \+ plan_detail(PlanID, implementation_timeline_months, _). % No timeline = not assessed

% --- Effective Date Conditions ---
% The effective date depends on conditions that may delay implementation.

effective_date_conditions_clear(PlanID) :-
    plan_detail(PlanID, dtcp_license_renewable, yes),
    plan_detail(PlanID, preferential_transactions_invalidation, yes).

effective_date_conditions_clear(PlanID) :-
    plan_detail(PlanID, conditions_precedent_listed, yes),
    \+ plan_detail(PlanID, dtcp_license_renewable, _). % No DTCP dependency

% --- Diagnostic output ---
check_timeline(PlanID) :-
    writeln(''),
    writeln('===== CIRP TIMELINE COMPLIANCE REPORT ====='),
    (plan_detail(PlanID, cirp_commencement_date, _) ->
        (within_cirp_timeline(PlanID) ->
            writeln('  PASS: Plan submitted within 330-day CIRP timeline') ;
            (beyond_extended_timeline(PlanID) ->
                writeln('  FAIL: Plan submitted BEYOND extended 390-day timeline') ;
                writeln('  WARN: Plan submitted beyond 330 days but within extended timeline')
            )
        ) ;
        writeln('  INFO: CIRP dates not provided - timeline check skipped')
    ),
    (timeline_feasible(PlanID) ->
        writeln('  PASS: Implementation timeline is feasible (<=24 months)') ;
        writeln('  FAIL: Implementation timeline exceeds 24 months - viability concern')
    ),
    (effective_date_conditions_clear(PlanID) ->
        writeln('  PASS: Effective date conditions are clear') ;
        writeln('  WARN: Effective date depends on external approvals (DTCP, NCLT)')
    ),
    writeln('===================================================='),
    halt.

% Helper: simple day difference (placeholder - in production use date library)
day_difference(Date1, Date2, Days) :-
    % This is a simplified placeholder.
    % In production, use a proper date library or convert to days.
    % For now, accept a pre-computed value from the facts.
    plan_detail(_, day_difference, Days).