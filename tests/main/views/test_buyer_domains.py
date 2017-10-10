import json

from tests.bases import BaseApplicationTest
from app.models import BuyerEmailDomain, AuditEvent


class TestCreateBuyerEmailDomain(BaseApplicationTest):
    def test_create_buyer_email_domain_with_no_data(self):
        res = self.client.post(
            '/buyer-email-domain',
            content_type='application/json'
        )

        assert res.status_code == 400

    def test_create_buyer_email_domain(self):
        res = self.client.post(
            '/buyer-email-domain',
            data=json.dumps({
                'domainName': "example.com",
                'updated_by': 'example'
            }),
            content_type='application/json')
        data = json.loads(res.get_data(as_text=True))

        assert res.status_code == 201
        assert data['buyer_email_domains']['domainName'] == 'example.com'

    def test_create_buyer_email_domain_fails_if_required_field_is_not_provided(self):
        res = self.client.post(
            '/buyer-email-domain',
            data=json.dumps({
                'updated_by': 'example'
            }),
            content_type='application/json')
        data = json.loads(res.get_data(as_text=True))

        assert res.status_code == 400
        assert data['error'] == "Invalid JSON must have 'domainName' keys"

    def test_create_buyer_email_domain_creates_audit_event(self):
        res = self.client.post(
            '/buyer-email-domain',
            data=json.dumps({
                'domainName': "example.com",
                'updated_by': 'example user'
            }),
            content_type='application/json')

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

    def test_create_buyer_email_domain_fails_if_domain_already_exists(self):
        pass
