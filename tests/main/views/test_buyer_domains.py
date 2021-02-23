import json
import mock
import pytest

from tests.bases import BaseApplicationTest
from app import db
from app.models import BuyerEmailDomain, AuditEvent


class TestCreateBuyerEmailDomain(BaseApplicationTest):
    def test_create_buyer_email_domain_with_no_data(self):
        res = self.client.post(
            '/buyer-email-domains',
            content_type='application/json'
        )

        assert res.status_code == 400

    @pytest.mark.parametrize('new_domain', ["fine.org", "also-fine.org", "also.fine.org", "f.org"])
    @pytest.mark.parametrize('existing_domain', ["ine.org", "o-fine.org"])
    def test_create_buyer_email_domain(self, existing_domain, new_domain):
        # Create a domain that shouldn't result in 'already been approved'
        db.session.add(BuyerEmailDomain(domain_name=existing_domain))
        db.session.commit()

        res = self.client.post(
            '/buyer-email-domains',
            data=json.dumps({
                'buyerEmailDomains': {'domainName': new_domain},
                'updated_by': 'example'
            }),
            content_type='application/json')
        data = json.loads(res.get_data(as_text=True))

        assert res.status_code == 201
        assert data['buyerEmailDomains']['domainName'] == new_domain

    @pytest.mark.parametrize(
        'existing_domain', ['approved.gov.uk', 'already.approved.gov.uk', 'definitely-approved.gov.uk']
    )
    def test_higher_level_domain_can_be_created_if_more_specific_domain_already_exists(self, existing_domain):
        db.session.add(BuyerEmailDomain(domain_name=existing_domain))
        db.session.commit()

        res = self.client.post(
            '/buyer-email-domains',
            data=json.dumps({
                'buyerEmailDomains': {'domainName': 'gov.uk'},
                'updated_by': 'example'
            }),
            content_type='application/json')
        data = json.loads(res.get_data(as_text=True))

        assert res.status_code == 201
        assert data['buyerEmailDomains']['domainName'] == "gov.uk"

    def test_create_buyer_email_domain_forces_to_lower_case(self):
        res = self.client.post(
            '/buyer-email-domains',
            data=json.dumps({
                'buyerEmailDomains': {'domainName': 'EXAMPLE.org'},
                'updated_by': 'example'
            }),
            content_type='application/json')
        data = json.loads(res.get_data(as_text=True))

        assert res.status_code == 201
        assert data['buyerEmailDomains']['domainName'] == "example.org"

    def test_create_buyer_email_domain_fails_if_required_field_is_not_provided(self):
        res = self.client.post(
            '/buyer-email-domains',
            data=json.dumps({
                'updated_by': 'example'
            }),
            content_type='application/json')
        data = json.loads(res.get_data(as_text=True))

        assert res.status_code == 400
        assert data['error'] == "Invalid JSON must have 'buyerEmailDomains' keys"

    def test_create_buyer_email_domain_creates_audit_event(self):
        self.client.post(
            '/buyer-email-domains',
            data=json.dumps({
                'buyerEmailDomains': {'domainName': "example.com"},
                'updated_by': 'example user'
            }),
            content_type='application/json'
        )

        buyer_email_domain = BuyerEmailDomain.query.filter(
            BuyerEmailDomain.domain_name == "example.com"
        ).first()

        audit = AuditEvent.query.filter(
            AuditEvent.object == buyer_email_domain
        ).first()

        assert audit.type == "create_buyer_email_domain"
        assert audit.user == "example user"
        assert audit.data == {
            'buyerEmailDomainId': buyer_email_domain.id,
            'buyerEmailDomainJson': {'domainName': 'example.com'}
        }

    @pytest.mark.parametrize(
        'new_domain',
        [
            'no-dots',
            'at@symbol.org',
            'contains space.org',
            'bad!char.org',
            'ampers&nd.org',
            'tld-too-short.x',
            '.tldonly',
            '.dots.at.start',
            'http://contains.colon'
            'contains.forward/slash',
            'contains.rogue?query=param'
        ]
    )
    def test_create_buyer_email_domain_fails_if_domain_invalid(self, new_domain):
        res = self.client.post(
            '/buyer-email-domains',
            data=json.dumps({
                'buyerEmailDomains': {'domainName': new_domain},
                'updated_by': 'example'
            }),
            content_type='application/json')
        data = json.loads(res.get_data())["error"]

        assert res.status_code == 400
        assert "JSON was not a valid format" in data

    @pytest.mark.parametrize(
        'new_domain', ['gov.uk', 'approved.gov.uk', 'already.approved.gov.uk', 'definitely-approved.gov.uk']
    )
    def test_create_buyer_email_domain_fails_if_higher_level_domain_already_approved(self, new_domain):
        db.session.add(BuyerEmailDomain(domain_name='gov.uk'))
        db.session.commit()

        res = self.client.post(
            '/buyer-email-domains',
            data=json.dumps({
                'buyerEmailDomains': {'domainName': new_domain},
                'updated_by': 'example'
            }),
            content_type='application/json')
        data = json.loads(res.get_data(as_text=True))

        assert res.status_code == 409
        assert data['error'] == "Domain name {} has already been approved".format(new_domain)


class TestDeleteBuyerEmailDomains(BaseApplicationTest):
    def setup(self):
        super(TestDeleteBuyerEmailDomains, self).setup()
        # Remove any default fixtures
        BuyerEmailDomain.query.delete()
        db.session.commit()

    def test_delete_buyer_email_domain_with_no_data(self):
        res = self.client.delete(
            '/buyer-email-domains',
            content_type='application/json'
        )

        assert res.status_code == 400

    def test_delete_buyer_email_domain_with_missing_domain(self):
        res = self.client.delete(
            '/buyer-email-domains',
            data=json.dumps({
                'buyerEmailDomains': {'domainName': 'gov.uk'},
                'updated_by': 'example'
            }),
            content_type='application/json'
        )

        assert res.status_code == 404

    def test_delete_buyer_email_domain_removes_domain(self):
        domain_name = "ac.uk"
        db.session.add(BuyerEmailDomain(domain_name=domain_name))
        db.session.commit()

        res = self.client.delete(
            '/buyer-email-domains',
            data=json.dumps({
                'buyerEmailDomains': {'domainName': domain_name},
                'updated_by': 'example'
            }),
            content_type='application/json'
        )

        assert res.status_code == 200
        assert BuyerEmailDomain.query.filter(
            BuyerEmailDomain.domain_name == domain_name
        ).first() is None


class TestListBuyerEmailDomains(BaseApplicationTest):
    def setup(self):
        super(TestListBuyerEmailDomains, self).setup()
        # Remove any default fixtures
        BuyerEmailDomain.query.delete()
        db.session.commit()

    def test_list_buyer_email_domain_200s_with_empty_list_when_no_domains(self):
        res = self.client.get('/buyer-email-domains')

        data = json.loads(res.get_data(as_text=True))

        assert res.status_code == 200
        assert data['buyerEmailDomains'] == []

    def test_list_buyer_email_domain_lists_serialized_domains_in_alphabetical_order(self):
        for existing_domain in ['abc.gov', 'bcd.gov', 'aaa-bcd.gov']:
            db.session.add(BuyerEmailDomain(domain_name=existing_domain))
            db.session.commit()

        res = self.client.get('/buyer-email-domains')

        data = json.loads(res.get_data(as_text=True))

        assert res.status_code == 200
        assert data['buyerEmailDomains'] == [
            {'domainName': 'aaa-bcd.gov', 'id': mock.ANY},
            {'domainName': 'abc.gov', 'id': mock.ANY},
            {'domainName': 'bcd.gov', 'id': mock.ANY},
        ]

    def test_list_buyer_email_domain_paginates(self):
        for existing_domain in ['{}.gov'.format(i) for i in range(101)]:
            db.session.add(BuyerEmailDomain(domain_name=existing_domain))
            db.session.commit()

        page1 = self.client.get('/buyer-email-domains')
        page2 = self.client.get('/buyer-email-domains?page=2')

        page_1_data = json.loads(page1.get_data(as_text=True))
        page_2_data = json.loads(page2.get_data(as_text=True))

        assert len(page_1_data['buyerEmailDomains']) == 100
        assert len(page_2_data['buyerEmailDomains']) == 1
