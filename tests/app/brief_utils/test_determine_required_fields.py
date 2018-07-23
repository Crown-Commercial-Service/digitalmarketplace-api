import pytest
from mock import patch
from app.brief_utils import determine_required_fields
from app.models import Brief, Lot, Framework


def test_should_return_required_fields_when_not_training():
    brief_data = {
        'whatTraining': ['other', 'content design', 'user research']
    }
    lot = Lot(slug='training', name='Not Training', one_service_limit=True)
    brief = Brief(lot=lot, data=brief_data)

    required_fields = [
        'trainingDetailType',
        'trainingDetailCover',
        'ldsContentDesignProposalOrLds',
        'ldsUserResearchProposalOrLds']

    assert required_fields == determine_required_fields(brief, required_fields=required_fields)


@pytest.mark.parametrize('brief_data,expected_result', [
    (
        {
            'whatTraining': ['other']
        },
        ['trainingDetailType', 'trainingDetailCover']
    ), (
        {'whatTraining': ['digital foundations']},
        ['ldsDigitalFoundationProposalOrLds']
    ), (
        {
            'whatTraining': ['digital foundations'],
            'ldsDigitalFoundationProposalOrLds': 'ldsUnits'
        },
        ['ldsDigitalFoundationUnits']
    ), (
        {
            'whatTraining': ['digital foundations'],
            'ldsDigitalFoundationProposalOrLds': 'specify'
        },
        ['ldsDigitalFoundationTrainingNeeds']
    )
])
def test_should_return_required_fields_when_lds(brief_data, expected_result):
    lot = Lot(name='Training', one_service_limit=True)
    with patch(
        'app.brief_utils.get_required_fields',
            return_value=[
                'ldsDigitalFoundationProposalOrLds',
                'ldsDigitalFoundationUnits',
                'ldsDigitalFoundationTrainingNeeds',
                'trainingDetailType',
                'trainingDetailCover'
            ]) as get_required_fields_function:
        brief = Brief(lot=lot, data=brief_data)

        required_fields = determine_required_fields(brief)

        assert get_required_fields_function.called
        for _ in expected_result:
            assert _ in required_fields


@pytest.mark.parametrize('brief_data,section_fields,expected_result', [
    pytest.param(  # not in section
        {
            'whatTraining': ['other']
        },
        ['trainingDetailType'],
        ['trainingDetailType', 'trainingDetailCover'],
        marks=pytest.mark.xfail
    ), (
        {
            'whatTraining': ['other']
        },
        [],
        []
    ), (
        {
            'whatTraining': ['other']
        },
        ['trainingDetailType'],
        ['trainingDetailType']
    ), (
        {'whatTraining': ['digital foundations']},
        ['ldsDigitalFoundationProposalOrLds'],
        ['ldsDigitalFoundationProposalOrLds']
    ), (
        {
            'whatTraining': ['digital foundations'],
            'ldsDigitalFoundationProposalOrLds': 'ldsUnits'
        },
        ['ldsDigitalFoundationUnits'],
        ['ldsDigitalFoundationUnits']
    ), (
        {
            'whatTraining': ['digital foundations'],
            'ldsDigitalFoundationProposalOrLds': 'specify'
        },
        ['ldsDigitalFoundationTrainingNeeds'],
        ['ldsDigitalFoundationTrainingNeeds']
    ), pytest.param(  # not in section
        {
            'whatTraining': ['digital foundations'],
            'ldsDigitalFoundationProposalOrLds': 'specify'
        },
        ['ldsDigitalFoundationUnits'],
        ['ldsDigitalFoundationTrainingNeeds'],
        marks=pytest.mark.xfail
    )
])
def test_should_return_required_fields_when_field_in_section(brief_data, section_fields, expected_result):
    lot = Lot(name='Training', one_service_limit=True)
    brief = Brief(lot=lot, data=brief_data)

    required_fields = determine_required_fields(
        brief,
        enforce_required=False,
        section={'required': section_fields, 'optional': []})

    for _ in expected_result:
        assert _ in required_fields


@pytest.mark.parametrize('brief_data,expected_result', [
    pytest.param(
        {
            'whatTraining': ['other']
        },
        ['trainingDetailCover'],
        marks=pytest.mark.xfail
    ), (
        {
            'whatTraining': ['other']
        },
        ['trainingDetailType']
    ), (
        {'whatTraining': ['digital foundations']},
        ['ldsDigitalFoundationProposalOrLds']
    ), (
        {
            'whatTraining': ['digital foundations'],
            'ldsDigitalFoundationProposalOrLds': 'ldsUnits'
        },
        []
    ), (
        {
            'whatTraining': ['digital foundations'],
            'ldsDigitalFoundationProposalOrLds': 'specify'
        },
        ['ldsDigitalFoundationTrainingNeeds']
    )
])
def test_should_return_required_fields_when_in_passed_list(brief_data, expected_result):
    lot = Lot(name='Training', one_service_limit=True)
    brief = Brief(lot=lot, data=brief_data)
    pre_defined_required_fields = [
        'trainingDetailType',
        'ldsDigitalFoundationProposalOrLds',
        'ldsDigitalFoundationTrainingNeeds'
    ]
    required_fields = determine_required_fields(
        brief,
        enforce_required=False,
        required_fields=pre_defined_required_fields)

    for _ in expected_result:
        assert _ in required_fields
