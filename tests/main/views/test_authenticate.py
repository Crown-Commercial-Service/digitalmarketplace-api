import pytest

from app.authentication import get_token_from_headers, get_allowed_tokens_from_config


def test_get_token_from_headers():
    yield check_token, {'Authorization': 'Bearer foo-bar'}, 'foo-bar'
    yield check_token, {'Authorization': 'Bearer bar-foo'}, 'bar-foo'
    yield check_token, {'Authorization': 'Bearer '}, ''
    yield (check_token, {'Authorisation': 'Bearer foo-bar'}, None,
           "Authorization header misspelt")
    yield (check_token, {'Authorization': 'Borrower foo-bar'}, None,
           "Authorization header prefix invalid")


def check_token(headers, expected_token, message=None):
    assert get_token_from_headers(headers) == expected_token, message


@pytest.mark.parametrize('config,tokens', [
    ({'DM_API_AUTH_TOKENS': 'foo:bar'}, ['foo', 'bar']),
    ({'DM_API_AUTH_TOKENS': 'bar'}, ['bar']),
    ({}, []),
])
def test_get_allowed_tokens_from_config(config, tokens):
    assert get_allowed_tokens_from_config(config) == tokens
