# -*- coding: utf-8 -*-
import pendulum
from app.api.services import domain_service, suppliers


class RFXDataValidator(object):
    def __init__(self, data):
        self.data = data

    def validate_closed_at(self):
        if 'closedAt' not in self.data or not self.data['closedAt']:
            return False
        parsed = pendulum.parse(self.data['closedAt']).in_timezone('Australia/Canberra').start_of('day')
        if parsed < pendulum.now('Australia/Canberra').add(days=2).start_of('day'):
            return False
        return True

    def validate_title(self):
        return True if self.data['title'].replace(' ', '') else False

    def validate_organisation(self):
        return True if self.data['organisation'].replace(' ', '') else False

    def validate_summary(self):
        return True if self.data['summary'].replace(' ', '') else False

    def validate_working_arrangements(self):
        return True if self.data['workingArrangements'].replace(' ', '') else False

    def validate_location(self):
        if not self.data['location']:
            return False
        if not len(self.data['location']) > 0:
            return False
        whitelist = [
            'Australian Capital Territory',
            'New South Wales',
            'Northern Territory',
            'Queensland',
            'South Australia',
            'Tasmania',
            'Victoria',
            'Western Australia',
            'Offsite'
        ]
        for location in self.data['location']:
            if location not in whitelist:
                return False
        return True

    def validate_seller_category(self):
        if not self.data['sellerCategory'].replace(' ', ''):
            return False
        domain_ids = [domain.id for domain in domain_service.all()]
        return True if int(self.data['sellerCategory']) in domain_ids else False

    def validate_sellers(self):
        if not self.data['sellers']:
            return False
        if not len(self.data['sellers']) > 0:
            return False
        for supplier_code in self.data['sellers']:
            supplier = suppliers.get_supplier_by_code(int(supplier_code))
            if not supplier:
                return False
            if suppliers.get_supplier_assessed_status(supplier.id, int(self.data['sellerCategory'])) != 'assessed':
                return False
        return True

    def validate_response_formats(self):
        if not self.data['evaluationType']:
            return False
        if not len(self.data['evaluationType']) > 0:
            return False
        if 'Written proposal' not in self.data['evaluationType'] and\
           'Response template' not in self.data['evaluationType']:
            return False
        whitelist = [
            'Response template',
            'Written proposal',
            'Presentation'
        ]
        for val in self.data['evaluationType']:
            if val not in whitelist:
                return False
        return True

    def validate_proposal_type(self):
        if 'Written proposal' in self.data['evaluationType']:
            if not len(self.data['proposalType']) > 0:
                return False
            whitelist = [
                'Breakdown of costs',
                'Case study',
                'References',
                'Résumés'
            ]
            for val in self.data['proposalType']:
                if val.encode('utf-8') not in whitelist:
                    return False
        return True

    def validate_requirements_document(self):
        if not self.data['requirementsDocument']:
            return False
        if not len(self.data['requirementsDocument']) > 0:
            return False
        return True

    def validate_response_template(self):
        if 'Response template' in self.data['evaluationType']:
            if not self.data['responseTemplate']:
                return False
            if not len(self.data['responseTemplate']) > 0:
                return False
        return True

    def validate_start_date(self):
        return True if self.data['startDate'].replace(' ', '') else False

    def validate_contract_length(self):
        return True if self.data['contractLength'].replace(' ', '') else False

    def validate_evaluation_criteria(self):
        if not self.data['evaluationCriteria']:
            return False
        if not len(self.data['evaluationCriteria']) > 0:
            return False
        weightings = 0
        for criteria in self.data['evaluationCriteria']:
            if 'criteria' not in criteria:
                return False
            if not criteria['criteria'].replace(' ', ''):
                return False
            if self.data['includeWeightings']:
                if 'weighting' not in criteria:
                    return False
                if not criteria['weighting'].replace(' ', ''):
                    return False
                if int(criteria['weighting']) == 0:
                    return False
                weightings += int(criteria['weighting'])
        if self.data['includeWeightings']:
            if weightings != 100:
                return False
        return True

    def validate_contact_number(self):
        if not self.data['contactNumber'].replace(' ', ''):
            return False
        return True

    def validate_required(self):
        errors = []
        if not self.validate_title():
            errors.append('You must add a title')
        if not self.validate_organisation():
            errors.append('You must add the name of your department, agency or organisation')
        if not self.validate_summary():
            errors.append('You must add a summary of work to be done')
        if not self.validate_working_arrangements():
            errors.append('You must add the working arrangements')
        if not self.validate_location():
            errors.append('You must select a valid location of where the work can be done')
        if not self.validate_seller_category():
            errors.append('Invalid seller category/domain')
        if not self.validate_sellers():
            errors.append(
                'You must select at least one seller and each seller must be assessed for the chosen category'
            )
        if not self.validate_response_formats():
            errors.append('You must choose what you would like sellers to provide through the Marketplace')
        if not self.validate_proposal_type():
            errors.append('You must select at least one proposal type when choosing to receive Written proposals.')
        if not self.validate_requirements_document():
            errors.append('You must upload a requirements document')
        if not self.validate_response_template():
            errors.append('You must upload a response template')
        if not self.validate_start_date():
            errors.append('You must add an estimated start date')
        if not self.validate_contract_length():
            errors.append('You must add a contract length')
        if not self.validate_evaluation_criteria():
            errors.append(
                'You must not have any empty criteria, any empty weightings, all weightings must be greater than 0,\
                 and add up to 100'
            )
        if not self.validate_closed_at():
            errors.append('The closing date must be at least 2 days into the future')
        if not self.validate_contact_number():
            errors.append('Contact number must be a valid phone number, including an area code')
        return errors

    def validate(self, publish=False):
        errors = []

        try:
            if publish:
                errors = errors + self.validate_required()

            # allowed fields and types
            whitelist = [
                {'name': 'id', 'type': int},
                {'name': 'title', 'type': basestring},
                {'name': 'organisation', 'type': basestring},
                {'name': 'location', 'type': list},
                {'name': 'summary', 'type': basestring},
                {'name': 'industryBriefing', 'type': basestring},
                {'name': 'sellerCategory', 'type': basestring},
                {'name': 'sellers', 'type': dict},
                {'name': 'attachments', 'type': list},
                {'name': 'requirementsDocument', 'type': list},
                {'name': 'responseTemplate', 'type': list},
                {'name': 'evaluationType', 'type': list},
                {'name': 'proposalType', 'type': list},
                {'name': 'evaluationCriteria', 'type': list},
                {'name': 'includeWeightings', 'type': bool},
                {'name': 'closedAt', 'type': basestring},
                {'name': 'contactNumber', 'type': basestring},
                {'name': 'startDate', 'type': basestring},
                {'name': 'contractLength', 'type': basestring},
                {'name': 'contractExtensions', 'type': basestring},
                {'name': 'budgetRange', 'type': basestring},
                {'name': 'workingArrangements', 'type': basestring},
                {'name': 'securityClearance', 'type': basestring},
                {'name': 'publish', 'type': bool},
                {'name': 'sellerSelector', 'type': basestring}
            ]

            request_keys = self.data.keys()
            whitelisted_keys = [key['name'] for key in whitelist]
            for key in request_keys:
                if key not in whitelisted_keys:
                    errors.append('Unexpected field "%s"' % key)

            for key in whitelist:
                if key['name'] in request_keys and not isinstance(self.data.get(key['name'], None), key['type']):
                    errors.append('Field "%s" is invalid, unexpected type' % key['name'])

        except Exception as e:
            errors.append(e.message)

        return errors
