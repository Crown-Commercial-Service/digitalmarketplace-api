import json
import pytest

from tests.bases import BaseApplicationTest
from app import db
from app.models import BuyerEmailDomain, AuditEvent


class TestCreateBuyerEmailDomain(BaseApplicationTest):
    def test_create_buyer_email_domain_with_no_data(self):
        res = self.client.post(
            '/buyer-email-domain',
            content_type='application/json'
        )

        assert res.status_code == 400

    @pytest.mark.parametrize('new_domain', ["fine.org", "also-fine.org", "also.fine.org"])
    @pytest.mark.parametrize('existing_domain', ["ine.org", ".org", "o-fine.org"])
    def test_create_buyer_email_domain(self, existing_domain, new_domain):
        with self.app.app_context():
            # Create a domain that shouldn't result in 'already been approved'
            db.session.add(BuyerEmailDomain(domain_name=existing_domain))
            db.session.commit()

        res = self.client.post(
            '/buyer-email-domain',
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
        with self.app.app_context():
            db.session.add(BuyerEmailDomain(domain_name=existing_domain))
            db.session.commit()

        res = self.client.post(
            '/buyer-email-domain',
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
            '/buyer-email-domain',
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
            '/buyer-email-domain',
            data=json.dumps({
                'updated_by': 'example'
            }),
            content_type='application/json')
        data = json.loads(res.get_data(as_text=True))

        assert res.status_code == 400
        assert data['error'] == "Invalid JSON must have 'buyerEmailDomains' keys"

    def test_create_buyer_email_domain_creates_audit_event(self):
        self.client.post(
            '/buyer-email-domain',
            data=json.dumps({
                'buyerEmailDomains': {'domainName': "example.com"},
                'updated_by': 'example user'
            }),
            content_type='application/json'
        )

        with self.app.app_context():
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
        'new_domain', ['no-dots', 'at@symbol.org', 'contains space.org', 'bad!char.org', 'tld-too-short.x']
    )
    def test_create_buyer_email_domain_fails_if_domain_invalid(self, new_domain):
        res = self.client.post(
            '/buyer-email-domain',
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
        with self.app.app_context():
            db.session.add(BuyerEmailDomain(domain_name='gov.uk'))
            db.session.commit()

        res = self.client.post(
            '/buyer-email-domain',
            data=json.dumps({
                'buyerEmailDomains': {'domainName': new_domain},
                'updated_by': 'example'
            }),
            content_type='application/json')
        data = json.loads(res.get_data(as_text=True))

        assert res.status_code == 409
        assert data['error'] == "Domain name {} has already been approved".format(new_domain)