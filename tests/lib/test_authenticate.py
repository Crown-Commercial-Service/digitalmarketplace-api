from nose.tools import eq_

from app.authentication import get_token_from_headers


def test_get_token_from_headers():
    yield check_token, {'Authorization': 'Bearer foo-bar'}, 'foo-bar'
    yield check_token, {'Authorization': 'Bearer bar-foo'}, 'bar-foo'
    yield check_token, {'Authorization': 'Bearer '}, ''
    yield (check_token, {'Authorisation': 'Bearer foo-bar'}, None,
           "Authorization header misspelt")
    yield (check_token, {'Authorization': 'Borrower foo-bar'}, None,
           "Authorization header prefix invalid")


def check_token(headers, expected_token, message=None):
    eq_(get_token_from_headers(headers), expected_token, message)
