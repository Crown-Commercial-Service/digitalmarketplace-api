from app.api.business.validators import ApplicationValidator
from app.models import Application


def test_can_get_errors_with_empty_string():
    application = Application(
        data={
            'disclosures': {
                'structual_changes': '',
                'investigations': '',
                'legal_proceedings': '',
                'insurance_claims': '',
                'conflicts_of_interest': '',
                'other_circumstances': ''
            }
        }
    )
    errors = ApplicationValidator(application).validate_disclosures()

    assert len(errors) == 6


def test_can_get_errors_with_yes():
    application = Application(
        data={
            'disclosures': {
                'structual_changes': 'yes',
                'investigations': 'yes',
                'legal_proceedings': 'yes',
                'insurance_claims': 'yes',
                'conflicts_of_interest': 'yes',
                'other_circumstances': 'yes'
            }
        }
    )
    errors = ApplicationValidator(application).validate_disclosures()
    assert len([e for e in errors if e.get('field').endswith('details')]) == 6
    assert len(errors) == 6
