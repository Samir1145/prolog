% Sample facts for Section 29A testing
:- discontiguous npa_status/2.

undischarged_insolvent(ra_firm_01, no).
wilful_defaulter(ra_firm_01, no).
npa_status(ra_firm_01, none).
convicted_offence(ra_firm_01, no).
disqualified_director(ra_firm_01, no).
prohibited_by_sebi(ra_firm_01, no).
involved_in_fraudulent_transactions(ra_firm_01, no).

connected_person(ra_firm_01, promoter_x).
npa_status(promoter_x, over_one_year).
npa_overdue_paid(promoter_x, no).
guarantee_executed(ra_firm_01, corporate_debtor, no).
guarantee_invoked(ra_firm_01, no).
guarantee_unpaid(ra_firm_01, no).