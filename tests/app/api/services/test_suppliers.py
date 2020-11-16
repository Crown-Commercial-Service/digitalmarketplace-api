from datetime import date, timedelta

import pytest
import pendulum

from app.api.services import suppliers
from app.models import Supplier, User, db, utcnow
from tests.app.helpers import BaseApplicationTest


class TestSuppliersService(BaseApplicationTest):
    def setup(self):
        super(TestSuppliersService, self).setup()

    @pytest.fixture()
    def supplier(self, app, request):
        params = request.param if hasattr(request, 'param') else {}
        expiry_date = date.today() + timedelta(days=10)
        expiry = '{}-{}-{}'.format(expiry_date.year, expiry_date.month, expiry_date.day)
        labourHire = (
            params['labourHire'] if 'labourHire' in params else
            {
                'vic': {
                    'expiry': expiry,
                    'licenceNumber': 'V123456'
                },
                'qld': {
                    'expiry': expiry,
                    'licenceNumber': 'Q123456'
                },
                'sa': {
                    'expiry': expiry,
                    'licenceNumber': 'S123456'
                },
                'act': {
                    'expiry': expiry,
                    'licenceNumber': 'A123456'
                }
            }
        )

        with app.app_context():
            db.session.add(Supplier(id=1, code=1, name='Seller 1', data={
                'contact_email': 'business.contact@digital.gov.au',
                'email': 'authorised.rep@digital.gov.au',
                'documents': {
                    'indemnity': {
                        'expiry': expiry
                    },
                    'liability': {
                        'expiry': expiry
                    },
                    'workers': {
                        'expiry': expiry
                    }
                },
                'labourHire': labourHire
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

    def test_get_expired_documents_returns_indemnity_liability_and_workers(self, supplier, users):
        expiry_date = date.today() + timedelta(days=10)
        expiry = '{}-{}-{}'.format(expiry_date.year, expiry_date.month, expiry_date.day)

        suppliers_with_expired_documents = suppliers.get_suppliers_with_expiring_documents(days=10)

        assert {
            'expiry': expiry,
            'type': 'indemnity'
        } in suppliers_with_expired_documents[0]['documents']

        assert {
            'expiry': expiry,
            'type': 'liability'
        } in suppliers_with_expired_documents[0]['documents']

        assert {
            'expiry': expiry,
            'type': 'workers'
        } in suppliers_with_expired_documents[0]['documents']

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

    def test_get_expired_licences_returns_empty_array_when_no_expired_licences(self, supplier, users):
        suppliers_with_expired_licences = suppliers.get_suppliers_with_expiring_labour_hire_licences(days=2)
        assert len(suppliers_with_expired_licences) == 0

    def test_get_expired_licences_returns_act_vic_and_qld(self, supplier, users):
        expiry_date = date.today() + timedelta(days=10)
        expiry = '{}-{}-{}'.format(expiry_date.year, expiry_date.month, expiry_date.day)

        suppliers_with_expired_licences = suppliers.get_suppliers_with_expiring_labour_hire_licences(days=10)
        assert len(suppliers_with_expired_licences[0]['labour_hire_licences']) == 3

    @pytest.mark.parametrize(
        'supplier', [
            {
                'labourHire': {
                    'vic': {
                        'expiry': pendulum.today(tz='Australia/Sydney').add(days=10).format('%Y-%m-%d'),
                        'licenceNumber': 'V123456'
                    }
                }
            }
        ], indirect=True
    )
    def test_get_expired_licences_returns_vic_only(self, supplier, users):
        expiry = pendulum.today(tz='Australia/Sydney').add(days=10).format('%Y-%m-%d')

        suppliers_with_expired_licences = suppliers.get_suppliers_with_expiring_labour_hire_licences(days=10)
        assert suppliers_with_expired_licences[0]['labour_hire_licences'] == [
            {
                'expiry': expiry,
                'state': 'vic',
                'licenceNumber': 'V123456'
            }
        ]

    @pytest.mark.parametrize(
        'supplier', [
            {
                'labourHire': {
                    'sa': {
                        'expiry': pendulum.today(tz='Australia/Sydney').add(days=10).format('%Y-%m-%d'),
                        'licenceNumber': 'S123456'
                    },
                    'vic': {
                        'expiry': pendulum.today(tz='Australia/Sydney').add(days=10).format('%Y-%m-%d'),
                        'licenceNumber': 'V123456'
                    },
                    'act': {
                        'expiry': pendulum.today(tz='Australia/Sydney').add(days=10).format('%Y-%m-%d'),
                        'licenceNumber': 'A123456'
                    }
                }
            }
        ], indirect=True
    )
    def test_ignore_sa_expired_licences_and_return_vic_and_act(self, supplier, users):
        expiry = pendulum.today(tz='Australia/Sydney').add(days=10).format('%Y-%m-%d')
        suppliers_with_expired_licences = suppliers.get_suppliers_with_expiring_labour_hire_licences(days=10)

        assert suppliers_with_expired_licences[0]['labour_hire_licences'] == [
            {
                'expiry': expiry,
                'state': 'vic',
                'licenceNumber': 'V123456'
            },
            {
                'expiry': expiry,
                'state': 'act',
                'licenceNumber': 'A123456'
            }
        ]

    def test_get_expired_licences_returns_all_supplier_email_addresses(self, supplier, users):
        expiry_date = date.today() + timedelta(days=10)
        expiry = '{}-{}-{}'.format(expiry_date.year, expiry_date.month, expiry_date.day)

        suppliers_with_expired_licences = suppliers.get_suppliers_with_expiring_labour_hire_licences(days=10)

        email_addresses = suppliers_with_expired_licences[0]['email_addresses']
        assert len(email_addresses) == 4
        assert 'authorised.rep@digital.gov.au' in email_addresses
        assert 'business.contact@digital.gov.au' in email_addresses
        assert 'user1@digital.gov.au' in email_addresses
        assert 'user2@digital.gov.au' in email_addresses

    def test_get_expired_licences_removes_duplicate_email_addresses(self, supplier, users):
        expiry_date = date.today() + timedelta(days=10)
        expiry = '{}-{}-{}'.format(expiry_date.year, expiry_date.month, expiry_date.day)

        supplier.data['contact_email'] = 'user1@digital.gov.au'
        supplier.data['email'] = 'user1@digital.gov.au'

        suppliers_with_expired_licences = suppliers.get_suppliers_with_expiring_labour_hire_licences(days=10)

        email_addresses = suppliers_with_expired_licences[0]['email_addresses']
        assert len(email_addresses) == 2
        assert 'user1@digital.gov.au' in email_addresses
        assert 'user2@digital.gov.au' in email_addresses
