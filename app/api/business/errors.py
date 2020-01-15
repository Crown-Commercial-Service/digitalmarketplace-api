class BriefError(Exception):
    pass


class NotFoundError(Exception):
    pass


class DeletedError(Exception):
    pass


class UnauthorisedError(Exception):
    pass


class ValidationError(Exception):
    pass


class TeamError(Exception):
    pass


class DomainCriteriaInvalidDomainException(Exception):
    """Raised when an invalid domain id is passed to DomainCriteria"""
    pass


class DomainCriteriaInvalidRateException(Exception):
    """Raised when an invalid rate is passed to DomainCriteria"""
    pass


class DomainApprovalException(Exception):
    """Raised when the domain approval outcome fails to apply."""
    pass
