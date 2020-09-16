import pytest

from app.api.services import abr_service
from tests.app.helpers import BaseApplicationTest
import requests
from nose.tools import assert_is_not_none
# from unittest.mock import Mock, patch, MagicMock
import requests_mock


class TestAbrService(BaseApplicationTest):
        def setup(self):
            super(TestAbrService, self).setup()
        
                # yield_fixture
        # @pytest.fixture()
        def test_abn(self):
            with requests_mock.mock() as mocker:
                mocker.get('https://pycon-au.org', json={'hello':'world'}, headers = {'Content-Type': 'application/json'})

                resp = requests.get('https://pycon-au.org')

                assert resp.json()['hello'] == 'world'
                assert resp.headers['Content-Type'] == 'application/json'
                assert mocker.called


# url regexp request_mock
        # @pytest.fixture()
        def mock_abn(self):
            b = mocker.get('https://pycon-au.org/b', text = 'PyConAU')
            c = mocker.get('https://pycon-au.org/b', text = '2017')
            e = mocker.get('https://pycon-au.org/b', text = 'Hello')

            responses = [requests.get('https://pycon-au.org/%s' % path)
                            for path in ('e', 'b', 'c')]
            for res in responses:
                assert resp.status_code == 200
            
            print(" ". join(resp.text for resp in responses))

            for m in [e, b,c]:
                assert m.called_once










        # @patch('app.api.services.abr_service.get_business_info_by_abn')
        # def test_request_response(mocker):
        #     abn = '96 257 979 159'
        #     include_historical_details ='N'
        #     link = 'https://abr.business.gov.au/abrxmlsearch/AbrXmlSearch.asmx/SearchByABNv201205?searchString='
        #     url = link + abn + '&includeHistoricalDetails=' + include_historical_details + '&authenticationGuid=' + api_key

        #     mock_api = mocker.MagicMock(name ='api')
        #     mock_api.get.side_effect = load_data
            
        #     mocker.patch(''), new = mock_api)


        #     #Act
        #     result = abr_service.get_business_info_by_abn()
            # response = requests.get('http://jsonplaceholder.typicode.com/todos')
            # assert_true(response.ok)

            # abn = '96 257 979 159'
            # call service, sends a request to the server

            # response = abr_service.get_business_info_by_abn(abn)
            # if the request is successfully, I expect a response
            # assert_is_not_none(response)

        # check if it works

    #  check that they return empty organisation_name, state, postcode
        # test for connectionError
        # HttpError
        #ProxyError
        #timeout error
        #SSLError

        #payload Exceptions

    # test with spaces and different alternatives of the abn
    #test invalid abn?


        #


