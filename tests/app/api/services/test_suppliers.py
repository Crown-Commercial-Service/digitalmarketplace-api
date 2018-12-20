from datetime import date, timedelta

import pytest

from app.api.services import suppliers
from app.models import Supplier, User, db, utcnow
from tests.app.helpers import BaseApplicationTest


class TestSuppliersService(BaseApplicationTest):
    def setup(self):
        super(TestSuppliersService, self).setup()

    @pytest.fixture()
    def supplier(self, app):
        expiry_date = date.today() + timedelta(days=10)
        expiry = '{}-{}-{}'.format(expiry_date.year, expiry_date.month, expiry_date.day)

        with app.app_context():
            db.session.add(Supplier(id=1, code=1, name='Seller 1', data={
                'contact_email': 'business.contact@digital.gov.au',
                'email': 'authorised.rep@digital.gov.au',
                'documents': {
                    'liability': {
                        'expiry': expiry
                    },
                    'workers': {
                        'expiry': expiry
                    }
                }
            }))
            yield db.session.query(Supplier).first()

    @pytest.fixture()
    def users(self, app):
        with app.app_context():
            db.session.add(
                User(
                    id=1,
                    name='User 1',
                    password='password1',
                    email_address='user1@digital.gov.au',
                    active=True,
                    role='supplier',
                    supplier_code=1,
                    password_changed_at=utcnow()
                )
            )
            db.session.add(
                User(
                    id=2,
                    name='User 2',
                    password='password2',
                    email_address='user2@digital.gov.au',
                    active=True,
                    role='supplier',
                    supplier_code=1,
                    password_changed_at=utcnow()
                )
            )
            db.session.add(
                User(
                    id=3,
                    name='User 3',
                    password='password3',
                    email_address='user3@digital.gov.au',
                    active=False,
                    role='supplier',
                    supplier_code=1,
                    password_changed_at=utcnow()
                )
            )
            yield db.session.query(User).all()

    def test_get_expired_documents_returns_empty_array_when_no_expired_documents(self, supplier, users):
        suppliers_with_expired_documents = suppliers.get_suppliers_with_expiring_documents(days=2)
        assert len(suppliers_with_expired_documents) == 0

    def test_get_expired_documents_returns_both_liability_and_workers(self, supplier, users):
        expiry_date = date.today() + timedelta(days=10)
        expiry = '{}-{}-{}'.format(expiry_date.year, expiry_date.month, expiry_date.day)

        suppliers_with_expired_documents = suppliers.get_suppliers_with_expiring_documents(days=10)
        assert suppliers_with_expired_documents[0]['documents'] == [
            {
                'expiry': expiry,
                'type': 'liability'
            },
            {
                'expiry': expiry,
                'type': 'workers'
            }
        ]

    def test_get_expired_documents_returns_all_supplier_email_addresses(self, supplier, users):
        expiry_date = date.today() + timedelta(days=10)
        expiry = '{}-{}-{}'.format(expiry_date.year, expiry_date.month, expiry_date.day)

        suppliers_with_expired_documents = suppliers.get_suppliers_with_expiring_documents(days=10)

        email_addresses = suppliers_with_expired_documents[0]['email_addresses']
        assert len(email_addresses) == 4
        assert 'authorised.rep@digital.gov.au' in email_addresses
        assert 'business.contact@digital.gov.au' in email_addresses
        assert 'user1@digital.gov.au' in email_addresses
        assert 'user2@digital.gov.au' in email_addresses

    def test_get_expired_documents_removes_duplicate_email_addresses(self, supplier, users):
        expiry_date = date.today() + timedelta(days=10)
        expiry = '{}-{}-{}'.format(expiry_date.year, expiry_date.month, expiry_date.day)

        supplier.data['contact_email'] = 'user1@digital.gov.au'
        supplier.data['email'] = 'user1@digital.gov.au'

        suppliers_with_expired_documents = suppliers.get_suppliers_with_expiring_documents(days=10)

        email_addresses = suppliers_with_expired_documents[0]['email_addresses']
        assert len(email_addresses) == 2
        assert 'user1@digital.gov.au' in email_addresses
        assert 'user2@digital.gov.au' in email_addresses
