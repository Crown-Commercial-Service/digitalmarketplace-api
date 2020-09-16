# -*- coding: utf-8 -*-
import pytest
import pendulum
import copy
from app.api.business.brief import BriefUserStatus
from app.models import db, Assessment, BriefAssessment, SupplierDomain, CaseStudy, BriefResponse


rfx_data = {
    'title': 'TEST',
    'organisation': 'ABC',
    'summary': 'TEST',
    'workingArrangements': 'TEST',
    'location': [
        'New South Wales'
    ],
    'sellerCategory': '1',
    'sellers': {
        '1': {
            'name': 'Test Supplier1'
        }
    },
    'evaluationType': [
        'Response template',
        'Written proposal'
    ],
    'proposalType': [
        'Breakdown of costs',
        'Résumés'
    ],
    'requirementsDocument': [
        'TEST.pdf'
    ],
    'responseTemplate': [
        'TEST2.pdf'
    ],
    'attachments': [
        'TEST3.pdf'
    ],
    'industryBriefing': 'TEST',
    'startDate': 'ASAP',
    'contractLength': 'TEST',
    'includeWeightings': True,
    'essentialRequirements': [
        {
            'criteria': 'TEST',
            'weighting': '55'
        },
        {
            'criteria': 'TEST 2',
            'weighting': '45'
        }
    ],
    'niceToHaveRequirements': [],
    'contactNumber': '0263635544'
}

open_to_all_atm_data = {
    "areaOfExpertise": "",
    "attachments": [
        "test.pdf"
    ],
    "backgroundInformation": "Old website needs a refresh",
    "closedAt": pendulum.today(tz='Australia/Sydney').add(days=14).format('%Y-%m-%d'),
    "contactNumber": "0412345678",
    "endUsers": "Users need a new website",
    "evaluationCriteria": [
        {
            "weighting": "",
            "criteria": "Code"
        }
    ],
    "evaluationType": [],
    "includeWeightings": False,
    "industryBriefing": "",
    "internalReference": "",
    "location": [
        "Australian Capital Territory",
        "New South Wales",
        "Northern Territory",
        "Queensland",
        "Tasmania",
        "Victoria"
    ],
    "openTo": "all",
    "organisation": "Digital Transformation Agency",
    "outcome": "Update everything",
    "requestMoreInfo": "no",
    "sellerCategory": "",
    "sellerSelector": "allSellers",
    "startDate": pendulum.today(tz='Australia/Sydney').add(days=24).format('%Y-%m-%d'),
    "summary": "Build new website",
    "timeframeConstraints": "",
    "title": "New website",
    "workAlreadyDone": "None"
}

open_to_category_atm_data = {
    "areaOfExpertise": "Cyber security",
    "attachments": [
        "test.pdf"
    ],
    "backgroundInformation": "Fix potential problems",
    "closedAt": pendulum.today(tz='Australia/Sydney').add(days=14).format('%Y-%m-%d'),
    "contactNumber": "0412345678",
    "endUsers": "Users don't want to get hacked",
    "evaluationCriteria": [
        {
            "weighting": "100",
            "criteria": "Review security"
        }
    ],
    "evaluationType": [],
    "includeWeightings": True,
    "industryBriefing": "",
    "internalReference": "",
    "location": [
        "Australian Capital Territory",
        "New South Wales",
        "South Australia",
        "Tasmania",
        "Victoria",
        "Western Australia",
        "Offsite"
    ],
    "openTo": "category",
    "organisation": "Digital Transformation Agency",
    "outcome": "Make sure website is secure",
    "requestMoreInfo": "no",
    "sellerCategory": "8",
    "sellerSelector": "someSellers",
    "startDate": pendulum.today(tz='Australia/Sydney').add(days=24).format('%Y-%m-%d'),
    "summary": "Conduct security assessments on website",
    "timeframeConstraints": "",
    "title": "Security review of website",
    "workAlreadyDone": "None"
}

open_to_all_specialist_data = {
    "areaOfExpertise": "Software engineering and Development",
    "attachments": [
        "test.pdf"
    ],
    "budgetRange": "",
    "closedAt": pendulum.today(tz='Australia/Sydney').add(days=14).format('%Y-%m-%d'),
    "comprehensiveTerms": False,
    "contactNumber": "0412 345 678",
    "contractExtensions": "",
    "contractLength": "2 years",
    "essentialRequirements": [
        {
            "weighting": "",
            "criteria": "Python"
        }
    ],
    "evaluationType": [
        "Responses to selection criteria",
        "Résumés"
    ],
    "includeWeightingsEssential": False,
    "includeWeightingsNiceToHave": False,
    "internalReference": "",
    "location": [
        "Australian Capital Territory",
        "New South Wales"
    ],
    "maxRate": "1000",
    "niceToHaveRequirements": [
        {
            "weighting": "",
            "criteria": ""
        }
    ],
    "numberOfSuppliers": "3",
    "openTo": "all",
    "organisation": "Digital Transformation Agency",
    "preferredFormatForRates": "dailyRate",
    "securityClearance": "noneRequired",
    "securityClearanceCurrent": "",
    "securityClearanceObtain": "",
    "securityClearanceOther": "",
    "sellerCategory": "6",
    "sellerSelector": "allSellers",
    "sellers": {},
    "startDate": pendulum.today(tz='Australia/Sydney').add(days=24).format('%Y-%m-%d'),
    "summary": "Code",
    "title": "Developer"
}

open_to_selected_specialist_data = {
    "areaOfExpertise": "Software engineering and Development",
    "attachments": [
        "test.pdf"
    ],
    "budgetRange": "",
    "closedAt": pendulum.today(tz='Australia/Sydney').add(days=14).format('%Y-%m-%d'),
    "comprehensiveTerms": False,
    "contactNumber": "0412 345 678",
    "contractExtensions": "",
    "contractLength": "2 years",
    "essentialRequirements": [
        {
            "weighting": "",
            "criteria": "Code"
        }
    ],
    "evaluationType": [
        "Responses to selection criteria",
        "Résumés"
    ],
    "includeWeightingsEssential": False,
    "includeWeightingsNiceToHave": False,
    "internalReference": "",
    "location": [
        "New South Wales",
        "Australian Capital Territory"
    ],
    "maxRate": "1000",
    "niceToHaveRequirements": [
        {
            "weighting": "",
            "criteria": ""
        }
    ],
    "numberOfSuppliers": "3",
    "openTo": "selected",
    "organisation": "Digital Transformation Agency",
    "preferredFormatForRates": "dailyRate",
    "securityClearance": "noneRequired",
    "securityClearanceCurrent": "",
    "securityClearanceObtain": "",
    "securityClearanceOther": "",
    "sellerCategory": "6",
    "sellerSelector": "someSellers",
    "sellers": {
        "1": {
            "name": "Test Supplier1"
        }
    },
    "startDate": pendulum.today(tz='Australia/Sydney').add(days=24).format('%Y-%m-%d'),
    "summary": "Code",
    "title": "Developer"
}

open_to_selected_specialist_data_not_invited = copy.copy(open_to_selected_specialist_data)
open_to_selected_specialist_data_not_invited['sellers'] = {
    '999': {
        'name': 'test'
    }
}


@pytest.fixture()
def supplier_domains(app, request, domains, suppliers):
    params = request.param if hasattr(request, 'param') else {}
    status = params['status'] if 'status' in params else 'assessed'
    price_status = params['price_status'] if 'price_status' in params else 'approved'
    with app.app_context():
        for domain in domains:
            db.session.add(SupplierDomain(
                supplier_id=suppliers[0].id,
                domain_id=domain.id,
                status=status,
                price_status=price_status
            ))
            db.session.flush()
        db.session.commit()
        yield SupplierDomain.query.all()


@pytest.fixture()
def assessments(app, supplier_domains):
    with app.app_context():
        for sd in supplier_domains:
            db.session.add(Assessment(
                supplier_domain_id=sd.id
            ))
            db.session.flush()
        db.session.commit()
        yield Assessment.query.all()


@pytest.fixture()
def brief_assessments(app, assessments):
    with app.app_context():
        for a in assessments:
            db.session.add(BriefAssessment(
                brief_id=1,
                assessment_id=a.id
            ))
            db.session.flush()
        db.session.commit()
        yield BriefAssessment.query.all()


@pytest.fixture()
def brief_response(app):
    with app.app_context():
        db.session.add(BriefResponse(
            id=1,
            brief_id=1,
            supplier_code=1,
            submitted_at=pendulum.now(),
            data={}
        ))

        db.session.commit()
        yield BriefResponse.query.get(1)


@pytest.mark.parametrize(
    'rfx_brief',
    [{'data': rfx_data}], indirect=True
)
def test_rfx_brief_user_status_selected_seller(rfx_brief, supplier_user, case_studies, brief_assessments):
    user_status = BriefUserStatus(rfx_brief, supplier_user)
    assert user_status.is_approved_seller()
    assert not user_status.is_recruiter_only()
    assert user_status.is_assessed_in_any_category()
    assert not user_status.has_evidence_in_draft_for_category()
    assert user_status.is_assessed_for_category()
    assert not user_status.is_awaiting_domain_assessment()
    assert not user_status.is_awaiting_application_assessment()
    assert not user_status.has_been_assessed_for_brief()
    assert user_status.can_respond()
    assert not user_status.has_responded()


@pytest.mark.parametrize(
    'rfx_brief',
    [{'data': rfx_data}], indirect=True
)
def test_rfx_brief_user_status_selected_seller_responded(rfx_brief, supplier_user, case_studies, brief_assessments,
                                                         brief_response):
    user_status = BriefUserStatus(rfx_brief, supplier_user)
    assert user_status.is_approved_seller()
    assert not user_status.is_recruiter_only()
    assert user_status.is_assessed_in_any_category()
    assert not user_status.has_evidence_in_draft_for_category()
    assert user_status.is_assessed_for_category()
    assert not user_status.is_awaiting_domain_assessment()
    assert not user_status.is_awaiting_application_assessment()
    assert not user_status.has_been_assessed_for_brief()
    assert user_status.can_respond()
    assert user_status.has_responded()


rfx_data_not_selected = copy.copy(rfx_data)
rfx_data_not_selected['sellers'] = {
    '999': {
        'name': 'test'
    }
}


@pytest.mark.parametrize(
    'rfx_brief',
    [{'data': rfx_data_not_selected}], indirect=True
)
def test_rfx_brief_user_status_non_selected_seller(rfx_brief, supplier_user, case_studies, brief_assessments):
    user_status = BriefUserStatus(rfx_brief, supplier_user)
    assert user_status.is_approved_seller()
    assert not user_status.is_recruiter_only()
    assert user_status.is_assessed_in_any_category()
    assert not user_status.has_evidence_in_draft_for_category()
    assert user_status.is_assessed_for_category()
    assert not user_status.is_awaiting_domain_assessment()
    assert not user_status.is_awaiting_application_assessment()
    assert not user_status.has_been_assessed_for_brief()
    assert not user_status.can_respond()
    assert not user_status.has_responded()


@pytest.mark.parametrize(
    'atm_brief',
    [{'data': open_to_all_atm_data}], indirect=True
)
def test_atm_brief_user_status_open_to_all_assessed_seller(atm_brief, supplier_user, case_studies, brief_assessments):
    user_status = BriefUserStatus(atm_brief, supplier_user)
    assert user_status.is_approved_seller()
    assert not user_status.is_recruiter_only()
    assert user_status.is_assessed_in_any_category()
    assert not user_status.has_evidence_in_draft_for_category()
    assert not user_status.is_assessed_for_category()
    assert not user_status.is_awaiting_domain_assessment()
    assert not user_status.is_awaiting_application_assessment()
    assert not user_status.has_been_assessed_for_brief()
    assert user_status.can_respond()
    assert not user_status.has_responded()


@pytest.mark.parametrize(
    'atm_brief',
    [{'data': open_to_all_atm_data}], indirect=True
)
def test_atm_brief_user_status_open_to_all_assessed_seller_responded(atm_brief, supplier_user, case_studies,
                                                                     brief_assessments, brief_response):
    user_status = BriefUserStatus(atm_brief, supplier_user)
    assert user_status.is_approved_seller()
    assert not user_status.is_recruiter_only()
    assert user_status.is_assessed_in_any_category()
    assert not user_status.has_evidence_in_draft_for_category()
    assert not user_status.is_assessed_for_category()
    assert not user_status.is_awaiting_domain_assessment()
    assert not user_status.is_awaiting_application_assessment()
    assert not user_status.has_been_assessed_for_brief()
    assert user_status.can_respond()
    assert user_status.has_responded()


@pytest.mark.parametrize(
    'atm_brief',
    [{'data': open_to_all_atm_data}], indirect=True
)
def test_atm_brief_user_status_open_to_all_unassessed_seller(atm_brief, supplier_user):
    user_status = BriefUserStatus(atm_brief, supplier_user)
    assert user_status.is_approved_seller()
    assert not user_status.is_recruiter_only()
    assert not user_status.is_assessed_in_any_category()
    assert not user_status.has_evidence_in_draft_for_category()
    assert not user_status.is_assessed_for_category()
    assert not user_status.is_awaiting_domain_assessment()
    assert not user_status.is_awaiting_application_assessment()
    assert not user_status.has_been_assessed_for_brief()
    assert not user_status.can_respond()
    assert not user_status.has_responded()


@pytest.mark.parametrize(
    'atm_brief',
    [{'data': open_to_category_atm_data}], indirect=True
)
def test_atm_brief_user_status_open_to_category_assessed_seller(atm_brief, supplier_user, case_studies,
                                                                brief_assessments):
    user_status = BriefUserStatus(atm_brief, supplier_user)
    assert user_status.is_approved_seller()
    assert not user_status.is_recruiter_only()
    assert user_status.is_assessed_in_any_category()
    assert not user_status.has_evidence_in_draft_for_category()
    assert user_status.is_assessed_for_category()
    assert not user_status.is_awaiting_domain_assessment()
    assert not user_status.is_awaiting_application_assessment()
    assert not user_status.has_been_assessed_for_brief()
    assert user_status.can_respond()
    assert not user_status.has_responded()


@pytest.mark.parametrize(
    'atm_brief',
    [{'data': open_to_category_atm_data}], indirect=True
)
def test_atm_brief_user_status_open_to_category_assessed_seller_responded(atm_brief, supplier_user, case_studies,
                                                                          brief_assessments, brief_response):
    user_status = BriefUserStatus(atm_brief, supplier_user)
    assert user_status.is_approved_seller()
    assert not user_status.is_recruiter_only()
    assert user_status.is_assessed_in_any_category()
    assert not user_status.has_evidence_in_draft_for_category()
    assert user_status.is_assessed_for_category()
    assert not user_status.is_awaiting_domain_assessment()
    assert not user_status.is_awaiting_application_assessment()
    assert not user_status.has_been_assessed_for_brief()
    assert user_status.can_respond()
    assert user_status.has_responded()


@pytest.mark.parametrize(
    'atm_brief',
    [{'data': open_to_category_atm_data}], indirect=True
)
def test_atm_brief_user_status_open_to_category_unassessed_seller(atm_brief, supplier_user):
    user_status = BriefUserStatus(atm_brief, supplier_user)
    assert user_status.is_approved_seller()
    assert not user_status.is_recruiter_only()
    assert not user_status.is_assessed_in_any_category()
    assert not user_status.has_evidence_in_draft_for_category()
    assert not user_status.is_assessed_for_category()
    assert not user_status.is_awaiting_domain_assessment()
    assert not user_status.is_awaiting_application_assessment()
    assert not user_status.has_been_assessed_for_brief()
    assert not user_status.can_respond()
    assert not user_status.has_responded()


@pytest.mark.parametrize(
    'atm_brief',
    [{'data': open_to_category_atm_data}], indirect=True
)
@pytest.mark.parametrize(
    'supplier_domains',
    [{'status': 'unassessed', 'price_status': 'unassessed'}], indirect=True
)
def test_atm_brief_user_status_open_to_category_waiting_domain_seller(atm_brief, supplier_user, supplier_domains,
                                                                      case_studies, brief_assessments, evidence):
    user_status = BriefUserStatus(atm_brief, supplier_user)
    assert user_status.is_approved_seller()
    assert not user_status.is_recruiter_only()
    assert not user_status.is_assessed_in_any_category()
    assert not user_status.has_evidence_in_draft_for_category()
    assert not user_status.is_assessed_for_category()
    assert user_status.is_awaiting_domain_assessment()
    assert not user_status.is_awaiting_application_assessment()
    assert not user_status.has_been_assessed_for_brief()
    assert not user_status.can_respond()
    assert not user_status.has_responded()


@pytest.mark.parametrize(
    'atm_brief',
    [{'data': open_to_category_atm_data}], indirect=True
)
@pytest.mark.parametrize(
    'supplier_domains',
    [{'status': 'rejected', 'price_status': 'rejected'}], indirect=True
)
def test_atm_brief_user_status_open_to_category_rejected_domain_seller(atm_brief, supplier_user, supplier_domains,
                                                                       case_studies, brief_assessments):
    atm_brief.publish()
    user_status = BriefUserStatus(atm_brief, supplier_user)
    assert user_status.is_approved_seller()
    assert not user_status.is_recruiter_only()
    assert not user_status.is_assessed_in_any_category()
    assert not user_status.has_evidence_in_draft_for_category()
    assert not user_status.is_assessed_for_category()
    assert not user_status.is_awaiting_domain_assessment()
    assert not user_status.is_awaiting_application_assessment()
    assert user_status.has_been_assessed_for_brief()
    assert not user_status.can_respond()
    assert not user_status.has_responded()


def test_atm_brief_user_status_as_applicant(atm_brief, applicant_user, supplier_domains,
                                            case_studies, brief_assessments):
    user_status = BriefUserStatus(atm_brief, applicant_user)
    assert not user_status.is_approved_seller()
    assert not user_status.is_recruiter_only()
    assert not user_status.is_assessed_in_any_category()
    assert not user_status.has_evidence_in_draft_for_category()
    assert not user_status.is_assessed_for_category()
    assert not user_status.is_awaiting_domain_assessment()
    assert not user_status.is_awaiting_application_assessment()
    assert not user_status.has_been_assessed_for_brief()
    assert not user_status.can_respond()
    assert not user_status.has_responded()


@pytest.mark.parametrize('atm_brief', [{'data': open_to_all_atm_data}], indirect=True)
def test_can_not_respond_to_open_to_all_atm_as_recruiter(atm_brief, supplier_user):
    supplier_user.supplier.data['recruiter'] = 'yes'
    user_status = BriefUserStatus(atm_brief, supplier_user)
    result = user_status.can_respond_to_atm_opportunity()

    assert result is False


@pytest.mark.parametrize('atm_brief', [{'data': open_to_all_atm_data}], indirect=True)
@pytest.mark.parametrize('recruiter', ['both', 'no'])
def test_can_respond_to_open_to_all_atm_as_assessed_seller(atm_brief, recruiter, supplier_user, supplier_domains):
    supplier_user.supplier.data['recruiter'] = recruiter
    user_status = BriefUserStatus(atm_brief, supplier_user)
    result = user_status.can_respond_to_atm_opportunity()

    assert result is True


@pytest.mark.parametrize('atm_brief', [{'data': open_to_all_atm_data}], indirect=True)
@pytest.mark.parametrize('recruiter', ['both', 'no'])
def test_can_not_respond_to_open_to_all_atm_as_unassessed_seller(atm_brief, recruiter, supplier_user):
    supplier_user.supplier.data['recruiter'] = recruiter
    user_status = BriefUserStatus(atm_brief, supplier_user)
    result = user_status.can_respond_to_atm_opportunity()

    assert result is False


@pytest.mark.parametrize('atm_brief', [{'data': open_to_category_atm_data}], indirect=True)
def test_can_not_respond_to_open_to_category_atm_as_recruiter(atm_brief, supplier_user):
    supplier_user.supplier.data['recruiter'] = 'yes'
    user_status = BriefUserStatus(atm_brief, supplier_user)
    result = user_status.can_respond_to_atm_opportunity()

    assert result is False


@pytest.mark.parametrize('atm_brief', [{'data': open_to_category_atm_data}], indirect=True)
@pytest.mark.parametrize('recruiter', ['both', 'no'])
def test_can_respond_to_open_to_category_atm_as_assessed_seller(atm_brief, recruiter, supplier_user, supplier_domains):
    supplier_user.supplier.data['recruiter'] = recruiter
    user_status = BriefUserStatus(atm_brief, supplier_user)
    result = user_status.can_respond_to_atm_opportunity()

    assert result is True


@pytest.mark.parametrize('atm_brief', [{'data': open_to_category_atm_data}], indirect=True)
@pytest.mark.parametrize('recruiter', ['both', 'no'])
def test_can_not_respond_to_open_to_category_atm_as_unassessed_seller(atm_brief, recruiter, supplier_user):
    supplier_user.supplier.data['recruiter'] = recruiter
    user_status = BriefUserStatus(atm_brief, supplier_user)
    result = user_status.can_respond_to_atm_opportunity()

    assert result is False


@pytest.mark.parametrize('rfx_brief', [{'data': rfx_data}], indirect=True)
def test_can_not_respond_to_rfx_as_recruiter(rfx_brief, supplier_user):
    supplier_user.supplier.data['recruiter'] = 'yes'
    user_status = BriefUserStatus(rfx_brief, supplier_user)
    result = user_status.can_respond_to_rfx_or_training_opportunity()

    assert result is False


@pytest.mark.parametrize('rfx_brief', [{'data': rfx_data}], indirect=True)
@pytest.mark.parametrize('recruiter', ['both', 'no'])
def test_can_respond_to_rfx_as_assessed_invited_seller(rfx_brief, recruiter, supplier_user, supplier_domains):
    supplier_user.supplier.data['recruiter'] = recruiter
    user_status = BriefUserStatus(rfx_brief, supplier_user)
    result = user_status.can_respond_to_rfx_or_training_opportunity()

    assert result is True


@pytest.mark.parametrize('rfx_brief', [{'data': rfx_data_not_selected}], indirect=True)
@pytest.mark.parametrize('recruiter', ['both', 'no'])
def test_can_not_respond_to_rfx_as_assessed_seller_not_invited(rfx_brief, recruiter, supplier_user, supplier_domains):
    supplier_user.supplier.data['recruiter'] = recruiter
    user_status = BriefUserStatus(rfx_brief, supplier_user)
    result = user_status.can_respond_to_rfx_or_training_opportunity()

    assert result is False


@pytest.mark.parametrize('rfx_brief', [{'data': rfx_data}], indirect=True)
@pytest.mark.parametrize('recruiter', ['both', 'no'])
def test_can_not_respond_to_rfx_as_unassessed_seller(rfx_brief, recruiter, supplier_user):
    supplier_user.supplier.data['recruiter'] = recruiter
    user_status = BriefUserStatus(rfx_brief, supplier_user)
    result = user_status.can_respond_to_rfx_or_training_opportunity()

    assert result is False


@pytest.mark.parametrize('specialist_brief', [{'data': open_to_all_specialist_data}], indirect=True)
@pytest.mark.parametrize('recruiter', ['yes', 'both', 'no'])
def test_can_respond_to_open_to_all_specialist_as_assessed_seller(
    specialist_brief, recruiter, supplier_user, supplier_domains
):
    supplier_user.supplier.data['recruiter'] = recruiter
    user_status = BriefUserStatus(specialist_brief, supplier_user)
    result = user_status.can_respond_to_specialist_opportunity()

    assert result is True


@pytest.mark.parametrize('specialist_brief', [{'data': open_to_all_specialist_data}], indirect=True)
@pytest.mark.parametrize('recruiter', ['both', 'no'])
def test_can_not_respond_to_open_to_all_specialist_as_unassessed_seller(specialist_brief, recruiter, supplier_user):
    supplier_user.supplier.data['recruiter'] = recruiter
    user_status = BriefUserStatus(specialist_brief, supplier_user)
    result = user_status.can_respond_to_specialist_opportunity()

    assert result is False


@pytest.mark.parametrize('specialist_brief', [{'data': open_to_selected_specialist_data}], indirect=True)
def test_can_respond_to_open_to_selected_specialist_as_invited_recruiter(
    specialist_brief, supplier_user, supplier_domains
):
    supplier_user.supplier.data['recruiter'] = 'yes'
    user_status = BriefUserStatus(specialist_brief, supplier_user)
    result = user_status.can_respond_to_specialist_opportunity()

    assert result is True


@pytest.mark.parametrize('specialist_brief', [{'data': open_to_selected_specialist_data_not_invited}], indirect=True)
def test_can_not_respond_to_open_to_selected_specialist_as_recruiter_not_invited(specialist_brief, supplier_user):
    supplier_user.supplier.data['recruiter'] = 'yes'
    user_status = BriefUserStatus(specialist_brief, supplier_user)
    result = user_status.can_respond_to_specialist_opportunity()

    assert result is False


@pytest.mark.parametrize('specialist_brief', [{'data': open_to_selected_specialist_data}], indirect=True)
@pytest.mark.parametrize('recruiter', ['both', 'no'])
def test_can_respond_to_open_to_selected_specialist_as_assessed_invited_seller(
    specialist_brief, recruiter, supplier_user, supplier_domains
):
    supplier_user.supplier.data['recruiter'] = recruiter
    user_status = BriefUserStatus(specialist_brief, supplier_user)
    result = user_status.can_respond_to_specialist_opportunity()

    assert result is True


@pytest.mark.parametrize('specialist_brief', [{'data': open_to_selected_specialist_data_not_invited}], indirect=True)
@pytest.mark.parametrize('recruiter', ['both', 'no'])
def test_can_not_respond_to_open_to_selected_specialist_as_assessed_seller_not_invited(
    specialist_brief, recruiter, supplier_user, supplier_domains
):
    supplier_user.supplier.data['recruiter'] = recruiter
    user_status = BriefUserStatus(specialist_brief, supplier_user)
    result = user_status.can_respond_to_specialist_opportunity()

    assert result is False


@pytest.mark.parametrize('specialist_brief', [{'data': open_to_selected_specialist_data}], indirect=True)
@pytest.mark.parametrize('recruiter', ['both', 'no'])
def test_can_not_respond_to_open_to_selected_specialist_as_unassessed_seller(
    specialist_brief, recruiter, supplier_user
):
    supplier_user.supplier.data['recruiter'] = recruiter
    user_status = BriefUserStatus(specialist_brief, supplier_user)
    result = user_status.can_respond_to_specialist_opportunity()

    assert result is False
