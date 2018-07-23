from app.brief_utils import check_lds
from app.models import Brief, Lot


def test_when_what_training_and_details_not_set():
    brief_data = {
        'whatTraining': ['other', 'content design', 'user research']
    }
    lot = Lot(name='Training', one_service_limit=True)
    brief = Brief(lot=lot, data=brief_data)

    required_fields = [
        'trainingDetailType',
        'trainingDetailCover',
        'ldsContentDesignProposalOrLds',
        'ldsUserResearchProposalOrLds']

    errors = check_lds(brief, required_fields)

    assert errors is not []
    assert len(errors) == len(required_fields)
    for c in range(len(errors)):
        error = errors[c]
        required_field = required_fields[c]
        assert error[required_field] == 'answer_required'


def test_when_what_training_and_details_is_set():
    brief_data = {
        'whatTraining': ['other', 'content design', 'user research'],
        'ldsContentDesignProposalOrLds': 'ldsUnits',
        'ldsUserResearchProposalOrLds': 'specify',
        'trainingDetailType': 'foo',
        'trainingDetailCover': 'bar'
    }
    lot = Lot(name='Training', one_service_limit=True)
    brief = Brief(lot=lot, data=brief_data)

    required_fields = [
        'trainingDetailType',
        'trainingDetailCover',
        'ldsContentDesignProposalOrLds',
        'ldsContentDesignUnits',
        'ldsUserResearchProposalOrLds',
        'ldsUserResearchTrainingNeeds']

    errors = check_lds(brief, required_fields)

    assert errors is not []
    assert len(errors) == 2
    assert errors[0]['ldsContentDesignUnits'] == 'answer_required'
    assert errors[1]['ldsUserResearchTrainingNeeds'] == 'answer_required'


def test_when_what_training_and_details_is_all_set():
    brief_data = {
        'whatTraining': ['other', 'content design', 'user research'],
        'ldsContentDesignProposalOrLds': 'ldsUnits',
        'ldsContentDesignUnits': ['anything'],
        'ldsUserResearchProposalOrLds': 'specify',
        'ldsUserResearchTrainingNeeds': 'foo',
        'trainingDetailType': 'foo',
        'trainingDetailCover': 'bar'
    }
    lot = Lot(name='Training', one_service_limit=True)
    brief = Brief(lot=lot, data=brief_data)

    required_fields = [
        'trainingDetailType',
        'trainingDetailCover',
        'ldsContentDesignProposalOrLds',
        'ldsContentDesignUnits',
        'ldsUserResearchProposalOrLds',
        'ldsUserResearchTrainingNeeds']

    errors = check_lds(brief, required_fields)

    assert len(errors) == 0
