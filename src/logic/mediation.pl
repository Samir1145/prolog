:- dynamic(is_commercial/1).
:- dynamic(pre_litigation_agreement/1).
:- dynamic(is_criminal/1).
:- dynamic(is_constitutional_matter/1).

% Define a threshold value of 50000 for commercial disputes.
commercial_threshold(50000).

% Helper rule to evaluate the threshold.
value_above_threshold(Value) :-
    commercial_threshold(Threshold),
    Value >= Threshold.

% A case is ineligible if is_criminal(true) or is_constitutional_matter(true).
is_ineligible :- is_criminal(true).
is_ineligible :- is_constitutional_matter(true).

% A case is eligible if is_commercial(true) AND value_above_threshold(Value).
is_eligible(Value) :-
    \+ is_ineligible,
    is_commercial(true),
    value_above_threshold(Value).

% A case is eligible if pre_litigation_agreement(true).
is_eligible(_) :-
    \+ is_ineligible,
    pre_litigation_agreement(true).
