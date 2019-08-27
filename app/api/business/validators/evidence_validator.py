import pendulum
from app.api.services import (
    domain_service,
    evidence_service,
    domain_criteria_service,
    key_values_service
)
from app.api.business.domain_criteria import DomainCriteria


class EvidenceDataValidator(object):
    def __init__(self, data, evidence=None):
        self.data = data
        self.evidence = evidence
        self.max_criteria = 2
        if self.evidence:
            self.domain = domain_service.get_by_name_or_id(evidence.domain.id)
            self.domain_criteria = domain_criteria_service.get_criteria_by_domain_id(evidence.domain.id)

        self.criteria_enforcement_cutoff_date = None
        key_value = key_values_service.get_by_key('criteria_enforcement_cutoff_date')
        if key_value:
            self.criteria_enforcement_cutoff_date = (
                pendulum.parse(key_value['data']['value'], tz='Australia/Canberra').date()
            )

    def get_criteria_needed(self):
        criteria_needed = self.domain.criteria_needed
        if self.validate_max_rate():
            domain_criteria = DomainCriteria(domain_id=self.domain.id, rate=self.data['maxDailyRate'])
            criteria_needed = domain_criteria.get_criteria_needed()
        return criteria_needed

    def validate_max_rate(self):
        if 'maxDailyRate' not in self.data:
            return False
        try:
            if not int(self.data['maxDailyRate']) > 0:
                return False
        except Exception:
            return False
        return True

    def validate_domain(self):
        return True if (hasattr(self, 'domain') and self.domain) else False

    def validate_criteria(self):
        if 'criteria' not in self.data:
            return False
        if not len(self.data['criteria']) > 0:
            return False
        if len(self.data['criteria']) < self.get_criteria_needed():
            return False
        if len(self.data['criteria']) > self.get_criteria_needed() + self.max_criteria:
            if self.evidence.created_at.date() > self.criteria_enforcement_cutoff_date:
                return False
        valid_criteria_ids = [x.id for x in self.domain_criteria]
        for criteria_id in self.data['criteria']:
            if criteria_id not in valid_criteria_ids:
                return False
        return True

    def validate_evidence_dates(self):
        if 'evidence' not in self.data:
            return False
        used_criteria_ids = self.data['evidence'].keys()
        for criteria_id in used_criteria_ids:
            if 'startDate' not in self.data['evidence'][criteria_id]:
                return False
            if 'endDate' not in self.data['evidence'][criteria_id]:
                return False
            if not self.data['evidence'][criteria_id]['startDate'].replace(' ', ''):
                return False
            if not self.data['evidence'][criteria_id]['endDate'].replace(' ', ''):
                return False
        return True

    def validate_evidence_client(self):
        if 'evidence' not in self.data:
            return False
        used_criteria_ids = self.data['evidence'].keys()
        for criteria_id in used_criteria_ids:
            if 'client' not in self.data['evidence'][criteria_id]:
                return False
            if not self.data['evidence'][criteria_id]['client'].replace(' ', ''):
                return False
        return True

    def validate_evidence_background(self):
        if 'evidence' not in self.data:
            return False
        used_criteria_ids = self.data['evidence'].keys()
        for criteria_id in used_criteria_ids:
            if 'background' not in self.data['evidence'][criteria_id]:
                return False
            if not self.data['evidence'][criteria_id]['background'].replace(' ', ''):
                return False
        return True

    def validate_evidence_responses(self):
        if 'evidence' not in self.data:
            return False
        valid_criteria_ids = [x.id for x in self.domain_criteria]
        used_criteria_ids = self.data['evidence'].keys()
        for criteria_id in used_criteria_ids:
            if int(criteria_id) not in valid_criteria_ids:
                return False
            if 'response' not in self.data['evidence'][criteria_id]:
                return False
            if not self.data['evidence'][criteria_id]['response'].replace(' ', ''):
                return False
        if len(self.data['evidence'].keys()) < self.get_criteria_needed():
            return False
        if len(self.data['evidence'].keys()) > self.get_criteria_needed() + self.max_criteria:
            if self.evidence.created_at.date() > self.criteria_enforcement_cutoff_date:
                return False
        return True

    def validate_evidence_responses_have_changed_since_previous(self):
        if not self.validate_evidence_responses():
            return True
        valid = True
        previous_evidence = evidence_service.get_previous_submitted_evidence_for_supplier_and_domain(
            self.evidence.id,
            self.evidence.domain_id,
            self.evidence.supplier_code
        )
        if previous_evidence and previous_evidence.status == 'assessed':
            return True
        if (
            previous_evidence and
            'maxDailyRate' in previous_evidence.data and
            'maxDailyRate' in self.data and
            previous_evidence.data['maxDailyRate'] != self.data['maxDailyRate']
        ):
            return True
        if previous_evidence and 'evidence' in previous_evidence.data:
            changed = False
            for criteria_id in self.data['evidence'].keys():
                if (str(criteria_id) in previous_evidence.data['evidence']):
                    if (
                        'response' in previous_evidence.data['evidence'][criteria_id] and
                        'response' in self.data['evidence'][criteria_id] and
                        previous_evidence.data['evidence'][criteria_id]['response'] !=
                        self.data['evidence'][criteria_id]['response']
                    ):
                        changed = True
                else:
                    changed = True
            if not changed:
                valid = False
        return valid

    def validate_required(self):
        errors = []
        if not self.validate_max_rate():
            errors.append('You must add a max rate and it must be greater than zero')
        if not self.validate_domain():
            errors.append('The domain id associated with this evidence is invalid')
        if not self.validate_criteria():
            errors.append('You must select which criteria you are responding to')
        if not self.validate_evidence_dates():
            errors.append('You must provide dates in your evidence and the from date must be before the to date')
        if not self.validate_evidence_client():
            errors.append('You must add a client to your evidence')
        if not self.validate_evidence_background():
            errors.append('You must add a background to your evidence')
        if not self.validate_evidence_responses():
            errors.append('You must respond to all selected criteria')
        if not self.validate_evidence_responses_have_changed_since_previous():
            errors.append(
                'Please make sure you make the appropriate changes (based on the assessor \
                feedback you received) before you re-submit for assessment. Refresh this page to make these changes.'
            )
        return errors

    def field_whitelist(self, whitelist, data):
        violations = []
        whitelisted_keys = [key['name'] for key in whitelist]
        keys = data.keys()
        for key in keys:
            if key not in whitelisted_keys:
                violations.append('Unexpected field "%s"' % key)

        for key in whitelist:
            if key['name'] in keys and not isinstance(data.get(key['name'], None), key['type']):
                violations.append(
                    'Field "%s" is invalid, unexpected type. Got %s expected %s'
                    % (key['name'], data.get(key['name'], None), key['type'])
                )
        return violations

    def validate(self, publish=False):
        errors = []

        try:
            if publish:
                errors = errors + self.validate_required()

            # allowed fields and types
            whitelist = [
                {'name': 'id', 'type': int},
                {'name': 'domainId', 'type': int},
                {'name': 'maxDailyRate', 'type': int},
                {'name': 'criteria', 'type': list},
                {'name': 'evidence', 'type': dict},
                {'name': 'publish', 'type': bool}
            ]
            errors = errors + self.field_whitelist(whitelist, self.data)

            # allowed fields in the evidence
            used_criteria_ids = self.data['criteria']
            whitelist_criteria_ids = [
                {'name': str(x), 'type': dict} for x in self.data['criteria']
            ]
            errors = errors + self.field_whitelist(whitelist_criteria_ids, self.data['evidence'])

            # allowed fields and types inside each response in the evidence dict
            whitelist_evidence = [
                {'name': 'client', 'type': basestring},
                {'name': 'background', 'type': basestring},
                {'name': 'response', 'type': basestring},
                {'name': 'refereeName', 'type': basestring},
                {'name': 'refereeNumber', 'type': basestring},
                {'name': 'startDate', 'type': basestring},
                {'name': 'endDate', 'type': basestring},
                {'name': 'sameAsFirst', 'type': bool}
            ]
            for criteria_id in self.data['evidence'].keys():
                errors = errors + self.field_whitelist(whitelist_evidence, self.data['evidence'][criteria_id])

        except Exception as e:
            errors.append(e.message)

        return errors
