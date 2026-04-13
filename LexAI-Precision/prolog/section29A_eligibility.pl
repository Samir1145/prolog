% --- Section 29A Eligibility Logic ---
% Facts use arity-2 format: disqualified_pred(RA, yes/no)

:- discontiguous npa_status/2.

is_eligible_29A(RA) :-
    \+ is_disqualified(RA),
    \+ has_ineligible_connected_person(RA).

% --- Disqualification Criteria (Section 29A Clauses a-h) ---

is_disqualified(RA) :- undischarged_insolvent(RA, yes).
is_disqualified(RA) :- wilful_defaulter(RA, yes).
is_disqualified(RA) :- has_unresolved_npa(RA).
is_disqualified(RA) :- convicted_offence(RA, yes).
is_disqualified(RA) :- disqualified_director(RA, yes).
is_disqualified(RA) :- prohibited_by_sebi(RA, yes).
is_disqualified(RA) :- involved_in_fraudulent_transactions(RA, yes).
is_disqualified(RA) :- unpaid_invoked_guarantee(RA).

% --- Detailed Logic for Clauses ---

% Clause (c): NPA for > 1 year is a bar UNLESS overdue amounts are paid
has_unresolved_npa(RA) :-
    npa_status(RA, over_one_year),
    \+ npa_overdue_paid(RA, yes).

% Clause (h): Guarantee must be invoked AND remain unpaid to disqualify
unpaid_invoked_guarantee(RA) :-
    guarantee_executed(RA, corporate_debtor, yes),
    guarantee_invoked(RA, yes),
    guarantee_unpaid(RA, yes).

% Clause (j): "Connected Person" logic
has_ineligible_connected_person(RA) :-
    connected_person(RA, CP),
    is_disqualified(CP).