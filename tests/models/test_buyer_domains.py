from app import db
from app.models.buyer_domains import BuyerEmailDomain
from tests.bases import BaseApplicationTest


class TestBuyerEmailDomains(BaseApplicationTest):

    def test_create_new_buyer_email_domain(self):
        with self.app.app_context():

            buyer_domain = BuyerEmailDomain(domain_name="superkalifrajilisticexpialidocious.org.uk")
            db.session.add(buyer_domain)
            db.session.commit()

            assert buyer_domain.id is not None
            assert buyer_domain.domain_name == "superkalifrajilisticexpialidocious.org.uk"

    def test_buyer_email_domain_serialization(self):
        buyer_domain = BuyerEmailDomain(domain_name="superkalifrajilisticexpialidocious.org.uk")

        assert buyer_domain.serialize().keys() == {'id', 'domain_name'}
