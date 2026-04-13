% --- Section 29A(j): Connected Persons Eligibility ---
% IBC Section 29A defines "connected person" broadly.
% This module implements the 9 categories of connected persons
% under Section 5(24)(a)-(i) of the Companies Act (as applied by IBC).

% === Connected Person Categories ===

% Category 1: Director or key managerial personnel
connected_person_category(RA, CP, director_or_kmp) :-
    is_director(CP, RA, yes);
    is_kmp(CP, RA, yes).

% Category 2: Relatives (spouse, parent, sibling, child)
connected_person_category(RA, CP, relative) :-
    is_relative(CP, RA, yes).

% Category 3: Partnership firm where RA or relative is partner
connected_person_category(RA, CP, partnership) :-
    is_partner(RA, CP, yes).

% Category 4: Private company where RA/relative is director/manager
connected_person_category(RA, CP, private_company_control) :-
    is_director(CP, _Company, yes),
    is_director(RA, _Company, yes).

% Category 5: Body corporate where RA/relative has >2% shareholding
connected_person_category(RA, CP, body_corporate_shareholding) :-
    has_shareholding(RA, CP, above_2_percent, yes).

% Category 6: Where RA/relative is a guarantor
connected_person_category(RA, CP, guarantor) :-
    guarantee_executed(RA, CP, yes).

% Category 7: Trust where RA/relative is trustee/beneficiary
connected_person_category(RA, CP, trust) :-
    is_trustee(RA, CP, yes).
connected_person_category(RA, CP, trust) :-
    is_beneficiary(RA, CP, yes).

% Category 8: Entity where RA/relative has control (management or affairs)
connected_person_category(RA, CP, control) :-
    has_control(RA, CP, yes).

% Category 9: Associate company within same group
connected_person_category(RA, CP, associate_company) :-
    is_associate_company(CP, RA, yes).

% === Transitive Disqualification ===
% If ANY connected person is disqualified under Sec 29A,
% the RA is INELIGIBLE.

ra_ineligible_through_connected_person(RA) :-
    connected_person(RA, CP),
    is_disqualified(CP).

ra_ineligible_through_connected_person(RA) :-
    connected_person_category(RA, CP, _),
    is_disqualified(CP).

% === Enhanced Eligibility Check ===
% Extends the base is_eligible_29A with connected person categories

is_eligible_29A_enhanced(RA) :-
    \+ is_disqualified(RA),
    \+ ra_ineligible_through_connected_person(RA),
    \+ has_ineligible_connected_person(RA).

% === Diagnostic Output ===
check_connected_persons(RA) :-
    writeln(''),
    writeln('===== SECTION 29A(j) CONNECTED PERSON ANALYSIS ====='),
    findall(CP, connected_person(RA, CP), DirectCPs),
    findall(CP-Cat, connected_person_category(RA, CP, Cat), Categorized),
    (DirectCPs = [] ->
        writeln('  INFO: No direct connected persons declared') ;
        format('  Direct connected persons: ~w~n', [DirectCPs])
    ),
    (Categorized = [] ->
        writeln('  INFO: No categorized connected persons found') ;
        writeln('  Categorized connected persons:'),
        forall(member(CP-Cat, Categorized),
            format('    - ~w (~w)~n', [CP, Cat])
        )
    ),
    findall(CP, ra_ineligible_through_connected_person(RA), IneligibleCPs),
    (IneligibleCPs = [] ->
        writeln('  PASS: No ineligible connected persons found') ;
        format('  FAIL: Ineligible connected persons: ~w~n', [IneligibleCPs])
    ),
    (is_eligible_29A_enhanced(RA) ->
        writeln('  RESULT: RA ELIGIBLE (no disqualifications through connected persons)') ;
        writeln('  RESULT: RA NOT ELIGIBLE (disqualification through connected person)')
    ),
    writeln('===================================================='),
    halt.