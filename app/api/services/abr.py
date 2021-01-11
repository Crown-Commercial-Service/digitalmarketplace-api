from app.api.helpers import Service

import requests
from requests.exceptions import (HTTPError, Timeout, ConnectionError, SSLError, ProxyError)
import re
from app.tasks import publish_tasks
from app.api.business.errors import AbrError
from flask import current_app
import xml.etree.ElementTree as ElementTree
import json
from xml.sax import saxutils


class AbrService(Service):

    def __init__(self, *args, **kwargs):
        super(AbrService, self).__init__(*args, **kwargs)

    def fetch_data(self, abn):
        url = self.build_url(abn)
        get_xml_data = self.get_response(url)
        result = self.get_data2(get_xml_data)
        return result

    # using the supplier's abn to set up the link to be sent ABR API
    def build_url(self, abn):
        api_key = current_app.config['ABR_API_KEY']
        include_historical_details = 'N'
        link = current_app.config['ABR_API_LINK']
        url = link + abn + '&includeHistoricalDetails=' + include_historical_details + '&authenticationGuid=' + api_key
        return url

    def get_response(self, url):
        try:
            response = requests.get(url)
            if response.ok:
                xmlText = response.content
                return xmlText

        # Raising different exceptions
        # Timeout error is considered as payload exception hence it is not included
        except ConnectionError as ex:
            raise AbrError('Connection Error')

        except HTTPError as ex:
            raise AbrError('HTTP Error')

        except ProxyError as ex:
            raise AbrError('Proxy Error')

        except SSLError as ex:
            raise AbrError('SSL Error')

        except Exception as ex:
                raise AbrError('Failed exception raised')

    def get_data(self, xmlText):
        try:
            # takes the first organisation name
            search_xml_organisation_name = re.findall(r'<organisationName>(.*?)</organisationName>', xmlText)
            organisation_name = search_xml_organisation_name[0]
            # this only works for &, < and > but not ' and ""
            organisation_name = saxutils.unescape(organisation_name)

            # takes the first postcode
            search_xml_postcode = re.findall(r'<postcode>(.*?)</postcode>', xmlText)
            postcode = search_xml_postcode[0]

            # takes the first state
            search_xml_state = re.findall(r'<stateCode>(.*?)</stateCode>', xmlText)
            state = search_xml_state[0]

            return json.dumps({
                'organisation_name': organisation_name,
                'postcode': postcode,
                'state': state
            })

        # Payload exceptions: https://abr.business.gov.au/Documentation/Exceptions
        except Exception as ex:
            search_exception_code = re.findall(r'<exceptionCode>(.*?)</exceptionCode>', xmlText)
            exception_code = search_exception_code[0]

            search_exception_description = re.findall(r'<exceptionDescription>(.*?)</exceptionDescription>', xmlText)
            exception_description = search_exception_description[0]

            raise AbrError(exception_code + ': ' + exception_description)
