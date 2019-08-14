# -*- coding: utf-8 -*-
import pendulum
from app.api.services import domain_service, suppliers


class ATMDataValidator(object):
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
        if not self.validate_open_to():
            return False
        if self.data['openTo'] == 'all' and self.data['sellerCategory'] == '':
            return True
        if (
            self.data['openTo'] == 'category' and
            self.data['sellerCategory'] and
            domain_service.get_by_name_or_id(int(self.data['sellerCategory']))
        ):
            return True
        return False

    def validate_response_formats(self):
        if not self.validate_request_more_info():
            return False
        if self.data['requestMoreInfo'] == 'yes':
            if len(self.data['evaluationType']) == 0:
                return False
            whitelist = [
                'Case study',
                'References',
                'Résumés',
                'Presentation',
                'Prototype'
            ]
            for val in self.data['evaluationType']:
                if val.encode('utf-8') not in whitelist:
                    return False
        elif len(self.data['evaluationType']) > 0:
            return False
        return True

    def validate_background_information(self):
        return True if self.data['backgroundInformation'].replace(' ', '') else False

    def validate_outcome(self):
        return True if self.data['outcome'].replace(' ', '') else False

    def validate_end_users(self):
        return True if self.data['endUsers'].replace(' ', '') else False

    def validate_work_already_done(self):
        return True if self.data['workAlreadyDone'].replace(' ', '') else False

    def validate_start_date(self):
        return True if self.data['startDate'].replace(' ', '') else False

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

    def validate_open_to(self):
        if self.data['openTo'] not in ['all', 'category']:
            return False
        return True

    def validate_request_more_info(self):
        if self.data['requestMoreInfo'] not in ['yes', 'no']:
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
        if not self.validate_location():
            errors.append('You must select a valid location of where the work can be done')
        if not self.validate_open_to():
            errors.append('Invalid openTo value')
        if not self.validate_seller_category():
            errors.append('Invalid seller category/domain')
        if not self.validate_response_formats():
            errors.append('Invalid response formats choice')
        if not self.validate_request_more_info():
            errors.append('Invalid requestMoreInfo value')
        if not self.validate_background_information():
            errors.append('You must add background information')
        if not self.validate_outcome():
            errors.append('You must add the outcome to be achieved')
        if not self.validate_end_users():
            errors.append('You must add details about the users')
        if not self.validate_work_already_done():
            errors.append('You must add details for work already done')
        if not self.validate_start_date():
            errors.append('You must add an estimated start date')
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
                {'name': 'backgroundInformation', 'type': basestring},
                {'name': 'outcome', 'type': basestring},
                {'name': 'endUsers', 'type': basestring},
                {'name': 'workAlreadyDone', 'type': basestring},
                {'name': 'industryBriefing', 'type': basestring},
                {'name': 'internalReference', 'type': basestring},
                {'name': 'sellerCategory', 'type': basestring},
                {'name': 'requestMoreInfo', 'type': basestring},
                {'name': 'attachments', 'type': list},
                {'name': 'evaluationType', 'type': list},
                {'name': 'evaluationCriteria', 'type': list},
                {'name': 'includeWeightings', 'type': bool},
                {'name': 'closedAt', 'type': basestring},
                {'name': 'contactNumber', 'type': basestring},
                {'name': 'timeframeConstraints', 'type': basestring},
                {'name': 'startDate', 'type': basestring},
                {'name': 'publish', 'type': bool},
                {'name': 'openTo', 'type': basestring},
                {'name': 'sellerSelector', 'type': basestring},
                {'name': 'areaOfExpertise', 'type': basestring}
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
