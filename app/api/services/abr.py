from datetime import datetime, timedelta

import pytz
from sqlalchemy import and_, case, func, literal, or_, select, union
from sqlalchemy.orm import joinedload, noload, raiseload
from sqlalchemy.dialects.postgresql import aggregate_order_by

from app import db
from app.api.helpers import Service
from app.models import (CaseStudy,
                        Domain,
                        Framework,
                        Supplier,
                        SupplierDomain,
                        SupplierFramework,
                        User)
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
        # self.xmlText = None
    
    
#     def get_business_info_by_abn(self, abn):
#         api_key = current_app.config['ABR_API_KEY']
#         include_historical_details = 'N'
#         # maybe remove this and have it as abn
#         # maybe add the link to config file
#         abn = abn
#         link = 'https://abr.business.gov.au/abrxmlsearch/AbrXmlSearch.asmx/SearchByABNv201205?searchString='
#         url = link + abn + '&includeHistoricalDetails=' + include_historical_details + '&authenticationGuid=' + api_key

# # maybe refactor code and split it up into 2 functions 1) sets up the url 2) to get responses from the abr service
#         try:
#             response = requests.get(url)
#             print("before response.ok")
#             if response.ok:
#                 xmlText = response.content
#                 root = ElementTree.fromstring(xmlText)
#                 # do i need root? if I just reference xmlTree
#                 search_xml_organisation_name = re.findall(r'<organisationName>(.*?)</organisationName>', xmlText)
#                 organisation_name = search_xml_organisation_name[0]
#                 # this only works for &, < and > but not ' and ""
#                 organisation_name = saxutils.unescape(organisation_name)

#                 # takes the first postcode
#                 search_xml_postcode = re.findall(r'<postcode>(.*?)</postcode>', xmlText)
#                 postcode = search_xml_postcode[0]

#                 # takes the first state
#                 search_xml_state = re.findall(r'<stateCode>(.*?)</stateCode>', xmlText)
#                 state = search_xml_state[0]

#                 return json.dumps({
#                     'organisation_name': organisation_name,
#                     'postcode': postcode,
#                     'state': state
#                 })

#             response.raise_for_status()
            
#         # might need an else and put all the raise exceptions
#         # Rasing different exceptions
#         except ConnectionError as ex:
#             raise AbrError('Connection Error')

#         except HTTPError as ex:
#             raise AbrError('HTTP Error')

#         except ProxyError as ex:
#             raise AbrError('ProxyError')

#         except Timeout as ex:
#             raise AbrError('Timeout')

#         except SSLError as ex:
#             raise AbrError('SSLError')

#         # Any other exceptions
#         except Exception as ex:
#             # maybe add the payload exceptions in here
#             raise AbrError('Failed exception raised')

        # need to relook this again
        # searching for payload exceptions
        # search_except_description = re.findall(r'<exceptionDescription>(.*?)</exceptionDescription>', xmlText)
        # except_description = search_except_description[0]

        # # raises except descriptions
        # if except_description:
        #     raise AbrError(except_description)


# maybe refactor the code into 3 or 4 ways
# init can set yp the data so self.url = "https", then use a method called get_url to return self.url 
# then fetch_data method and get request url raise the exceptions 
# then third methid get_data, if there is data parse it https://medium.com/@kevinhowbrook/mocking-api-request-tests-for-wagtail-with-kanyerest-520a4374f81f


    # might need to consider changing the name 
    def get_url(self, abn):
        api_key = current_app.config['ABR_API_KEY']
        include_historical_details = 'N'

        # resp = requests.get(BASE_UR + '')
        link = 'https://abr.business.gov.au/abrxmlsearch/AbrXmlSearch.asmx/SearchByABNv201205?searchString='
        url = link + abn + '&includeHistoricalDetails=' + include_historical_details + '&authenticationGuid=' + api_key

        a = self.fetch_data(url)
        print("this is a " + a)
        return a
    
    def fetch_data(self, url):
        try:
            response = requests.get(url)

            if response.ok:
                xmlText = response.content
                c = self.get_data(xmlText)
                return c

            response.raise_for_status()
            
        # might need an else and put all the raise exceptions
        # Rasing different exceptions
        except ConnectionError as ex:
            raise AbrError('Connection Error')

        except HTTPError as ex:
            raise AbrError('HTTP Error')

        except ProxyError as ex:
            raise AbrError('ProxyError + reshma')

        # this is considered as payload exception
        except Timeout as ex:
            raise AbrError('Timeout')

        except SSLError as ex:
            raise AbrError('SSLError')

        # Any other exceptions + timeout as it is considered as an application error
        except Exception as ex:
                raise AbrError('Failed exception raised')


    def get_data(self, xmlText):
        root = ElementTree.fromstring(xmlText)
        # do i need root? if I just reference xmlTree
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
        print("organisation name, postcode and state" + organisation_name + postcode + state)

        return json.dumps({
            'organisation_name': organisation_name,
            'postcode': postcode,
            'state': state
        })

        # else:
        #     return []