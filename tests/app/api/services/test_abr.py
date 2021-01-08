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

        # new version
        @mock.patch("app.api.services.abr_service.get_response")
        def test_fetch2(self, mocked_fetch_data):
            expected_parsed_data = '{"state": "NSW", "organisation_name": "yay", "postcode": "2750"}'
            data = abr_service.get_data2(self.mocked_fetch_data())
            self.assertEqual(data, expected_parsed_data)

# old tests

        # @mock.patch("app.api.services.abr_service.fetch_data")
        # def test_fetch(self, mocked_fetch_data):
        #     expected_parsed_data = '{"state": "NSW", "organisation_name": "yay", "postcode": "2750"}'
        #     data = abr_service.get_data(self.mocked_fetch_data())
        #     self.assertEqual(data, expected_parsed_data)

        # # assertRaises only checks if an exception was raised
        # @mock.patch('app.api.services.abr_service.fetch_data')
        # def test_connecton_error_exception_raised(self, mock_requests_get):
        #     """ test the connectionError is raised"""
        #     mock_requests_get.side_effect = requests.exceptions.ConnectionError()
        #     url = 'http://google.com'
        #     with self.assertRaises(requests.exceptions.ConnectionError):
        #         abr_service.fetch_data(url)

        # @mock.patch('app.api.services.abr_service.fetch_data')
        # def test_ssl_error_exception_raised(self, mock_requests_get):
        #     """ test the connectionError is raised"""
        #     mock_requests_get.side_effect = requests.exceptions.SSLError()
        #     url = 'http://google.com'
        #     with self.assertRaises(requests.exceptions.SSLError):
        #         abr_service.fetch_data(url)

        # @mock.patch('app.api.services.abr_service.fetch_data')
        # def test_http_error_exception_raised(self, mock_requests_get):
        #     """ test the httpError is raised"""
        #     mock_requests_get.side_effect = requests.exceptions.HTTPError()
        #     url = 'http://google.com'
        #     with self.assertRaises(requests.exceptions.HTTPError):
        #         abr_service.fetch_data(url)

        # @mock.patch('app.api.services.abr_service.fetch_data')
        # def test_proxy_error_exception_raised(self, mock_requests_get):
        #     """ test the httpError is raised"""
        #     mock_requests_get.side_effect = requests.exceptions.ProxyError()
        #     url = 'http://google.com'
        #     with self.assertRaises(requests.exceptions.ProxyError):
        #         abr_service.fetch_data(url)

        # @mock.patch('app.api.services.abr_service.fetch_data')
        # def test_http_exception_message(self, mock_requests_get):
        #     """ test the httpError exception message"""
        #     mock_requests_get.side_effect = requests.exceptions.HTTPError('HTTP Error')
        #     url = 'http://google.com'
        #     with pytest.raises(requests.exceptions.HTTPError) as excinfo:
        #         abr_service.fetch_data(url)

        #     assert excinfo.value.message == 'HTTP Error'

        # @mock.patch('app.api.services.abr_service.fetch_data')
        # def test_proxy_exception_message(self, mock_requests_get):
        #     mock_requests_get.side_effect = requests.exceptions.ProxyError('ProxyError')
        #     url = 'http://google.com'
        #     with pytest.raises(requests.exceptions.ProxyError) as excinfo:
        #         abr_service.fetch_data(url)

        #     assert excinfo.value.message == 'ProxyError'

        # @mock.patch('app.api.services.abr_service.fetch_data')
        # def test_proxy_exception_message(self, mock_requests_get):
        #     mock_requests_get.side_effect = requests.exceptions.SSLError('SSL Error')
        #     url = 'http://google.com'
        #     with pytest.raises(requests.exceptions.SSLError) as excinfo:
        #         abr_service.fetch_data(url)

        #     assert excinfo.value.message == 'SSL Error'

        # @mock.patch('app.api.services.abr_service.fetch_data')
        # def test_exception_message(self, mock_requests_get):
        #     mock_requests_get.side_effect = Exception('Failed exception raised')
        #     url = 'http://google.com'
        #     with pytest.raises(Exception) as ex:
        #         abr_service.fetch_data(url)

        #     assert ex.value.message == 'Failed exception raised'
