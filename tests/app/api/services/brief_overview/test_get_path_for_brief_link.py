import pytest

from app.api.services import brief_overview_service
from conftest import outcome_brief, outcome_lot, specialist_brief, specialist_lot


def test_correct_path_returned_for_title(outcome_brief):
    path = brief_overview_service.get_path_for_brief_link(outcome_brief, brief_overview_service.TITLE_TEXT)
    assert path == ('/buyers/frameworks/{}/requirements/{}/{}/edit/title/title'
                    .format(outcome_brief.framework.slug, outcome_brief.lot.slug, outcome_brief.id))


def test_correct_path_returned_for_role(specialist_brief):
    path = brief_overview_service.get_path_for_brief_link(specialist_brief, brief_overview_service.ROLE_TEXT)
    assert path == ('/buyers/frameworks/{}/requirements/{}/{}/edit/role/title'
                    .format(specialist_brief.framework.slug, specialist_brief.lot.slug, specialist_brief.id))


@pytest.mark.parametrize('brief, lot', [(outcome_brief, outcome_lot), (specialist_brief, specialist_lot)])
def test_correct_path_returned_for_location(brief, framework, lot):
    test_brief = brief(framework, lot())
    path = brief_overview_service.get_path_for_brief_link(test_brief, brief_overview_service.LOCATION_TEXT)
    assert path == ('/buyers/frameworks/{}/requirements/{}/{}/edit/location/location'
                    .format(test_brief.framework.slug, test_brief.lot.slug, test_brief.id))


@pytest.mark.parametrize('brief, lot', [(outcome_brief, outcome_lot), (specialist_brief, specialist_lot)])
def test_correct_path_returned_for_description_of_work(brief, framework, lot):
    test_brief = brief(framework, lot())
    path = brief_overview_service.get_path_for_brief_link(test_brief, brief_overview_service.DESCRIPTION_OF_WORK_TEXT)
    assert path == ('/buyers/frameworks/{}/requirements/{}/{}/description-of-work'
                    .format(test_brief.framework.slug, test_brief.lot.slug, test_brief.id))


@pytest.mark.parametrize('brief, lot', [(outcome_brief, outcome_lot), (specialist_brief, specialist_lot)])
def test_correct_path_returned_for_shortlist_and_evaluation(brief, framework, lot):
    test_brief = brief(framework, lot())
    path = brief_overview_service.get_path_for_brief_link(
        test_brief, brief_overview_service.SHORTLIST_AND_EVALUATION_TEXT)
    assert path == ('/buyers/frameworks/{}/requirements/{}/{}/shortlist-and-evaluation-process'
                    .format(test_brief.framework.slug, test_brief.lot.slug, test_brief.id))


@pytest.mark.parametrize('brief, lot', [(outcome_brief, outcome_lot), (specialist_brief, specialist_lot)])
def test_correct_path_returned_for_brief_window(brief, framework, lot):
    test_brief = brief(framework, lot())
    path = brief_overview_service.get_path_for_brief_link(test_brief, brief_overview_service.BRIEF_WINDOW_TEXT)
    assert path == ('/buyers/frameworks/{}/requirements/{}/{}/edit/how-long-your-brief-will-be-open/'
                    'requirementsLength'.format(test_brief.framework.slug, test_brief.lot.slug, test_brief.id))


@pytest.mark.parametrize('brief, lot', [(outcome_brief, outcome_lot), (specialist_brief, specialist_lot)])
def test_correct_path_returned_for_question_and_answer_session(brief, framework, lot):
    test_brief = brief(framework, lot())
    path = brief_overview_service.get_path_for_brief_link(test_brief, brief_overview_service.QUESTION_AND_ANSWER_TEXT)
    assert path == ('/buyers/frameworks/{}/requirements/{}/{}/question-and-answer-session-details'
                    .format(test_brief.framework.slug, test_brief.lot.slug, test_brief.id))


@pytest.mark.parametrize('brief, lot', [(outcome_brief, outcome_lot), (specialist_brief, specialist_lot)])
def test_correct_path_returned_for_who_can_respond(brief, framework, lot):
    test_brief = brief(framework, lot())
    path = brief_overview_service.get_path_for_brief_link(test_brief, brief_overview_service.WHO_CAN_RESPOND_TEXT)
    assert path == ('/buyers/frameworks/{}/requirements/{}/{}/edit/who-can-respond/specifySeller'
                    .format(test_brief.framework.slug, test_brief.lot.slug, test_brief.id))


@pytest.mark.parametrize('brief, lot', [(outcome_brief, outcome_lot), (specialist_brief, specialist_lot)])
def test_correct_path_returned_for_review_and_publish(brief, framework, lot):
    test_brief = brief(framework, lot())
    path = brief_overview_service.get_path_for_brief_link(test_brief, brief_overview_service.PUBLISH_TEXT)
    assert path == ('/buyers/frameworks/{}/requirements/{}/{}/publish'
                    .format(test_brief.framework.slug, test_brief.lot.slug, test_brief.id))


@pytest.mark.parametrize('brief, lot', [(outcome_brief, outcome_lot), (specialist_brief, specialist_lot)])
def test_correct_path_returned_for_answer_a_question(brief, framework, lot):
    test_brief = brief(framework, lot())
    path = brief_overview_service.get_path_for_brief_link(test_brief, brief_overview_service.ANSWER_QUESTION_TEXT)
    assert path == ('/buyers/frameworks/{}/requirements/{}/{}/supplier-questions/answer-question'
                    .format(test_brief.framework.slug, test_brief.lot.slug, test_brief.id))


@pytest.mark.parametrize('brief, lot', [(outcome_brief, outcome_lot), (specialist_brief, specialist_lot)])
def test_correct_path_returned_for_view_responses(brief, framework, lot):
    test_brief = brief(framework, lot())
    path = brief_overview_service.get_path_for_brief_link(test_brief, brief_overview_service.VIEW_RESPONSES_TEXT)
    assert path == ('/buyers/frameworks/{}/requirements/{}/{}/responses'
                    .format(test_brief.framework.slug, test_brief.lot.slug, test_brief.id))


@pytest.mark.parametrize('brief, lot', [(outcome_brief, outcome_lot), (specialist_brief, specialist_lot)])
def test_correct_path_returned_for_evaluation_template(brief, framework, lot):
    test_brief = brief(framework, lot())
    path = brief_overview_service.get_path_for_brief_link(test_brief, brief_overview_service.EVALUATION_TEMPLATE_TEXT)
    assert path == '/static/media/documents/Scoring_Template.xlsx'


@pytest.mark.parametrize('brief, lot', [(outcome_brief, outcome_lot), (specialist_brief, specialist_lot)])
def test_correct_path_returned_for_start_work_order(brief, framework, lot):
    test_brief = brief(framework, lot())
    path = brief_overview_service.get_path_for_brief_link(test_brief, brief_overview_service.START_WORK_ORDER_TEXT)
    assert path == ('/buyers/frameworks/{}/requirements/{}/{}/work-orders/create'
                    .format(test_brief.framework.slug, test_brief.lot.slug, test_brief.id))


@pytest.mark.parametrize('brief, lot', [(outcome_brief, outcome_lot), (specialist_brief, specialist_lot)])
def test_correct_path_returned_for_edit_work_order(brief, framework, lot, work_order):
    test_brief = brief(framework, lot())
    test_brief.work_order = work_order
    path = brief_overview_service.get_path_for_brief_link(test_brief, brief_overview_service.EDIT_WORK_ORDER_TEXT)
    assert path == '/work-orders/{}'.format(test_brief.work_order.id)
