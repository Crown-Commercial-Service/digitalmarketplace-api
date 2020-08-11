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
    
    def get_business_info_by_abn(self, email_address, abn):
        api_key = current_app.config['ABR_API_KEY']
        include_historical_details = 'N'
        # maybe remove this and have it as abn
        abn = abn
        link = 'https://abr.business.gov.au/abrxmlsearch/AbrXmlSearch.asmx/SearchByABNv201205?searchString='
        url = link + abn + '&includeHistoricalDetails=' + include_historical_details + '&authenticationGuid=' + api_key

        try:
            response = requests.get(url)
            response.raise_for_status()
            xmlText = response.content
            root = ElementTree.fromstring(xmlText)

        # Rasing different exceptions
        except ConnectionError as ex:
            raise AbrError('Connection Error')

        except HTTPError as ex:
            raise AbrError('HTTP Error')

        except ProxyError as ex:
            raise AbrError('ProxyError')

        except Timeout as ex:
            raise AbrError('Timeout')

        except SSLError as ex:
            raise AbrError('SSLError')

        # Any other exceptions
        except Exception as ex:
            raise AbrError('Failed exception raised')

        # need to relook this again
        # searching for payload exceptions
        # search_except_description = re.findall(r'<exceptionDescription>(.*?)</exceptionDescription>', xmlText)
        # except_description = search_except_description[0]

        # # raises except descriptions
        # if except_description:
        #     raise AbrError(except_description)

        # takes the first organisationName
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
