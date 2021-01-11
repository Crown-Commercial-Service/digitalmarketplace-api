import pytest

from app.api.services import abr_service
import requests
import unittest
import mock
from mock import patch


class TestAbrService(unittest.TestCase):

    def mocked_fetch_data(self):
        data = '<ABR><response><stateCode>NSW</stateCode><postcode>2750</postcode>'\
            '<organisationName>yay</organisationName></response></ABR>'
        return data

    def mocked_payload_exception(self):
        data = '<ABR><response><exception><exceptionDescription>Search text is not a '\
            'valid ABN or ACN</exceptionDescription><exceptionCode>WEBSERVICES</exceptionCode>'\
            '</exception></response></ABR>'
        return data

    @mock.patch("app.api.services.abr_service.get_response")
    def test_parsed_data(self, mocked_fetch_data):
        """ test expected parsed data"""
        expected_parsed_data = '{"state": "NSW", "organisation_name": "yay", "postcode": "2750"}'
        data = abr_service.get_data(self.mocked_fetch_data())
        self.assertEqual(data, expected_parsed_data)

    @mock.patch("app.api.services.abr_service.get_response")
    def test_payload_exceptions(self, mocked_payload_exception):
        """ test payload exception"""
        expected_msg = 'WEBSERVICES: Search text is not a valid ABN or ACN'
        with pytest.raises(Exception) as ex_msg:
            abr_service.get_data(self.mocked_payload_exception())

        assert ex_msg.value.message == expected_msg

    @mock.patch('app.api.services.abr_service.get_response')
    def test_connecton_error_exception_raised(self, mock_requests_get):
        """ test that connection error is raised"""
        mock_requests_get.side_effect = requests.exceptions.ConnectionError()
        url = 'http://google.com'
        with self.assertRaises(requests.exceptions.ConnectionError):
            abr_service.get_response(url)

    @mock.patch('app.api.services.abr_service.get_response')
    def test_ssl_error_exception_raised(self, mock_requests_get):
        """ test that SSL error is raised"""
        mock_requests_get.side_effect = requests.exceptions.SSLError()
        url = 'http://google.com'
        with self.assertRaises(requests.exceptions.SSLError):
            abr_service.get_response(url)

    @mock.patch('app.api.services.abr_service.get_response')
    def test_http_error_exception_raised(self, mock_requests_get):
        """ test that HTTP error is raised"""
        mock_requests_get.side_effect = requests.exceptions.HTTPError()
        url = 'http://google.com'
        with self.assertRaises(requests.exceptions.HTTPError):
            abr_service.get_response(url)

    @mock.patch('app.api.services.abr_service.get_response')
    def test_proxy_error_exception_raised(self, mock_requests_get):
        """ test that proxy error is raised"""
        mock_requests_get.side_effect = requests.exceptions.ProxyError()
        url = 'http://google.com'
        with self.assertRaises(requests.exceptions.ProxyError):
            abr_service.get_response(url)

    @mock.patch('app.api.services.abr_service.get_response')
    def test_http_exception_message(self, mock_requests_get):
        """ test that HTTP error exception message"""
        mock_requests_get.side_effect = requests.exceptions.HTTPError('HTTP Error')
        url = 'http://google.com'
        with pytest.raises(requests.exceptions.HTTPError) as ex_info:
            abr_service.get_response(url)

        assert ex_info.value.message == 'HTTP Error'

    @mock.patch('app.api.services.abr_service.get_response')
    def test_proxy_exception_message(self, mock_requests_get):
        """ test that proxy error exception message"""
        mock_requests_get.side_effect = requests.exceptions.ProxyError('Proxy Error')
        url = 'http://google.com'
        with pytest.raises(requests.exceptions.ProxyError) as ex_msg:
            abr_service.get_response(url)

        assert ex_msg.value.message == 'Proxy Error'

    @mock.patch('app.api.services.abr_service.get_response')
    def test_ssl_exception_message(self, mock_requests_get):
        """ test that SSL error exception message"""
        mock_requests_get.side_effect = requests.exceptions.SSLError('SSL Error')
        url = 'http://google.com'
        with pytest.raises(requests.exceptions.SSLError) as ex_msg:
            abr_service.get_response(url)

        assert ex_msg.value.message == 'SSL Error'

    @mock.patch('app.api.services.abr_service.get_response')
    def test_exception_message(self, mock_requests_get):
        """ test other exception message"""
        mock_requests_get.side_effect = Exception('Failed exception raised')
        url = 'http://google.com'
        with pytest.raises(Exception) as ex_msg:
            abr_service.get_response(url)

        assert ex_msg.value.message == 'Failed exception raised'
