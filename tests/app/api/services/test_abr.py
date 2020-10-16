import pytest

from app.api.services import abr_service
import requests
import unittest
import mock
from mock import patch
from app.api.business.errors import AbrError

class TestAbrService(unittest.TestCase):

        def mocked_fetch_data(self):
            data = '<ABRPayloadSearchResults xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns="http://abr.business.gov.au/ABRXMLSearch/"> <response><stateCode>NSW</stateCode> <postcode>2750</postcode> <organisationName>yay</organisationName></response></ABRPayloadSearchResults>'
            return data
        
        @mock.patch("app.api.services.abr_service.fetch_data")
        def test_fetch(self, mocked_fetch_data):
            expected_parsed_data =  '{"state": "NSW", "organisation_name": "yay", "postcode": "2750"}'
            data = abr_service.get_data(self.mocked_fetch_data())
            self.assertEqual(data, expected_parsed_data)

        # assertRaises only checks if an exception was raised
        @mock.patch('app.api.services.abr_service.fetch_data')
        def test_connecton_error_exception_raised(self, mock_requests_get):
            """ test the connectionError is raised"""
            mock_requests_get.side_effect = requests.exceptions.ConnectionError()
            url = 'http://google.com'
            with self.assertRaises(requests.exceptions.ConnectionError):
                abr_service.fetch_data(url)
        

        @mock.patch('app.api.services.abr_service.fetch_data')
        def test_http_error_exception_raised(self, mock_requests_get):
            """ test the httpError is raised"""
            mock_requests_get.side_effect = requests.exceptions.HTTPError()
            url = 'http://google.com'
            with self.assertRaises(requests.exceptions.HTTPError):
                abr_service.fetch_data(url)

        
        @mock.patch('app.api.services.abr_service.fetch_data')
        def test_proxy_error_exception_raised(self, mock_requests_get):
            """ test the httpError is raised"""
            mock_requests_get.side_effect = requests.exceptions.ProxyError()
            url = 'http://google.com'
            with self.assertRaises(requests.exceptions.ProxyError):
                abr_service.fetch_data(url)


        @mock.patch('app.api.services.abr_service.fetch_data')
        def test_http_exception_message(self, mock_requests_get):
            # HTTP Error
            mock_requests_get.side_effect = requests.exceptions.HTTPError()
            url = 'http://google.com'
            with pytest.raises(requests.exceptions.HTTPError, match='HTTP Error'):
                abr_service.fetch_data(url)
            # mock_requests_get.side_effect = requests.exceptions.HTTPError()
            # url = 'http://google.com'
            # with pytest.raises(requests.exceptions.HTTPError) as excinfo:
            #     abr_service.fetch_data(url)

            # assert "HTTP Error" in str(excinfo)


        @mock.patch('app.api.services.abr_service.fetch_data')
        def test_proxy_exception_message(self, mock_requests_get):
            mock_requests_get.side_effect = requests.exceptions.ProxyError('ProxyError + reshma')
            url = 'http://google.com'
            with pytest.raises(requests.exceptions.ProxyError) as excinfo:
                abr_service.fetch_data(url)

            assert excinfo.value.message == 'ProxyError + reshma'

        @mock.patch('app.api.services.abr_service.fetch_data')
        def test_exception_message(self, mock_requests_get):
            mock_requests_get.side_effect = Exception('Failed exception raised')
            url = 'http://google.com'
            with pytest.raises(Exception) as ex:
                abr_service.fetch_data(url)

            assert ex.value.message == 'Failed exception raised'

            # mock_requests_get.side_effect = Exception()
            # url = 'http://google.com'
            # try:
            #     abr_service.fetch_data(url)

            # except requests.exceptions.ConnectionError:
            #     pass

            # except requests.exceptions.HTTPError:
            #     pass

            # except requests.exceptions.ProxyError:
            #     pass

            # # this is considered as payload exception
            # except requests.exceptions.Timeout:
            #     pass

            # except requests.exceptions.SSLError:
            #     pass

            # except Exception as ex:
            #     import pdb; pdb.set_trace()
            #     self.fail('Failed exception raised')
        
        # @mock.patch('app.api.services.abr_service.fetch_data')
        # def test_proxy_error_exception(self, proxy_host):
        #     """ test the proxy Error is raised"""
        #     # url = 'http://google.com'
        #     session = requests.Session()
        #     with pytest,raises(ProxyError):
        #         session.get()
            

            # import pdb; pdb.set_trace()
            # self.assertIn('ProxyError', context.exception)
            # self.assertTrue('ProxyError()' in context.exception)
        
        # @mock.patch('app.api.services.abr_service.fetch_data')
        # def test_exception(self, mock_requests_get):
        #     """ test the proxy Error is raised"""
        #     # mock = Mock()
        #     mock_requests_get.side_effect = Exception('Boom')
        #     url = 'http://google.com'
        #     # with self.assertRaises(requests.exceptions.ProxyError):
        #     abr_service.fetch_data(url)
        
        # @mock.patch('app.api.services.abr_service.fetch_data')
        # def test_ssl_error_exception(self, mock_requests_get):
        #     """ test the proxy Error is raised"""
        #     mock_requests_get.side_effect = requests.exceptions.SSLError()
        #     with self.assertRaises(requests.exceptions.SSLError):
        #         abr_service.get_data()

        # @mock.patch('app.api.services.abr_service.fetch_data')
        # def test_timeout(self):
        #     """ test the proxy Error is raised"""
        #     # mock_requests_get.side_effect = requests.exceptions.Timeout()
        #     with self.assertRaises(Exception) as ex:
        #         abr_service.get_data()
            
            # import pdb; pdb.set_trace()
            # assert str(ex) == 'Failed exception raised'
        
    #  check that they return empty organisation_name, state, postcode
        #timeout error

        #payload Exceptions
        #check with internation abn

    # test with spaces and different alternatives of the abn
    #test for invalid abn