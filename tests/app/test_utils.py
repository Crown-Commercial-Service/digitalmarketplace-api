import pytest

from nose.tools import assert_equal
from werkzeug.exceptions import HTTPException

from .helpers import BaseApplicationTest

from app.utils import (display_list,
                       strip_whitespace_from_data,
                       json_has_matching_id,
                       json_has_required_keys,
                       link,
                       purge_nulls_from_data)


def test_link():
    assert link("self", "/") == {"self": "/"}


class TestJSONHasRequiredKeys(BaseApplicationTest):
    def test_json_has_required_keys(self):
        with self.app.app_context():
            sample_json = {"name": "Linus",
                           "favourite_kitten": "all of them"}
            keys = ["name", "favourite_kitten", "gender"]
            with pytest.raises(HTTPException):
                json_has_required_keys(sample_json, keys)


class TestJSONHasMatchingId(BaseApplicationTest):
    def test_json_has_matching_id(self):
        self.data = {"id": 123456}
        with self.app.app_context():
            with pytest.raises(HTTPException):
                json_has_matching_id(self.data, 78910)


def test_display_list_two_items():
    test_list = ["eggs", "spam"]
    expected = "eggs and spam"
    assert display_list(test_list) == expected


def test_display_list_three_items():
    test_list = ["eggs", "spam", "ham"]
    expected = "eggs, spam, and ham"
    assert display_list(test_list) == expected


def test_strip_whitespace_from_data():
    struct = {"eggs": "  ham "}
    assert strip_whitespace_from_data(struct)['eggs'] == "ham"
    struct_with_list = {"eggs": ["  spam  ", "  ham  ", "  eggs "]}
    after_strip = strip_whitespace_from_data(struct_with_list)
    for item in after_strip['eggs']:
        assert " " not in item


def test_purge_nulls():
    service_with_nulls = {
        'serviceName': 'Service with nulls',
        'empty': None,
        'serviceSummary': None,
        'price': 'Not a lot'
    }
    same_service_without_nulls = {
        'serviceName': 'Service with nulls',
        'price': 'Not a lot'
    }
    assert_equal(purge_nulls_from_data(service_with_nulls), same_service_without_nulls)
