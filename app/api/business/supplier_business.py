import collections

import pendulum

from app.api.business.agreement_business import (get_current_agreement,
                                                 get_new_agreement,
                                                 has_signed_current_agreement)
from app.api.business.validators import SupplierValidator
from app.api.services import application_service, key_values_service, suppliers
import requests
from requests.exceptions import HTTPError
import re
from app.tasks import publish_tasks
def get_business_name_from_abn(email_address, abn ):
    #Guid number
    authenticationGuid = '7ef41140-8406-40b4-8bf2-12582b5404ce'
    includeHistoricalDetails = 'N'
    abn = abn

    url = 'https://abr.business.gov.au/abrxmlsearch/AbrXmlSearch.asmx/SearchByABNv201205?searchString=' + abn + '&includeHistoricalDetails='+ includeHistoricalDetails +'&authenticationGuid='+ authenticationGuid
    # url = 'http://godfgdfgdogle.cs'
    try:
        response = requests.get(url)
        # if response is succcessful, no exceptions are raised
        response.raise_for_status()
        xmlText = response.content
        searchXml = re.findall(r'<organisationName>(.*?)</organisationName>', xmlText)
        # #takes the first organisation name as there are several such as trading names etc
        organisationName = searchXml[0]
        print("YAYYYYYYY")
        return organisationName

   
    except Exception as ex:
        print("SAD")
        publish_tasks.user.delay(
            publish_tasks.compress_user(user),
            'abr_failed',
            email_address=email_address,
            abn=abn
        )
        organisationName = ""
        return organisationName

    # searchXmlpostCode = re.findall(r'<postcode>(.*?)</postcode>', xmlText)
    # print(searchXmlpostCode)
    # return organisationName

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
