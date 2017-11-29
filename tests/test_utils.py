import pytest
import mock

from flask import current_app
from nose.tools import assert_equal
from werkzeug.exceptions import BadRequest, HTTPException

from tests.bases import BaseApplicationTest

from app.utils import (display_list,
                       strip_whitespace_from_data,
                       json_has_keys,
                       json_has_matching_id,
                       json_has_required_keys,
                       link,
                       purge_nulls_from_data,
                       keyfilter_json,
                       index_object)

from dmapiclient import HTTPError


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


class TestKeyFilterJSON(object):
    def test_null(self):
        assert keyfilter_json(None, lambda k: True) is None
        assert keyfilter_json(None, lambda k: False) is None

    def test_recursion(self):
        assert keyfilter_json({
            'somelist': [
                {
                    'something': 'yes',
                    'otherthing': 'no'
                },
                {
                    'something': 'maybe',
                    'otherthing': 'definitely'
                }
            ],
            'something': 'woo'
        }, lambda k: k != 'something') == {
            'somelist': [
                {
                    'otherthing': 'no'
                },
                {
                    'otherthing': 'definitely'
                }
            ],
        }


@mock.patch('app.utils.search_api_client', autospec=True)
class TestIndexObject(BaseApplicationTest):
    def test_calls_the_search_api_index_method_correctly(self, search_api_client):
        with self.app.app_context():
            for framework, doc_type_to_index_mapping in current_app.config['DM_FRAMEWORK_TO_ES_INDEX'].items():
                for doc_type, index_name in doc_type_to_index_mapping.items():

                    index_object(framework, doc_type, 123, {'serialized': 'object'})

                    search_api_client.index.assert_called_once_with(
                        index_name=index_name,
                        object_id=123,
                        serialized_object={'serialized': 'object'},
                        doc_type=doc_type,
                    )
                    search_api_client.reset_mock()

    @mock.patch('app.utils.current_app')
    def test_logs_an_error_message_if_no_mapping_found(self, current_app, search_api_client):
        current_app.config = {
            'DM_FRAMEWORK_TO_ES_INDEX': {
                'not-a-framework': {
                    'services': 'g-cloud-9'
                }
            }
        }

        index_object('g-cloud-9', 'services', 123, {'serialized': 'object'})

        current_app.logger.error.assert_called_once_with(
            "Failed to find index name for framework 'g-cloud-9' with object type 'services'"
        )

    @mock.patch('app.utils.current_app')
    def test_logs_a_warning_if_HTTPError_from_search_api(self, current_app, search_api_client):
        search_api_client.index.side_effect = HTTPError()
        current_app.config = {
            'DM_FRAMEWORK_TO_ES_INDEX': {
                'g-cloud-9': {
                    'services': 'g-cloud-9'
                }
            }
        }

        index_object('g-cloud-9', 'services', 123, {'serialized': 'object'})

        current_app.logger.warning.assert_called_once_with(
            'Failed to add services object with id 123 to g-cloud-9 index: Request failed'
        )


def test_display_list_two_items():
    test_list = ["eggs", "spam"]
    expected = "eggs and spam"
    assert display_list(test_list) == expected


def test_display_list_three_items():
    test_list = ["eggs", "spam", "ham"]
    expected = "eggs, spam, and ham"
    assert display_list(test_list) == expected


def test_strip_whitespace_from_data_with_string_data():
    struct = {"eggs": "  ham "}
    assert strip_whitespace_from_data(struct)['eggs'] == "ham"


def test_strip_whitespace_from_data_with_list_data():
    struct_with_list = {"eggs": ["  spam  ", "  ham  ", "  eggs "]}
    after_strip = strip_whitespace_from_data(struct_with_list)
    for item in after_strip['eggs']:
        assert " " not in item


def test_strip_whitespace_from_data_with_dict_data():
    struct = {"eggs": [{'evidence': ' whitespace in here '}, {'evidence': 'no white space'}]}
    assert strip_whitespace_from_data(struct) == {
        "eggs": [{'evidence': 'whitespace in here'}, {'evidence': 'no white space'}]
    }


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


def test_json_has_keys():
    def check(data, data_required_keys, data_optional_keys, result):
        if result:
            assert json_has_keys(data, data_required_keys, data_optional_keys) is None
        else:
            with pytest.raises(BadRequest):
                json_has_keys(data, data_required_keys, data_optional_keys)

    for data, data_required_keys, data_optional_keys, result in [
        ({}, [], [], True),
        ({}, None, None, True),
        ({'key1': 'value1'}, ['key1'], None, True),
        ({'key1': 'value1'}, [], ['key1'], True),
        ({}, [], ['key1'], True),
        ({}, ['key1'], [], False),
        ({'key1': 'value1'}, [], [], False),
        ({'key1': 'value1'}, [], ['key2'], False),
    ]:
        check(data, data_required_keys, data_optional_keys, result)
