from app.api.helpers import Service
import requests
from requests.exceptions import (HTTPError, Timeout, ConnectionError, SSLError, ProxyError, RequestException)
import re
from app.api.business.errors import AbrError
from flask import current_app
from xml.sax import saxutils


class AbrService(Service):

    def __init__(self, *args, **kwargs):
        super(AbrService, self).__init__(*args, **kwargs)

    def find_business_by_abn(self, abn):
        url = self.build_abn_search_url(abn)
        response = self.call_abr_api(url)
        result = self.get_data(response)
        return result

    def build_abn_search_url(self, abn):
        api_key = current_app.config['ABR_API_KEY']
        include_historical_details = 'N'
        link = current_app.config['ABR_API_LINK']
        url = link + abn + '&includeHistoricalDetails=' + include_historical_details + '&authenticationGuid=' + api_key
        return url

    def call_abr_api(self, url):
        try:
            response = requests.get(url)
            if response.ok:
                error = self.get_abr_exception(response.content)
                if error is None:
                    return response.content
                else:
                    raise AbrError(error)

        # Timeout error is a payload exception hence it is not included
        except ConnectionError as ex:
            raise AbrError('Connection Error')

        except HTTPError as ex:
            raise AbrError('HTTP Error')

        except ProxyError as ex:
            raise AbrError('Proxy Error')

        except SSLError as ex:
            raise AbrError('SSL Error')

        except RequestException as ex:
            raise AbrError('Unexpected request error')

    # Payload exceptions: https://abr.business.gov.au/Documentation/Exceptions
    def get_abr_exception(self, response):
        exception_code = 'No exception code found'
        exception_description = 'No exception description found'

        search_exception_code = re.findall(r'<exceptionCode>(.+)</exceptionCode>', response)
        if len(search_exception_code) > 0:
            exception_code = search_exception_code[0]

        search_exception_description = re.findall(r'<exceptionDescription>(.+)</exceptionDescription>',
                                                  response)
        if len(search_exception_description) > 0:
            exception_description = search_exception_description[0]

        if (exception_code != 'No exception code found') or (exception_description != 'No exception description found'):
            error = exception_code + ': ' + exception_description
            return error
        else:
            return None

    def get_data(self, response):
        # takes the first organisation name
        search_xml_organisation_name = re.findall(r'<organisationName>(.+)</organisationName>', response)
        organisation_name = search_xml_organisation_name[0] if len(search_xml_organisation_name) > 0 else ''
        # this only works for &, < and > but not ' and ""
        organisation_name = saxutils.unescape(organisation_name)

        # takes the first postcode
        search_xml_postcode = re.findall(r'<postcode>(.+)</postcode>', response)
        postcode = search_xml_postcode[0] if len(search_xml_postcode) > 0 else ''

        # takes the first state
        search_xml_state = re.findall(r'<stateCode>(.+)</stateCode>', response)
        state = search_xml_state[0] if len(search_xml_state) > 0 else ''
        abn_dict = {
            'organisation_name': organisation_name,
            'postcode': postcode,
            'state': state
        }
        return abn_dict
