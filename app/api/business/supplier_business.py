import collections

import pendulum

from app.api.business.agreement_business import (get_current_agreement,
                                                 get_new_agreement,
                                                 has_signed_current_agreement)
from app.api.business.validators import SupplierValidator
from app.api.services import application_service, key_values_service, suppliers
import requests
from requests.exceptions import (HTTPError, Timeout, ConnectionError, SSLError, ProxyError)
import re
from app.tasks import publish_tasks
from app.api.business.errors import AbrError
from flask import current_app
import xml.etree.ElementTree as ElementTree
import json

def get_business_info_by_abn(email_address, abn):
    apiKey = current_app.config['ABR_API_KEY']
    includeHistoricalDetails = 'N'
    abn = abn
    url = 'https://abr.business.gov.au/abrxmlsearch/AbrXmlSearch.asmx/SearchByABNv201205?searchString=' + abn + '&includeHistoricalDetails=' + includeHistoricalDetails + '&authenticationGuid=' + apiKey
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        xmlText = response.content
        root = ElementTree.fromstring(xmlText)

    # Rasing Different exceptions
    except ConnectionError as ex:
        raise AbrError('Connection Error')

    # Invalid HTTP Reponse
    except HTTPError as ex:
        raise AbrError('HTTP Error')

    except ProxyError as ex:
        raise AbrError('ProxyError')

    except Timeout as ex:
        raise AbrError('Timeout')

    except SSLError as ex:
        raise AbrError('SSLError')

    # Any other expections
    except Exception as ex:
        raise AbrError('Some exception raised')

    # takes the first organisationName
    search_xml_organisation_name = re.findall(r'<organisationName>(.*?)</organisationName>', xmlText)
    organisation_name = search_xml_organisation_name[0]

    # takes the first postcode
    search_xml_postcode = re.findall(r'<postcode>(.*?)</postcode>', xmlText)
    postcode = search_xml_postcode[0]

    # takes the first state
    search_xml_state = re.findall(r'<stateCode>(.*?)</stateCode>', xmlText)
    state = search_xml_state[0]

    # a dict to store these pre-filled info
    business_info_abn_dict = {'organisation_name': organisation_name, 'postcode':postcode, 'state': state}
    business_info_abn = json.dumps(business_info_abn_dict)
    print(business_info_abn_dict)

    return business_info_abn

def abn_is_used(abn):
    abn = "".join(abn.split())
    supplier = suppliers.get_supplier_by_abn(abn)
    if supplier:
        return True
    application = application_service.get_applications_by_abn(abn)
    if application:
        return True
    return False


def get_supplier_messages(code, skip_application_check):
    applications = application_service.find(
        supplier_code=code,
        type='edit'
    ).all()

    supplier = suppliers.get_supplier_by_code(code)
    validation_result = SupplierValidator(supplier).validate_all()

    if any([a for a in applications if a.status == 'saved']):
        validation_result.warnings.append({
            'message': 'You have saved updates on your profile. '
                       'You must submit these changes to the Marketplace for review. '
                       'If you did not make any changes, select \'Discard all updates\'.',
            'severity': 'warning',
            'step': 'update',
            'id': 'SB001'
        })

    if not skip_application_check:
        if any([a for a in applications if a.status == 'submitted']):
            del validation_result.warnings[:]
            del validation_result.errors[:]

    if not has_signed_current_agreement(supplier):
        if get_current_agreement():
            message = (
                'Your authorised representative {must accept the new Master Agreement} '
                'before you can apply for opportunities.'
            )
            validation_result.errors.append({
                'message': message,
                'severity': 'error',
                'step': 'representative',
                'id': 'SB002',
                'links': {
                    'must accept the new Master Agreement': '/2/seller-edit/{}/representative'.format(code)
                }
            })
    else:
        new_master_agreement = get_new_agreement()
        if new_master_agreement:
            start_date = new_master_agreement.start_date.in_tz('Australia/Canberra').date()
            message = (
                'From {}, your authorised representative must '
                'accept the new Master Agreement '
                'before you can apply for opportunities.'
            ).format(start_date.strftime('%-d %B %Y'))

            validation_result.warnings.append({
                'message': message,
                'severity': 'warning',
                'step': 'representative',
                'id': 'SB002'
            })

    return validation_result
