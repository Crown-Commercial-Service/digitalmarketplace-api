from app.brief_utils import check_training_method
from app.models import Brief, Lot


def test_when_own_preference_and_approach_not_set():
    brief_data = {
        'approachSelector': 'ownPreference'
    }
    lot = Lot(name='Training', one_service_limit=True)
    brief = Brief(lot=lot, data=brief_data)
    error = check_training_method(brief)
    assert error is not None
    assert error['trainingApproachOwn'] == 'answer_required'


def test_when_own_preference_and_approach_set_to_empty():
    brief_data = {
        'approachSelector': 'ownPreference',
        'trainingApproachOwn': ''
    }
    lot = Lot(name='Training', one_service_limit=True)
    brief = Brief(lot=lot, data=brief_data)
    error = check_training_method(brief)
    assert error is not None
    assert error['trainingApproachOwn'] == 'answer_required'


def test_when_own_preference_and_approach_is_set():
    brief_data = {
        'approachSelector': 'ownPreference',
        'trainingApproachOwn': 'test'
    }
    lot = Lot(name='Training', one_service_limit=True)
    brief = Brief(lot=lot, data=brief_data)
    error = check_training_method(brief)
    assert error is None
