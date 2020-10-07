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


    #  check that they return empty organisation_name, state, postcode
        # test for connectionError
        # HttpError
        #ProxyError
        #timeout error
        #SSLError

        #payload Exceptions
        #check with internation abn

    # test with spaces and different alternatives of the abn
    #test for invalid abn

   # @mock.patch("app.api.services.abr_service.fetch_data")
        # def test_fetch_with_exception(self):
        #     # with self.assertRaises(Exception) as context:
        #     #     abr_service.get_data()

        # #     self.assertTrue('HTTP Error' in context.exception)
        #     with pytest.raises(requests.exceptions.Timeout) as e:
        #         abr_service.get_data()
        #     assert str(e) == "AbrError: HTTP Error"
            
            # self.assertRaises(HTTPError, abr_service.get_data())

                            # with self.assertRaises(Exception) as context:
            #     abr_service.get_data()

        #     self.assertTrue('HTTP Error' in context.exception)
        # @patch("app.api.services.abr_service.get")
        # def test_main_exception(self):
        #     exception = HTTPError(mock.Mock(status=404), "HTTP Error")
        #     # mock_get(mock.ANY).raise_for_status.side_effect = exception

        #     with pytest.raises(HTTPError) as error_info:
        #         abr_service.get_data()
        #         assert error_info == exception

        # def test(requests_mock):
        #     abn = '42685714570'
        #     link = 'https://abr.business.gov.au/abrxmlsearch/AbrXmlSearch.asmx/SearchByABNv201205?searchString='
        #     include_historical_details = 'N'
        #     api_key = '123456789'
        #     url = link + abn + '&includeHistoricalDetails=' + include_historical_details + '&authenticationGuid=' + api_key

        #     requests_mock.get(url, status_code=404)
        #     with pytest.raises(HTTPError):
        #         resp = abr_service.fetch_data()
            
        # @mock.patch("app.api.services.abr_service.fetch_data")
        # def test_connecton_error(requests_mock):
        #     status_code = 503
        #     resp = abr_service.fetch_data()
        #     assert resp.status_code == status_code

        # @mock.patch('app.api.services.abr_service.fetch_data')
        # @mock.patch('requests.get')
        # def test_failed_query(self, mock_get):
        #     mock_resp = self._mock_response(status=500, raise_for_status=HTTPError("HTTP Error"))
        #     mock_get.return_value = mock_resp
        #     self.assertRaises(HTTPError, abr_service.fetch_data())
        # def test_verify(mock_request):
        #     mock_resp = requests.models.Response()
        #     mock_resp.status_code = 404
        #     mock_request.return_value = mock_resp
        #     # res = requests.get()
        #     res = abr_service.fetch_data()
        #     with pytest.raises(requests.exceptions.HTTPError) as err_msg:
        #         res.raise_for_status()
        #     print(err_msg)

        # def test(self):
        #     with self.assertRaises(Exception) as context:
        #         abr_service.fetch_data()
        #     self.assertTrue('Failed exception raised' in context.exception)
        # @mock.patch("app.api.services.abr_service.fetch_data", side_effect=Exception('Failed exception raised'))
        # def test_exception(self):
        #     mock_message_raise = 'Failed exception raised'
        #     resp = abr_service.fetch_data()
        #     assert resp == mock_message_raise

        # patch - filename, class name, method
        # exceptions

# doesn't work
        # @mock.patch("app.api.services.abr_service.requests.get")
        # def test_data_if_timeout(self, mock_get):
        #     """ If a timeout is caught we should be getting the default data"""
        #     mock_get.side_effect = Timeout
        #     data = abr_service.get_data()
        #     self.assertEqual(data, self.default_data)

    

    # @mock.patch('app.api.services.abr_service.fetch_data')
    # def test_shouldRaiseHttpError404(self):
    #     m = Mock(side_effect=Exception)

    #     m = mock.Mock()
        # barMock.side_effect = HttpError(mock.Mock(status=404), 'not found')
        # result = foo()
        # self.assertIsNone(result)  # fails, test raises HttpError

    # invalid abn

        # @mock.patch("app.api.services.abr_service.fetch_data")
        # def test_simple(requests_mock):
        #     api_key = '123456789'
        #     abn = '42685714570'
        #     link = 'https://abr.business.gov.au/abrxmlsearch/AbrXmlSearch.asmx/SearchByABNv201205?searchString='
        #     include_historical_details = 'N'

        #     url = link + abn + '&includeHistoricalDetails=' + include_historical_details + '&authenticationGuid=' + api_key
        #     requests_mock.get(url, text='<exception><exceptionDescription>Search text is not a valid ABN or ACN</exceptionDescription><exceptionCode>WEBSERVICES</exceptionCode></exception>')
        #     exception_message =  'WEBSERVICES: Search text is not a valid ABN or ACN'

        #     data = abr_service.get_fetch()
        #     self.assertEqual(data, exception_message)