from app.api.business.domain_criteria import DomainCriteria
from app.api.business.errors import DomainCriteriaInvalidDomainException, DomainCriteriaInvalidRateException


def test_domain_criteria_success(domains):
    for domain in domains:
        domain_criteria = DomainCriteria(
            domain_id=domain.id,
            rate=1
        )
        assert domain_criteria.get_criteria_needed() == domain.criteria_needed

        domain_criteria = DomainCriteria(
            domain_id=domain.id,
            rate=domain.price_maximum + 10
        )
        assert domain_criteria.get_criteria_needed() == domain.criteria_needed + 1


def test_domain_criteria_fail_invalid_domain(domains):
    try:
        domain_criteria = DomainCriteria(
            domain_id=999,
            rate=1
        )
        assert False
    except DomainCriteriaInvalidDomainException as e:
        assert True


def test_domain_criteria_fail_invalid_rate(domains):
    try:
        domain_criteria = DomainCriteria(
            domain_id=1,
            rate='x'
        )
        assert False
    except DomainCriteriaInvalidRateException as e:
        assert True
