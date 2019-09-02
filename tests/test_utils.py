import json
import mock
import pytest

from dmapiclient import HTTPError
from flask import current_app
from werkzeug.exceptions import BadRequest, HTTPException

from app.utils import (
    display_list,
    index_object,
    json_has_keys,
    json_has_matching_id,
    json_has_required_keys,
    keyfilter_json,
    link,
    list_result_response,
    paginated_result_response,
    purge_nulls_from_data,
    single_result_response,
    strip_whitespace_from_data,
)
from tests.bases import BaseApplicationTest


def test_link():
    assert link("self", "/") == {"self": "/"}


class TestJSONHasRequiredKeys(BaseApplicationTest):
    def test_json_has_required_keys(self):
        sample_json = {"name": "Linus",
                       "favourite_kitten": "all of them"}
        keys = ["name", "favourite_kitten", "gender"]
        with pytest.raises(HTTPException):
            json_has_required_keys(sample_json, keys)


class TestJSONHasMatchingId(BaseApplicationTest):
    def test_json_has_matching_id(self):
        self.data = {"id": 123456}
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
    @pytest.mark.parametrize("wait_for_response", (False, True,))
    def test_calls_the_search_api_index_method_correctly(self, search_api_client, wait_for_response):
        for framework, doc_type_to_index_mapping in current_app.config['DM_FRAMEWORK_TO_ES_INDEX'].items():
            for doc_type, index_name in doc_type_to_index_mapping.items():

                index_object(framework, doc_type, 123, {'serialized': 'object'}, wait_for_response=wait_for_response)

                assert search_api_client.index.mock_calls == [
                    mock.call(
                        index_name=index_name,
                        object_id=123,
                        serialized_object={'serialized': 'object'},
                        doc_type=doc_type,
                        client_wait_for_response=wait_for_response,
                    )
                ]
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
            'Failed to add services object with id 123 to g-cloud-9 index: Unknown request failure in dmapiclient'
        )


class TestResultResponses(BaseApplicationTest):
    def _get_single_result_mock(self):
        result = mock.Mock()
        result.serialize.return_value = {"serialized": "content"}
        return result

    def test_single_result_response(self):
        with self.app.test_request_context("/"):
            result = self._get_single_result_mock()

            response = single_result_response("name", result)

            assert json.loads(response.get_data(as_text=True)) == {"name": {"serialized": "content"}}
            result.serialize.assert_called_once()

    def test_single_result_response_with_serialize_kwargs(self):
        with self.app.test_request_context("/"):
            result = self._get_single_result_mock()

            response = single_result_response("name", result, {"do": "this"})

            assert json.loads(response.get_data(as_text=True)) == {"name": {"serialized": "content"}}
            result.serialize.assert_called_once_with(do="this")

    def _get_list_result_mocks(self):
        results_query = mock.MagicMock()
        results_query.count.return_value = 2
        result = mock.Mock()
        result.serialize.side_effect = [{"serialized1": "content1"}, {"serialized2": "content2"}]
        results_query.__iter__.return_value = [result, result]
        return result, results_query

    def test_list_result_response(self):
        with self.app.test_request_context("/"):
            result, results_query = self._get_list_result_mocks()

            response = list_result_response("name", results_query)

            assert json.loads(response.get_data(as_text=True)) == {
                "name": [{"serialized1": "content1"}, {"serialized2": "content2"}],
                "meta": {"total": 2}
            }
            assert result.serialize.call_count == 2

    def test_list_result_response_with_serialize_kwargs(self):
        with self.app.test_request_context("/"):
            result, results_query = self._get_list_result_mocks()

            response = list_result_response("name", results_query, {"do": "this"})

            assert json.loads(response.get_data(as_text=True)) == {
                "name": [{"serialized1": "content1"}, {"serialized2": "content2"}],
                "meta": {"total": 2}
            }
            calls = [mock.call(do="this"), mock.call(do="this")]
            result.serialize.assert_has_calls(calls)

    def _get_paginated_result_mocks(self):
        result = mock.Mock()
        result.serialize.side_effect = [{"serialized1": "content1"}, {"serialized2": "content2"}]

        pagination = mock.MagicMock()
        pagination.total = 10
        pagination.items.__iter__.return_value = [result, result]

        results_query = mock.Mock()
        results_query.paginate.return_value = pagination

        return result, results_query, pagination

    @mock.patch('app.utils.pagination_links', autospec=True)
    def test_paginated_result_response(self, pagination_links):
        with self.app.test_request_context("/"):
            result, results_query, pagination = self._get_paginated_result_mocks()
            pagination_links.return_value = {"paginated": "links"}

            response = paginated_result_response("name", results_query, 3, 2, '.endpoint', {"arg": "value"})

            assert json.loads(response.get_data(as_text=True)) == {
                "name": [{"serialized1": "content1"}, {"serialized2": "content2"}],
                "meta": {"total": 10},
                "links": {"paginated": "links"}
            }
            results_query.paginate.assert_called_once_with(page=3, per_page=2)
            pagination_links.assert_called_once_with(pagination, '.endpoint', {"arg": "value"})
            assert result.serialize.call_count == 2

    @mock.patch('app.utils.pagination_links', autospec=True)
    def test_paginated_result_response_with_serialize_kwargs(self, pagination_links):
        with self.app.test_request_context("/"):
            result, results_query, pagination = self._get_paginated_result_mocks()
            pagination_links.return_value = {"paginated": "links"}

            response = paginated_result_response(
                "name", results_query, 3, 2, '.endpoint', {"arg": "value"}, {"do": "this"}
            )

            assert json.loads(response.get_data(as_text=True)) == {
                "name": [{"serialized1": "content1"}, {"serialized2": "content2"}],
                "meta": {"total": 10},
                "links": {"paginated": "links"}
            }
            results_query.paginate.assert_called_once_with(page=3, per_page=2)
            pagination_links.assert_called_once_with(pagination, '.endpoint', {"arg": "value"})
            calls = [mock.call(do="this"), mock.call(do="this")]
            result.serialize.assert_has_calls(calls)


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
    assert purge_nulls_from_data(service_with_nulls) == same_service_without_nulls


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
