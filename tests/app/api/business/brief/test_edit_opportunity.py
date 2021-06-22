# -*- coding: utf-8 -*-
import copy

import mock
import pendulum
import pytest

from app.api.business.brief import brief_edit_business
from app.api.services import audit_service, audit_types, brief_history_service
from app.api.services import briefs as brief_service
from app.api.services import frameworks_service, lots_service
from app.api.services import users as user_service
from app.models import Agency, Brief, Supplier, db
from tests.app.helpers import BaseApplicationTest


class TestEditOpportunity(BaseApplicationTest):
    def setup(self):
        super(TestEditOpportunity, self).setup()

    @pytest.fixture()
    def agencies(self, app):
        with app.app_context():
            db.session.add(
                Agency(
                    id=1,
                    name='Department of Schmidt',
                    domain='ng.gov.au',
                    whitelisted=True,
                    body_type='cc',
                    reports=False
                )
            )

            db.session.commit()

            yield db.session.query(Agency).all()

    @pytest.fixture()
    def suppliers(self, app):
        with app.app_context():
            db.session.add(
                Supplier(
                    abn=1,
                    code=1,
                    name='Supplier 1'
                )
            )

            db.session.add(
                Supplier(
                    abn=2,
                    code=2,
                    name='Supplier 2'
                )
            )

            db.session.commit()

            yield db.session.query(Supplier).all()

    @pytest.fixture()
    def briefs(self, app, users, suppliers):
        framework = frameworks_service.find(slug='digital-marketplace').one_or_none()
        atm_lot = lots_service.find(slug='atm').one_or_none()
        specialist_lot = lots_service.find(slug='specialist').one_or_none()
        rfx_lot = lots_service.find(slug='rfx').one_or_none()
        now = pendulum.now('utc')

        with app.app_context():
            atm_brief = Brief(
                id=1,
                data={
                    'title': 'ATM title',
                    'closedAt': pendulum.today(tz='Australia/Sydney').add(days=14).format('YYYY-MM-DD'),
                    'organisation': 'ABC',
                    'summary': 'My ATM summary',
                    'location': [
                        'New South Wales'
                    ],
                    'sellerCategory': '',
                    'openTo': 'all',
                    'requestMoreInfo': 'yes',
                    'evaluationType': [
                        'References',
                        'Case study',
                    ],
                    'attachments': [
                        'TEST3.pdf'
                    ],
                    'industryBriefing': 'TEST',
                    'startDate': 'ASAP',
                    'includeWeightings': True,
                    'evaluationCriteria': [
                        {
                            'criteria': 'TEST',
                            'weighting': '55'
                        },
                        {
                            'criteria': 'TEST 2',
                            'weighting': '45'
                        }
                    ],
                    'contactNumber': '0263635544',
                    'timeframeConstraints': 'TEST',
                    'backgroundInformation': 'TEST',
                    'outcome': 'TEST',
                    'endUsers': 'TEST',
                    'workAlreadyDone': 'TEST'
                },
                framework=framework,
                lot=atm_lot,
                users=users,
                published_at=now,
                withdrawn_at=None
            )

            atm_brief.questions_closed_at = now.add(days=3)
            atm_brief.closed_at = now.add(days=5)
            db.session.add(atm_brief)

            specialist_brief = Brief(
                id=2,
                data={
                    'areaOfExpertise': 'Software engineering and Development',
                    'attachments': [],
                    'budgetRange': '',
                    'closedAt': pendulum.today(tz='Australia/Sydney').add(days=14).format('YYYY-MM-DD'),
                    'contactNumber': '0123456789',
                    'contractExtensions': '',
                    'contractLength': '1 year',
                    'comprehensiveTerms': True,
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
                    'evaluationType': [
                        'Responses to selection criteria',
                        'Résumés'
                    ],
                    'includeWeightingsEssential': False,
                    'includeWeightingsNiceToHave': False,
                    'internalReference': '',
                    'location': [
                        'Australian Capital Territory'
                    ],
                    'maxRate': '123',
                    'niceToHaveRequirements': [
                        {
                            'criteria': 'Code review',
                            'weighting': '0'
                        }
                    ],
                    'numberOfSuppliers': '3',
                    'openTo': 'selected',
                    'organisation': 'Digital Transformation Agency',
                    'preferredFormatForRates': 'dailyRate',
                    'securityClearance': 'noneRequired',
                    'securityClearanceCurrent': '',
                    'securityClearanceObtain': '',
                    'securityClearanceOther': '',
                    'sellers': {
                        '1': {
                            'name': 'Seller 1'
                        }
                    },
                    'sellerCategory': '6',
                    'sellerSelector': 'oneSeller',
                    'startDate': pendulum.today(tz='Australia/Sydney').add(days=14).format('YYYY-MM-DD'),
                    'summary': 'My specialist summary',
                    'title': 'Specialist title'
                },
                framework=framework,
                lot=specialist_lot,
                users=users,
                published_at=now,
                withdrawn_at=None
            )

            specialist_brief.questions_closed_at = now.add(days=3)
            specialist_brief.closed_at = now.add(days=5)
            db.session.add(specialist_brief)

            rfx_brief = Brief(
                id=3,
                data={
                    'title': 'TEST',
                    'closedAt': pendulum.today(tz='Australia/Sydney').add(days=14).format('YYYY-MM-DD'),
                    'organisation': 'ABC',
                    'summary': 'TEST',
                    'workingArrangements': 'TEST',
                    'location': [
                        'New South Wales'
                    ],
                    'sellerCategory': '1',
                    'sellers': {
                        '1': {
                            'name': 'Seller 1'
                        }
                    },
                    'evaluationType': [
                        'Response template',
                        'Written proposal'
                    ],
                    'proposalType': [
                        'Breakdown of costs'
                    ],
                    'requirementsDocument': [
                        'TEST.pdf'
                    ],
                    'responseTemplate': [
                        'TEST2.pdf'
                    ],
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
                },
                framework=framework,
                lot=specialist_lot,
                users=users,
                published_at=now,
                withdrawn_at=None
            )

            rfx_brief.questions_closed_at = now.add(days=3)
            rfx_brief.closed_at = now.add(days=5)
            db.session.add(rfx_brief)

            yield db.session.query(Brief).all()

    def test_edit_title_updates_title(self, briefs):
        atm_brief = brief_service.get(1)
        new_title = 'New title'
        brief_edit_business.edit_title(atm_brief, new_title)
        assert atm_brief.data['title'] == new_title

    @pytest.mark.parametrize('new_title', ['ATM title', '', None, False])
    def test_edit_title_does_not_update_title(self, briefs, new_title):
        atm_brief = brief_service.get(1)
        original_title = atm_brief.data['title']
        brief_edit_business.edit_title(atm_brief, new_title)
        assert atm_brief.data['title'] == original_title

    def test_get_sellers_to_invite_returns_new_sellers(self, briefs):
        specialist_brief = brief_service.get(2)
        new_sellers = {
            '1': {
                'name': 'Seller 1'
            },
            '2': {
                'name': 'Seller 2'
            },
            '3': {
                'name': 'Seller 3'
            }
        }

        sellers_to_invite = brief_edit_business.get_sellers_to_invite(specialist_brief, new_sellers)
        seller_codes = sellers_to_invite.keys()

        assert len(seller_codes) == 2
        assert '1' not in seller_codes
        assert '2' in seller_codes
        assert '3' in seller_codes

    def test_get_sellers_to_invite_returns_empty_dictionary_when_no_new_sellers(self, briefs):
        specialist_brief = brief_service.get(2)
        new_sellers = {
            '1': {
                'name': 'Seller 1'
            }
        }

        sellers_to_invite = brief_edit_business.get_sellers_to_invite(specialist_brief, new_sellers)
        seller_codes = sellers_to_invite.keys()

        assert len(seller_codes) == 0
        assert '1' not in seller_codes

    def test_edit_sellers_updates_sellers(self, briefs):
        specialist_brief = brief_service.get(2)
        new_sellers = {
            '1': {
                'name': 'Seller 1'
            },
            '2': {
                'name': 'Seller 2'
            }
        }

        brief_edit_business.edit_sellers(specialist_brief, new_sellers)
        assert specialist_brief.data['sellers'] == new_sellers

    def test_edit_seller_selector_updates_seller_selector(self, briefs):
        specialist_brief = brief_service.get(2)
        new_sellers = {
            '2': {
                'name': 'Seller 2'
            }
        }

        assert specialist_brief.data['sellerSelector'] == 'oneSeller'
        brief_edit_business.edit_seller_selector(specialist_brief, new_sellers)
        assert specialist_brief.data['sellerSelector'] == 'someSellers'

    def test_edit_sellers_does_not_update_sellers_for_atm_opportunity(self, briefs):
        atm_brief = brief_service.get(1)
        new_sellers = {
            '1': {
                'name': 'Seller 1'
            }
        }

        brief_edit_business.edit_sellers(atm_brief, new_sellers)
        assert 'sellers' not in atm_brief.data

    def test_edit_sellers_does_not_update_sellers(self, briefs):
        specialist_brief = brief_service.get(2)
        original_sellers = specialist_brief.data['sellers']
        new_sellers = {
            '1': {
                'name': 'Seller 1'
            }
        }

        brief_edit_business.edit_sellers(specialist_brief, new_sellers)
        assert specialist_brief.data['sellers'] == original_sellers

    def test_edit_sellers_does_not_update_seller_selector(self, briefs):
        specialist_brief = brief_service.get(2)
        new_sellers = {
            '1': {
                'name': 'Seller 1'
            }
        }

        assert specialist_brief.data['sellerSelector'] == 'oneSeller'
        brief_edit_business.edit_sellers(specialist_brief, new_sellers)
        assert specialist_brief.data['sellerSelector'] == 'oneSeller'

    def test_edit_summary_updates_summary(self, briefs):
        atm_brief = brief_service.get(1)
        new_summary = 'New summary'
        brief_edit_business.edit_summary(atm_brief, new_summary)
        assert atm_brief.data['summary'] == new_summary

    @pytest.mark.parametrize('new_summary', ['My ATM summary', '', None, False])
    def test_edit_summary_does_not_update_summary(self, briefs, new_summary):
        atm_brief = brief_service.get(1)
        original_summary = atm_brief.data['summary']
        brief_edit_business.edit_summary(atm_brief, new_summary)
        assert atm_brief.data['summary'] == original_summary

    def test_edit_closing_date_updates_closing_date(self, briefs):
        atm_brief = brief_service.get(1)
        timezone = 'Australia/Sydney'
        new_closing_date = pendulum.now(timezone).add(days=7)

        brief_edit_business.edit_closing_date(atm_brief, new_closing_date.to_date_string())

        local_closing_date = atm_brief.closed_at.in_timezone(timezone)
        assert local_closing_date.year == new_closing_date.year
        assert local_closing_date.month == new_closing_date.month
        assert local_closing_date.day == new_closing_date.day

    def test_edit_closing_date_updates_closing_time_to_6pm(self, briefs):
        atm_brief = brief_service.get(1)
        timezone = 'Australia/Sydney'
        new_closing_date = pendulum.now(timezone).add(days=7)

        brief_edit_business.edit_closing_date(atm_brief, new_closing_date.to_date_string())

        local_closing_date = atm_brief.closed_at.in_timezone(timezone)
        assert local_closing_date.hour == 18

    def test_edit_closing_date_updates_questions_closed_at(self, briefs):
        atm_brief = brief_service.get(1)
        new_closing_date = pendulum.now('Australia/Sydney').add(days=7)
        original_questions_closed_at = atm_brief.questions_closed_at

        brief_edit_business.edit_closing_date(atm_brief, new_closing_date.to_date_string())
        assert atm_brief.questions_closed_at > original_questions_closed_at

    def test_title_was_edited_returns_true_with_different_titles(self):
        edited = brief_edit_business.title_was_edited('Title', 'Old title')
        assert edited is True

    def test_title_was_edited_returns_false_with_same_titles(self):
        edited = brief_edit_business.title_was_edited('Title', 'Title')
        assert edited is False

    def test_sellers_were_edited_returns_true_with_different_sellers(self):
        old_sellers = {
            '1': {
                'name': 'Seller 1'
            }
        }

        sellers = {
            '1': {
                'name': 'Seller 1'
            },
            '2': {
                'name': 'Seller 2'
            }
        }

        edited = brief_edit_business.sellers_were_edited(sellers, old_sellers)
        assert edited is True

    def test_sellers_were_edited_returns_false_with_same_sellers(self):
        sellers = {
            '1': {
                'name': 'Seller 1'
            }
        }

        edited = brief_edit_business.sellers_were_edited(sellers, sellers)
        assert edited is False

    def test_closing_date_was_edited_returns_true_with_different_closing_date(self):
        closing_date = pendulum.now('utc')
        previous_closing_date = pendulum.now('utc').add(days=2)
        edited = brief_edit_business.closing_date_was_edited(closing_date, previous_closing_date)
        assert edited is True

    def test_closing_date_was_edited_returns_false_with_same_closing_date(self):
        closing_date = pendulum.now('utc')
        edited = brief_edit_business.closing_date_was_edited(closing_date, closing_date)
        assert edited is False

    def test_closing_date_was_edited_returns_true_with_different_closing_date_as_string(self):
        closing_date = pendulum.now('utc').to_iso8601_string()
        previous_closing_date = pendulum.now('utc').add(days=2).to_iso8601_string()
        edited = brief_edit_business.closing_date_was_edited(closing_date, previous_closing_date)
        assert edited is True

    def test_closing_date_was_edited_returns_false_with_same_closing_date_as_string(self):
        closing_date = pendulum.now('utc').to_iso8601_string()
        edited = brief_edit_business.closing_date_was_edited(closing_date, closing_date)
        assert edited is False

    @mock.patch('app.api.business.brief.brief_edit_business.agency_service')
    def test_only_sellers_were_edited(self, agency_service, briefs, users):
        specialist_brief = brief_service.get(2)
        user = user_service.get(2)
        agency_service.get_agency_name.return_value = 'DTA'

        edits = {
            'closingDate': '',
            'title': '',
            'sellers': {
                '1': {
                    'name': 'Seller 1'
                },
                '2': {
                    'name': 'Seller 2'
                }
            },
            'summary': ''
        }

        brief = brief_edit_business.edit_opportunity(user.id, specialist_brief.id, edits)
        only_sellers_edited = brief_edit_business.only_sellers_were_edited(specialist_brief.id)
        assert only_sellers_edited is True

    @mock.patch('app.api.business.brief.brief_edit_business.agency_service')
    def test_only_sellers_were_edited_is_false_when_title_edited(self, agency_service, briefs, users):
        specialist_brief = brief_service.get(2)
        user = user_service.get(2)
        agency_service.get_agency_name.return_value = 'DTA'

        edits = {
            'closingDate': '',
            'title': 'test',
            'sellers': {
                '1': {
                    'name': 'Seller 1'
                },
                '2': {
                    'name': 'Seller 2'
                }
            },
            'summary': ''
        }

        brief = brief_edit_business.edit_opportunity(user.id, specialist_brief.id, edits)
        only_sellers_edited = brief_edit_business.only_sellers_were_edited(specialist_brief.id)
        assert only_sellers_edited is False

    @mock.patch('app.api.business.brief.brief_edit_business.agency_service')
    def test_only_sellers_were_edited_is_false_when_closing_date_edited(self, agency_service, briefs, users):
        specialist_brief = brief_service.get(2)
        user = user_service.get(2)
        agency_service.get_agency_name.return_value = 'DTA'

        edits = {
            'closingDate': pendulum.now('Australia/Canberra').add(days=7).to_date_string(),
            'title': '',
            'sellers': {
                '1': {
                    'name': 'Seller 1'
                },
                '2': {
                    'name': 'Seller 2'
                }
            },
            'summary': ''
        }

        brief = brief_edit_business.edit_opportunity(user.id, specialist_brief.id, edits)
        only_sellers_edited = brief_edit_business.only_sellers_were_edited(specialist_brief.id)
        assert only_sellers_edited is False

    @mock.patch('app.api.business.brief.brief_edit_business.agency_service')
    def test_only_sellers_were_edited_is_false_when_summary_edited(self, agency_service, briefs, users):
        specialist_brief = brief_service.get(2)
        user = user_service.get(2)
        agency_service.get_agency_name.return_value = 'DTA'

        edits = {
            'closingDate': pendulum.now('Australia/Canberra').add(days=7).to_date_string(),
            'title': '',
            'sellers': {
                '1': {
                    'name': 'Seller 1'
                },
                '2': {
                    'name': 'Seller 2'
                }
            },
            'summary': 'New summary'
        }

        brief = brief_edit_business.edit_opportunity(user.id, specialist_brief.id, edits)
        only_sellers_edited = brief_edit_business.only_sellers_were_edited(specialist_brief.id)
        assert only_sellers_edited is False

    @mock.patch('app.api.business.brief.brief_edit_business.agency_service')
    def test_edit_opportunity_creates_history_record(self, agency_service, briefs, users):
        specialist_brief = brief_service.get(2)
        user = user_service.get(2)
        agency_service.get_agency_name.return_value = 'DTA'

        edits = {
            'closingDate': '',
            'title': 'test',
            'sellers': {},
            'summary': ''
        }

        brief = brief_edit_business.edit_opportunity(user.id, specialist_brief.id, edits)
        history = brief_history_service.all()

        assert len(history) == 1
        assert history[0].brief_id == brief.id
        assert history[0].user_id == user.id

    @mock.patch('app.api.business.brief.brief_edit_business.agency_service')
    def test_edit_opportunity_creates_history_record_with_original_data(self, agency_service, briefs, users):
        specialist_brief = brief_service.get(2)
        original_closed_at = copy.deepcopy(specialist_brief.closed_at)
        original_specialist_data = copy.deepcopy(specialist_brief.data)
        user = user_service.get(2)
        agency_service.get_agency_name.return_value = 'DTA'

        edits = {
            'closingDate': '',
            'title': 'test',
            'sellers': {},
            'summary': ''
        }

        brief = brief_edit_business.edit_opportunity(user.id, specialist_brief.id, edits)
        history = brief_history_service.all()

        assert pendulum.parse(history[0].data['closed_at'], tz='utc') == original_closed_at
        assert history[0].data['sellers'] == original_specialist_data['sellers']
        assert history[0].data['sellerSelector'] == original_specialist_data['sellerSelector']
        assert history[0].data['title'] == original_specialist_data['title']

    @mock.patch('app.api.business.brief.brief_edit_business.agency_service')
    def test_edit_opportunity_creates_audit_event(self, agency_service, briefs, users):
        specialist_brief = brief_service.get(2)
        user = user_service.get(2)
        agency_service.get_agency_name.return_value = 'DTA'

        edits = {
            'closingDate': '',
            'title': 'test',
            'sellers': {},
            'summary': ''
        }

        brief = brief_edit_business.edit_opportunity(user.id, specialist_brief.id, edits)
        audit_event = audit_service.find(
            object_id=specialist_brief.id,
            object_type='Brief',
            type=audit_types.opportunity_edited.value
        ).one_or_none()

        assert audit_event is not None

    def test_edit_attachments_updates_attachments(self, briefs):
        specialist_brief = brief_service.get(2)
        attachments = ['1.pdf', '2.pdf']

        brief_edit_business.edit_attachments(specialist_brief, attachments)
        assert specialist_brief.data['attachments'] == attachments

    def test_edit_response_template_updates_response_template(self, briefs):
        rfx_brief = brief_service.get(3)
        response_template = ['new.pdf']

        brief_edit_business.edit_response_template(rfx_brief, response_template)
        assert rfx_brief.data['responseTemplate'] == response_template

    def test_edit_empty_response_template_does_not_update_response_template(self, briefs):
        rfx_brief = brief_service.get(3)
        original_template = rfx_brief.data['responseTemplate']
        response_template = []

        brief_edit_business.edit_response_template(rfx_brief, response_template)
        assert rfx_brief.data['responseTemplate'] == original_template

    def test_edit_requirements_document_updates_requirements_document(self, briefs):
        rfx_brief = brief_service.get(3)
        requirements_document = ['new.pdf']

        brief_edit_business.edit_requirements_document(rfx_brief, requirements_document)
        assert rfx_brief.data['requirementsDocument'] == requirements_document

    def test_edit_empty_requirements_document_does_not_update_requirements_document(self, briefs):
        rfx_brief = brief_service.get(3)
        original_template = rfx_brief.data['requirementsDocument']
        requirements_document = []

        brief_edit_business.edit_requirements_document(rfx_brief, requirements_document)
        assert rfx_brief.data['requirementsDocument'] == original_template

    @mock.patch('app.api.business.brief.brief_edit_business.agency_service')
    def test_edit_documents_only_apply_edits_with_edited_flag_set(self, agency_service, briefs, users):
        atm_brief = brief_service.get(1)
        user = user_service.get(2)
        agency_service.get_agency_name.return_value = 'DTA'
        original_attachments = atm_brief.data['attachments']

        edits = {
            'closingDate': '',
            'title': 'test',
            'summary': 'test',
            'sellers': {},
            'attachments': [],
            'documentsEdited': False
        }

        brief = brief_edit_business.edit_opportunity(user.id, atm_brief.id, edits)
        assert len(original_attachments) > 0
        assert brief.data['attachments'] == original_attachments

        edits = {
            'closingDate': '',
            'title': 'test',
            'summary': 'test',
            'sellers': {},
            'attachments': ['ABC.PDF'],
            'documentsEdited': True
        }

        brief = brief_edit_business.edit_opportunity(user.id, atm_brief.id, edits)
        assert brief.data['attachments'] == ['ABC.PDF']
