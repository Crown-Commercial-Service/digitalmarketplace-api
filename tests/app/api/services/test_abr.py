import pytest

from app.api.services import abr_service
import requests
import unittest
import mock
from mock import patch

class TestAbrService(unittest.TestCase):

        def mocked_fetch_data():
            data = '<ABRPayloadSearchResults xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns="http://abr.business.gov.au/ABRXMLSearch/"> <response><stateCode>NSW</stateCode> <postcode>2750</postcode> <organisationName>yay</organisationName></response></ABRPayloadSearchResults>'
            return data
        
        @mock.patch("app.api.services.abr_service.fetch_data", side_effect=mocked_fetch_data)
        def test_fetch(self, mocked_fetch_data):
            expected_parsed_data =  '{"state": "NSW", "organisation_name": "yay", "postcode": "2750"}'
            data = abr_service.get_data()
            self.assertEqual(data, expected_parsed_data)

        @mock.patch('app.api.services.abr_service.fetch_data')
        def test_connecton_error_exception(self, mock_requests_get):
            """ test the connectionError is raised"""
            mock_requests_get.side_effect = requests.exceptions.ConnectionError()
            with self.assertRaises(requests.exceptions.ConnectionError):
                abr_service.get_data()
        

        @mock.patch('app.api.services.abr_service.fetch_data')
        def test_http_error_exception(self, mock_requests_get):
            """ test the httpError is raised"""
            mock_requests_get.side_effect = requests.exceptions.HTTPError()
            with self.assertRaises(requests.exceptions.HTTPError):
                abr_service.get_data()

        @mock.patch('app.api.services.abr_service.fetch_data')
        def test_proxy_error_exception(self, mock_requests_get):
            """ test the proxy Error is raised"""
            mock_requests_get.side_effect = requests.exceptions.ProxyError()
            with self.assertRaises(requests.exceptions.ProxyError):
                abr_service.get_data()
        
        @mock.patch('app.api.services.abr_service.fetch_data')
        def test_ssl_error_exception(self, mock_requests_get):
            """ test the proxy Error is raised"""
            mock_requests_get.side_effect = requests.exceptions.SSLError()
            with self.assertRaises(requests.exceptions.SSLError):
                abr_service.get_data()

        @mock.patch('app.api.services.abr_service.fetch_data')
        def test_timeout(self):
            """ test the proxy Error is raised"""
            # mock_requests_get.side_effect = requests.exceptions.Timeout()
            with self.assertRaises(Exception) as ex:
                abr_service.get_data()
            
            # import pdb; pdb.set_trace()
            # assert str(ex) == 'Failed exception raised'
        
    #  check that they return empty organisation_name, state, postcode
        #timeout error

        #payload Exceptions
        #check with internation abn

    # test with spaces and different alternatives of the abn
    #test for invalid abn