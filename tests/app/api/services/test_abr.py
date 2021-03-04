import pytest
from app.api.services import abr_service
from app.api.business.errors import AbrError
import requests
import mock
from mock import patch


class TestAbrService():

    def mocked_find_business_by_abn(self):
        data = '<ABR><response><stateCode>NSW</stateCode><postcode>2750</postcode>'\
            '<organisationName>yay</organisationName></response></ABR>'
        return data

    def mocked_payload_exception(self):
        data = '<ABR><response><exception><exceptionDescription>Search text is not a '\
            'valid ABN or ACN</exceptionDescription><exceptionCode>WEBSERVICES</exceptionCode>'\
            '</exception></response></ABR>'
        return data

    def mocked_payload_exception_with_no_description(self):
        data = '<ABR><response><exception><exceptionCode>WEBSERVICES</exceptionCode>'\
            '</exception></response></ABR>'
        return data

    def mocked_payload_exception_with_no_code(self):
        data = '<ABR><response><exception><exceptionDescription>Search text is not a '\
            'valid ABN or ACN</exceptionDescription>'\
            '</exception></response></ABR>'
        return data

    def mocked_payload_exception_with_no_code_and_no_description(self):
        data = '<ABR><response></response></ABR>'
        return data

    @mock.patch("app.api.services.abr_service.call_abr_api")
    def test_abr_response_can_be_parsed(self, mocked_find_business_by_abn):
        expected_parsed_data = {'state': 'NSW', 'organisation_name': 'yay', 'postcode': '2750'}
        data = abr_service.get_data(self.mocked_find_business_by_abn())
        assert data == expected_parsed_data

    @mock.patch("app.api.services.abr_service.call_abr_api")
    def test_abr_exception_can_be_parsed(self, mocked_payload_exception):
        expected_msg = 'WEBSERVICES: Search text is not a valid ABN or ACN'
        result = abr_service.get_abr_exception(self.mocked_payload_exception())
        assert result == expected_msg

    @mock.patch("app.api.services.abr_service.call_abr_api")
    def test_abr_exception_can_be_parsed_with_no_exception_desc(self, mocked_payload_exception_with_no_description):
        expected_msg = 'WEBSERVICES: No exception description found'
        result = abr_service.get_abr_exception(self.mocked_payload_exception_with_no_description())
        assert result == expected_msg

    @mock.patch("app.api.services.abr_service.call_abr_api")
    def test_abr_exception_can_be_parsed_with_no_exception_code(self, mocked_payload_exception_with_no_code):
        expected_msg = 'No exception code found: Search text is not a valid ABN or ACN'
        result = abr_service.get_abr_exception(self.mocked_payload_exception_with_no_code())
        assert result == expected_msg

    @mock.patch("app.api.services.abr_service.call_abr_api")
    def test_abr_exception_parsed_with_no_ex_code_desc(self, mocked_payload_exception_with_no_code_and_no_description):
        expected_msg = None
        result = abr_service.get_abr_exception(self.mocked_payload_exception_with_no_code_and_no_description())
        assert result == expected_msg

    @mock.patch('app.api.services.abr_service.call_abr_api')
    def test_connecton_error_exception_raised(self, mock_requests_get):
        mock_requests_get.side_effect = requests.exceptions.ConnectionError()
        url = 'http://google.com'
        with pytest.raises(requests.exceptions.ConnectionError):
            abr_service.call_abr_api(url)

    @mock.patch('app.api.services.abr_service.call_abr_api')
    def test_ssl_error_exception_raised(self, mock_requests_get):
        mock_requests_get.side_effect = requests.exceptions.SSLError()
        url = 'http://google.com'
        with pytest.raises(requests.exceptions.SSLError):
            abr_service.call_abr_api(url)

    @mock.patch('app.api.services.abr_service.call_abr_api')
    def test_http_error_exception_raised(self, mock_requests_get):
        mock_requests_get.side_effect = requests.exceptions.HTTPError()
        url = 'http://google.com'
        with pytest.raises(requests.exceptions.HTTPError):
            abr_service.call_abr_api(url)

    @mock.patch('app.api.services.abr_service.call_abr_api')
    def test_proxy_error_exception_raised(self, mock_requests_get):
        mock_requests_get.side_effect = requests.exceptions.ProxyError()
        url = 'http://google.com'
        with pytest.raises(requests.exceptions.ProxyError):
            abr_service.call_abr_api(url)

    @mock.patch('app.api.services.abr_service.call_abr_api')
    def test_http_exception_message(self, mock_requests_get):
        mock_requests_get.side_effect = requests.exceptions.HTTPError('HTTP Error')
        url = 'http://google.com'
        with pytest.raises(requests.exceptions.HTTPError) as ex_info:
            abr_service.call_abr_api(url)

        assert ex_info.value.message == 'HTTP Error'

    @mock.patch('app.api.services.abr_service.call_abr_api')
    def test_proxy_exception_message(self, mock_requests_get):
        mock_requests_get.side_effect = requests.exceptions.ProxyError('Proxy Error')
        url = 'http://google.com'
        with pytest.raises(requests.exceptions.ProxyError) as ex_msg:
            abr_service.call_abr_api(url)

        assert ex_msg.value.message == 'Proxy Error'

    @mock.patch('app.api.services.abr_service.call_abr_api')
    def test_ssl_exception_message(self, mock_requests_get):
        mock_requests_get.side_effect = requests.exceptions.SSLError('SSL Error')
        url = 'http://google.com'
        with pytest.raises(requests.exceptions.SSLError) as ex_msg:
            abr_service.call_abr_api(url)

        assert ex_msg.value.message == 'SSL Error'

    @mock.patch('app.api.services.abr_service.call_abr_api')
    def test_exception_message(self, mock_requests_get):
        mock_requests_get.side_effect = requests.exceptions.RequestException('Unexpected request error')
        url = 'http://google.com'
        with pytest.raises(requests.exceptions.RequestException) as ex_msg:
            abr_service.call_abr_api(url)

        assert ex_msg.value.message == 'Unexpected request error'
