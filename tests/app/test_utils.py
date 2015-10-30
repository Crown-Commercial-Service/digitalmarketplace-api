from app.utils import (display_list,
                       strip_whitespace_from_data,
                       json_has_matching_id,
                       json_has_required_keys,
                       link)

from nose.tools import assert_equal, raises
from werkzeug.exceptions import HTTPException

from .helpers import BaseApplicationTest


def test_link():
    assert_equal(link("self", "/"), {"self": "/"})


class TestJSONHasRequiredKeys(BaseApplicationTest):
    @raises(HTTPException)
    def test_json_has_required_keys(self):
        with self.app.app_context():
            sample_json = {"name": "Linus",
                           "favourite_kitten": "all of them"}
            keys = ["name", "favourite_kitten", "gender"]
            json_has_required_keys(sample_json, keys)


class TestJSONHasMatchingId(BaseApplicationTest):
    @raises(HTTPException)
    def test_json_has_matching_id(self):
        self.data = {"id": 123456}
        with self.app.app_context():
            json_has_matching_id(self.data, 78910)


def test_display_list_two_items():
    test_list = ["eggs", "spam"]
    expected = "eggs and spam"
    assert_equal(display_list(test_list), expected)


def test_display_list_three_items():
    test_list = ["eggs", "spam", "ham"]
    expected = "eggs, spam, and ham"
    assert_equal(display_list(test_list), expected)


def test_strip_whitespace_from_data():
    struct = {"eggs": "  ham "}
    assert_equal(strip_whitespace_from_data(struct)['eggs'], "ham")
    struct_with_list = {"eggs": ["  spam  ", "  ham  ", "  eggs "]}
    after_strip = strip_whitespace_from_data(struct_with_list)
    for item in after_strip['eggs']:
        # check to see if there is any whitespace left.
        # if not, find will return -1
        assert_equal(item.find(" "), -1)
