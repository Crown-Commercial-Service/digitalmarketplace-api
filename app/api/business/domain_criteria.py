from app.api.services import domain_service
from app.api.business.errors import DomainCriteriaInvalidDomainException, DomainCriteriaInvalidRateException


class DomainCriteria(object):
    def __init__(self, domain_id=None, rate=None):
        self.domain = domain_service.find(id=domain_id).one_or_none()
        if not self.domain:
            raise DomainCriteriaInvalidDomainException('Invalid domain id')
        if not rate or not str(rate).isdigit():
            raise DomainCriteriaInvalidRateException('Invalid rate')
        self.rate = int(rate)

    def get_criteria_needed(self):
        criteria_needed = self.domain.criteria_needed
        if self.rate > self.domain.price_maximum:
            criteria_needed += 1
        return criteria_needed
