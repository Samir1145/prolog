% ============================================================
% Insolvency and Bankruptcy Code (IBC) - Section 7
% Corporate Insolvency Resolution Process (CIRP)
% Financial Creditor Application
% ============================================================

:- module(ibc_section7, [
    can_file_application/1,
    valid_applicant/1,
    minimum_creditors_required/3,
    application_requirements/2,
    adjudicating_authority_action/2,
    cirp_commencement/1
]).


% ============================================================
% SECTION 7(1) - Who can file
% ============================================================

% A financial creditor can file either by itself or jointly
can_file_application(Applicant) :-
    valid_applicant(Applicant),
    default_has_occurred.

valid_applicant(financial_creditor(_)).
valid_applicant(joint_financial_creditors(_List)).
valid_applicant(person_on_behalf_of_financial_creditor(_)).

% Default includes debt owed to ANY financial creditor, not just applicant
default_includes_others(CorporateDebtor) :-
    financial_debt_owed(CorporateDebtor, _AnyCreditor).


% ============================================================
% SECTION 7(1) PROVISOS - Minimum creditor thresholds
% ============================================================

% Proviso 1 & 2: Special classes of financial creditors (s.21(6A)(a) and (b))
% and allottees under real estate projects

minimum_creditors_required(Class, TotalInClass, Required) :-
    hundred_or_ten_percent(TotalInClass, Required),
    creditor_class(Class).

hundred_or_ten_percent(Total, 100) :-
    Total >= 1000.  % 10% of 1000 = 100, so threshold is 100

hundred_or_ten_percent(Total, Required) :-
    Total < 1000,
    Required is max(1, round(Total * 0.10)).

creditor_class(section_21_6a_a).
creditor_class(section_21_6a_b).
creditor_class(real_estate_allottees(_Project)).

% Real estate allottees must file jointly under the SAME project
valid_allottee_application(Project, Allottees) :-
    length(Allottees, Count),
    total_allottees_in_project(Project, Total),
    minimum_creditors_required(real_estate_allottees(Project), Total, MinRequired),
    Count >= MinRequired.

% Amendment Act 2020: Pending applications must be modified within 30 days
% or deemed withdrawn
pending_application_deadline_days(30).

must_modify_or_withdraw(Application) :-
    filed_before_amendment_2020(Application),
    not_yet_admitted(Application).


% ============================================================
% SECTION 7(2) - Form and manner
% ============================================================

application_requirements(form, prescribed_form).
application_requirements(fee, prescribed_fee).
application_requirements(manner, prescribed_manner).


% ============================================================
% SECTION 7(3) - Documents to furnish
% ============================================================

required_documents(record_of_default).       % 7(3)(a)
required_documents(proposed_irp_name).       % 7(3)(b)
required_documents(other_info_as_specified). % 7(3)(c)

% Record of default can be:
record_of_default_source(information_utility_record).
record_of_default_source(other_specified_evidence).


% ============================================================
% SECTION 7(4) - Adjudicating Authority's duty to ascertain
% ============================================================

ascertainment_deadline_days(14). % Within 14 days of receiving application

% AA must ascertain default from:
ascertain_default_from(information_utility_records).
ascertain_default_from(evidence_by_financial_creditor).

% If AA fails to pass order within 14 days, must record reasons in writing
must_record_reasons(adjudicating_authority) :-
    not_passed_order_within_deadline.


% ============================================================
% SECTION 7(5) - Admission or Rejection
% ============================================================

adjudicating_authority_action(admit, Application) :-
    default_has_occurred,
    application_is_complete(Application),
    no_disciplinary_proceedings_pending(proposed_irp(Application)).

adjudicating_authority_action(reject, Application) :-
    (   default_not_occurred
    ;   application_is_incomplete(Application)
    ;   disciplinary_proceedings_pending(proposed_irp(Application))
    ).

% Proviso to 7(5)(b): Must give notice before rejection for defects
notice_before_rejection(Application) :-
    adjudicating_authority_action(reject, Application),
    rejection_reason(incomplete_application).

rectification_window_days(7). % 7 days to fix defect after notice


% ============================================================
% SECTION 7(6) - Commencement of CIRP
% ============================================================

cirp_commencement(CorporateDebtor) :-
    application_admitted(CorporateDebtor, AdmissionDate),
    cirp_start_date(CorporateDebtor, AdmissionDate).

% CIRP commences from date of ADMISSION of application
cirp_start_date(CorporateDebtor, Date) :-
    application_admitted(CorporateDebtor, Date).


% ============================================================
% SECTION 7(7) - Communication of orders
% ============================================================

communication_deadline_days(7). % Within 7 days of admission/rejection

communicate_order(admit, Application) :-
    notify(financial_creditor(Application)),
    notify(corporate_debtor(Application)).

communicate_order(reject, Application) :-
    notify(financial_creditor(Application)).


% ============================================================
% HELPER PREDICATES (facts to be asserted at runtime)
% ============================================================

% These are to be asserted dynamically based on case facts:
:- dynamic(default_has_occurred/0).
:- dynamic(default_not_occurred/0).
:- dynamic(application_is_complete/1).
:- dynamic(application_is_incomplete/1).
:- dynamic(no_disciplinary_proceedings_pending/1).
:- dynamic(disciplinary_proceedings_pending/1).
:- dynamic(application_admitted/2).
:- dynamic(not_passed_order_within_deadline/0).
:- dynamic(filed_before_amendment_2020/1).
:- dynamic(not_yet_admitted/1).
:- dynamic(total_allottees_in_project/2).
:- dynamic(financial_debt_owed/2).
:- dynamic(rejection_reason/1).


% ============================================================
% EXAMPLE QUERY USAGE
% ============================================================
% To check if a creditor can file:
%   ?- assert(default_has_occurred), can_file_application(financial_creditor(acme_bank)).
%
% To check minimum allottees needed for a project with 500 total:
%   ?- minimum_creditors_required(real_estate_allottees(project_x), 500, N).
%   N = 50.
%
% To check if application should be admitted:
%   ?- assert(default_has_occurred),
%      assert(application_is_complete(app_001)),
%      assert(no_disciplinary_proceedings_pending(proposed_irp(app_001))),
%      adjudicating_authority_action(admit, app_001).