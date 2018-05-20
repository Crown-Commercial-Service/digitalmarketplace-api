import pytest

from app.authentication import get_token_from_headers, get_allowed_tokens_from_config


def test_get_token_from_headers():
    check_token({'Authorization': 'Bearer foo-bar'}, 'foo-bar')
    check_token({'Authorization': 'Bearer bar-foo'}, 'bar-foo')
    check_token({'Authorization': 'Bearer '}, '')
    check_token({'Authorisation': 'Bearer foo-bar'}, None, "Authorization header misspelt")
    check_token({'Authorization': 'Borrower foo-bar'}, None, "Authorization header prefix invalid")


def check_token(headers, expected_token, message=None):
    assert get_token_from_headers(headers) == expected_token, message


@pytest.mark.parametrize('config,module, tokens', [
    ({'DM_API_AUTH_TOKENS': 'foo:bar'}, 'main', ['foo', 'bar']),
    ({'DM_API_AUTH_TOKENS': 'bar'}, 'main', ['bar']),
    ({'DM_API_CALLBACK_AUTH_TOKENS': 'potato:carrot'}, 'callbacks', ['potato', 'carrot']),
    ({'DM_API_CALLBACK_AUTH_TOKENS': 'parsnip'}, 'callbacks', ['parsnip']),
    ({}, 'main', []),
])
def test_get_allowed_tokens_from_config(config, tokens, module):
    assert get_allowed_tokens_from_config(config, module=module) == tokens
