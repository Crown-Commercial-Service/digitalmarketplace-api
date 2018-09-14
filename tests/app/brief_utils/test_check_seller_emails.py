from mock import patch

from app.api.services import suppliers, users
from app.brief_utils import check_seller_emails
from app.models import Supplier, User


def test_check_one_seller_email_not_found():
    brief_data = {
        'sellerSelector': 'oneSeller',
        'sellerEmail': 'nofound@a.com'
    }
    errs = {}
    with \
        patch.object(users, 'get_sellers_by_email', return_value=[]) as get_sellers_by_email, \
        patch.object(suppliers,
                     'get_suppliers_by_contact_email',
                     return_value=[]) as get_suppliers_by_contact_email:
            error = check_seller_emails(brief_data, errs)
            assert error is not None
            assert error['sellerEmail'] == 'email_not_found~nofound@a.com'


def test_check_one_seller_email_found():
    brief_data = {
        'sellerSelector': 'oneSeller',
        'sellerEmail': 'found@a.com'
    }
    errs = {}
    with patch.object(users, 'get_sellers_by_email', return_value=[User()]) as get_sellers_by_email:
        error = check_seller_emails(brief_data, errs)
        assert error is None


def test_check_one_seller_email_unanswered():
    test_cases = [{
        'sellerSelector': 'oneSeller',
        'sellerEmail': ''
    }, {
        'sellerSelector': 'oneSeller',
        'sellerEmail': None
    }, {
        'sellerSelector': 'oneSeller'
    }]
    errs = {}
    with patch.object(users, 'get_sellers_by_email', return_value=[]) as get_sellers_by_email:
        for test_case in test_cases:
            error = check_seller_emails(test_case, errs)
            assert error is not None
            assert error['sellerEmail'] == 'answer_required'


def test_check_some_seller_email_unanswered():
    test_cases = [{
        'sellerSelector': 'someSellers',
        'sellerEmailList': []
    }, {
        'sellerSelector': 'someSellers'
    }]
    errs = {}
    with patch.object(users, 'get_sellers_by_email', return_value=[]) as get_sellers_by_email:
        for test_case in test_cases:
            error = check_seller_emails(test_case, errs)
            assert error is not None
            assert error['sellerEmailList'] == 'answer_required'


def test_check_some_seller_email_answered():
    test_cases = [{
        'sellerSelector': 'someSellers',
        'sellerEmailList': [
            'test@c.com'
        ]
    }]
    errs = {}
    with patch.object(users, 'get_sellers_by_email', return_value=[User()]) as get_sellers_by_email:
        for test_case in test_cases:
            error = check_seller_emails(test_case, errs)
            assert error is None


def test_check_some_seller_email_found():
    brief_data = {
        'sellerSelector': 'someSellers',
        'sellerEmailList': [
            'found@a.com'
        ]
    }
    errs = {}
    with patch.object(users, 'get_sellers_by_email', return_value=[User()]) as get_sellers_by_email:
        error = check_seller_emails(brief_data, errs)
        assert error is None


def test_check_some_seller_email_not_found():
    brief_data = {
        'sellerSelector': 'someSellers',
        'sellerEmailList': [
            'notfound@a.com'
        ]
    }
    errs = {}
    with \
        patch.object(users, 'get_sellers_by_email', return_value=[]) as get_sellers_by_email, \
        patch.object(suppliers,
                     'get_suppliers_by_contact_email',
                     return_value=[]) as get_suppliers_by_contact_email:
            error = check_seller_emails(brief_data, errs)
            assert error is not None
            assert error['sellerEmailList'] == 'email_not_found~notfound@a.com'


def test_check_seller_email_return_none_when_error():
    brief_data = {
        'sellerSelector': 'someSellers',
        'sellerEmailList': [
            'notfound@a.com'
        ]
    }
    errs = {
        'sellerEmailList': 'invalid_format'
    }
    with patch.object(users, 'get_sellers_by_email', return_value=[]) as get_sellers_by_email:
        error = check_seller_emails(brief_data, errs)
        assert error is None


def test_contact_email_found_for_one_seller():
    brief_data = {
        'sellerEmail': 'found@a.com',
        'sellerSelector': 'oneSeller'
    }

    errs = {}
    with \
        patch.object(users, 'get_sellers_by_email', return_value=[]) as get_sellers_by_email, \
        patch.object(suppliers,
                     'get_suppliers_by_contact_email',
                     return_value=[Supplier(data={
                         'contact_email': 'found@a.com'
                     })]) as get_suppliers_by_contact_email:
            error = check_seller_emails(brief_data, errs)
            assert error is None


def test_contact_email_found_for_some_sellers():
    brief_data = {
        'sellerEmailList': ['found@a.com'],
        'sellerSelector': 'someSellers'
    }

    errs = {}
    with \
        patch.object(users, 'get_sellers_by_email', return_value=[]) as get_sellers_by_email, \
        patch.object(suppliers,
                     'get_suppliers_by_contact_email',
                     return_value=[Supplier(data={
                         'contact_email': 'found@a.com'
                     })]) as get_suppliers_by_contact_email:
            error = check_seller_emails(brief_data, errs)
            assert error is None
