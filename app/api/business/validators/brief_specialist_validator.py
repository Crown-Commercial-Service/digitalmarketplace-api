# -*- coding: utf-8 -*-
import pendulum
from app.api.services import domain_service, suppliers


class SpecialistDataValidator(object):
    def __init__(self, data):
        self.data = data

    def validate_closed_at(self):
        if 'closedAt' not in self.data or not self.data.get('closedAt'):
            return False
        parsed = pendulum.parse(self.data.get('closedAt')).in_timezone('Australia/Canberra').start_of('day')
        if parsed < pendulum.now('Australia/Canberra').add(days=2).start_of('day'):
            return False
        if parsed > pendulum.now('Australia/Canberra').add(days=364).start_of('day'):
            return False
        return True

    def validate_title(self):
        return True if self.data.get('title', '').replace(' ', '') else False

    def validate_organisation(self):
        return True if self.data.get('organisation', '').replace(' ', '') else False

    def validate_summary(self):
        return True if self.data.get('summary', '').replace(' ', '') else False

    def validate_location(self):
        if not self.data.get('location', []):
            return False
        if not len(self.data.get('location', [])) > 0:
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
        for location in self.data.get('location', []):
            if location not in whitelist:
                return False
        return True

    def validate_response_formats(self):
        if len(self.data.get('evaluationType', [])) == 0:
            return False

        whitelist = [
            'Responses to selection criteria',
            'Résumés',
            'References',
            'Interviews',
            'Scenarios or tests',
            'Presentations'
        ]

        has_responses = False
        has_resume = False
        for val in self.data.get('evaluationType', []):
            if val.encode('utf-8') not in whitelist:
                return False
            if val.encode('utf-8') == whitelist[0]:
                has_responses = True
            if val.encode('utf-8') == whitelist[1]:
                has_resume = True
        if not has_responses or not has_resume:
            return False
        return True

    def validate_preferred_format_for_rates(self):
        return (
            True if
            self.data.get('preferredFormatForRates') in ['dailyRate', 'hourlyRate']
            else False
        )

    def validate_security_clearance(self):
        return (
            True
            if self.data.get('securityClearance') in [
                'noneRequired',
                'abilityToObtain',
                'mustHave',
                'other'
            ]
            else False
        )

    def validate_security_clearance_obtain(self):
        if (
            self.data.get('securityClearance') in ['abilityToObtain'] and
            self.data.get('securityClearanceObtain') not in [
                'baseline',
                'nv1',
                'nv2',
                'pv'
            ]
        ):
            return False
        return True

    def validate_security_clearance_current(self):
        if (
            self.data.get('securityClearance') in ['mustHave'] and
            self.data.get('securityClearanceCurrent') not in [
                'baseline',
                'nv1',
                'nv2',
                'pv'
            ]
        ):
            return False
        return True

    def validate_security_clearance_other(self):
        if (
            self.data.get('securityClearance') in ['other'] and
            not self.data.get('securityClearanceOther').replace(' ', '')
        ):
            return False
        return True

    def validate_work_already_done(self):
        return True if self.data.get('workAlreadyDone').replace(' ', '') else False

    def validate_start_date(self):
        if 'startDate' not in self.data or not self.data.get('startDate', '').replace(' ', ''):
            return False

        parsed = pendulum.parse(self.data.get('startDate')).in_timezone('Australia/Canberra').start_of('day')
        if parsed < pendulum.now('Australia/Canberra').start_of('day'):
            return False

        return True

    def validate_contract_length(self):
        return True if self.data.get('contractLength', '').replace(' ', '') else False

    def remove_empty_criteria(self, criteria, includeWeightings):
        if includeWeightings:
            return [c for c in criteria if (
                c['criteria'].replace(' ', '') or
                c.get('weighting', '').replace(' ', '')
            )]
        else:
            return [c for c in criteria if (
                c['criteria'].replace(' ', '')
            )]

    def validate_evaluation_criteria_essential(self):
        if not self.data.get('essentialRequirements'):
            return False

        self.data['essentialRequirements'] = self.remove_empty_criteria(
            self.data.get('essentialRequirements'),
            self.data.get('includeWeightingsEssential')
        )

        if not len(self.data.get('essentialRequirements')) > 0:
            return False

        weightings = 0
        for criteria in self.data.get('essentialRequirements'):
            if 'criteria' not in criteria:
                return False
            if not criteria['criteria'].replace(' ', ''):
                return False
            if self.data.get('includeWeightingsEssential'):
                if 'weighting' not in criteria:
                    return False
                if not criteria.get('weighting', '').replace(' ', ''):
                    return False
                if int(criteria.get('weighting', '0')) == 0:
                    return False
                weightings += int(criteria.get('weighting', ''))
        if self.data.get('includeWeightingsEssential'):
            if weightings != 100:
                return False
        return True

    def validate_evaluation_criteria_nice_to_have(self):
        if not self.data.get('niceToHaveRequirements'):
            return False

        self.data['niceToHaveRequirements'] = self.remove_empty_criteria(
            self.data.get('niceToHaveRequirements'),
            self.data.get('includeWeightingsNiceToHave')
        )

        weightings = 0
        for criteria in self.data.get('niceToHaveRequirements'):
            if self.data.get('includeWeightingsNiceToHave'):
                if (
                    (
                        criteria['criteria'].replace(' ', '') and
                        not criteria.get('weighting', '').replace(' ', '')
                    ) or (
                        not criteria['criteria'].replace(' ', '') and
                        criteria.get('weighting', '').replace(' ', '')
                    )
                ):
                    return False

                if criteria.get('weighting', '').replace(' ', ''):
                    if int(criteria.get('weighting', '')) == 0:
                        return False
                    else:
                        weightings += int(criteria.get('weighting', ''))

        if self.data.get('includeWeightingsNiceToHave'):
            if weightings and weightings != 100:
                return False
        return True

    def validate_contact_number(self):
        if not self.data.get('contactNumber', '').replace(' ', ''):
            return False
        return True

    def validate_seller_category(self):
        if (
            self.data.get('sellerCategory', '').replace(' ', '') and
            not domain_service.get_by_name_or_id(int(self.data.get('sellerCategory')))
        ):
            return False
        return True

    def validate_open_to(self):
        if (
            self.validate_seller_category() and
            self.data.get('openTo') not in ['all', 'selected']
        ):
            return False
        return True

    def validate_sellers(self):
        if (
            self.validate_seller_category() and
            self.validate_open_to() and
            self.data.get('openTo') in ['selected'] and
            (
                not self.data.get('sellers') or
                len(self.data.get('sellers')) == 0
            )
        ):
            return False

        for supplier_code in self.data.get('sellers', []):
            supplier = suppliers.get_supplier_by_code(int(supplier_code))
            if not supplier:
                return False

        return True

    def validate_number_of_suppliers(self):
        if not self.data.get('numberOfSuppliers', '').replace(' ', ''):
            return False
        if (
            int(self.data.get('numberOfSuppliers')) <= 0 or
            int(self.data.get('numberOfSuppliers')) > 100
        ):
            return False
        return True

    def validate_required(self):
        errors = []
        if not self.validate_title():
            errors.append('You must add a title')
        if not self.validate_organisation():
            errors.append('You must add the name of your department, agency or organisation')
        if not self.validate_summary():
            errors.append('You must add what the specialist will do')
        if not self.validate_location():
            errors.append('You must select a valid location of where the work can be done')
        if not self.validate_seller_category():
            errors.append('Invalid seller category/domain')
        if not self.validate_open_to():
            errors.append('Invalid openTo value')
        if not self.validate_sellers():
            errors.append('You must select some sellers')
        if not self.validate_response_formats():
            errors.append('Invalid response formats choice')
        if not self.validate_number_of_suppliers():
            errors.append('Invalid number of suppliers')
        if not self.validate_preferred_format_for_rates():
            errors.append('You must add background information')
        if not self.validate_security_clearance():
            errors.append('You must add security clearance details')
        if not self.validate_security_clearance_obtain():
            errors.append('You must select ability to obtain security clearance')
        if not self.validate_security_clearance_current():
            errors.append('You must select current security clearance')
        if not self.validate_security_clearance_other():
            errors.append('You must add other security clearance details')
        if not self.validate_start_date():
            errors.append('You must add an estimated start date')
        if not self.validate_contract_length():
            errors.append('You must add contract length')
        if not self.validate_evaluation_criteria_essential():
            errors.append(
                'You must not have any empty essential criteria, any empty weightings, \
                all weightings must be greater than 0, \
                and add up to 100'
            )
        if not self.validate_evaluation_criteria_nice_to_have():
            errors.append(
                'You must not have any empty desirable criteria, any empty weightings, \
                all weightings must be greater than 0, \
                and add up to 100'
            )
        if not self.validate_closed_at():
            errors.append('The closing date must be at least 2 days into the future or not more than one year long')
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
                {'name': 'summary', 'type': basestring},
                {'name': 'location', 'type': list},
                {'name': 'attachments', 'type': list},
                {'name': 'contactNumber', 'type': basestring},
                {'name': 'internalReference', 'type': basestring},
                {'name': 'includeWeightingsEssential', 'type': bool},
                {'name': 'essentialRequirements', 'type': list},
                {'name': 'includeWeightingsNiceToHave', 'type': bool},
                {'name': 'niceToHaveRequirements', 'type': list},
                {'name': 'numberOfSuppliers', 'type': basestring},
                {'name': 'evaluationType', 'type': list},
                {'name': 'preferredFormatForRates', 'type': basestring},
                {'name': 'maxRate', 'type': basestring},
                {'name': 'budgetRange', 'type': basestring},
                {'name': 'securityClearance', 'type': basestring},
                {'name': 'industryBriefing', 'type': basestring},
                {'name': 'securityClearanceObtain', 'type': basestring},
                {'name': 'securityClearanceCurrent', 'type': basestring},
                {'name': 'securityClearanceOther', 'type': basestring},
                {'name': 'sellerCategory', 'type': basestring},
                {'name': 'openTo', 'type': basestring},
                {'name': 'sellers', 'type': dict},
                {'name': 'startDate', 'type': basestring},
                {'name': 'contractLength', 'type': basestring},
                {'name': 'contractExtensions', 'type': basestring},
                {'name': 'areaOfExpertise', 'type': basestring},
                {'name': 'closedAt', 'type': basestring},
                {'name': 'publish', 'type': bool},
                {'name': 'comprehensiveTerms', 'type': bool}
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
