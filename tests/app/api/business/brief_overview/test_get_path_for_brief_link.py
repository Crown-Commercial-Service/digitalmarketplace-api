import pytest

from app.api.business import brief_overview_business
from conftest import outcome_brief, outcome_lot, specialist_brief, specialist_lot


@pytest.mark.parametrize('brief, lot', [(outcome_brief, outcome_lot), (specialist_brief, specialist_lot)])
def test_correct_path_returned(brief, framework, lot, work_order):
    test_brief = brief(framework, lot())
    test_brief.work_order = work_order
    path = brief_overview_business.get_path_for_brief_link(test_brief, '{path}/random/string/{work_order_id}/foo/bar')
    assert path == ((
        '/buyers/frameworks/{framework_slug}/requirements/'
        '{lot_slug}/{work_order_id}/random/string/{work_order_id}/foo/bar')
        .format(framework_slug=test_brief.framework.slug,
                lot_slug=test_brief.lot.slug,
                work_order_id=work_order.id))


def test_correct_path_returned_for_title(outcome_brief):
    path = brief_overview_business.get_path_for_brief_link(outcome_brief, '{path}/edit/title/title')
    assert path == ('/buyers/frameworks/{}/requirements/{}/{}/edit/title/title'
                    .format(outcome_brief.framework.slug, outcome_brief.lot.slug, outcome_brief.id))


def test_correct_path_returned_for_role(specialist_brief):
    path = brief_overview_business.get_path_for_brief_link(specialist_brief, '{path}/edit/role/title')
    assert path == ('/buyers/frameworks/{}/requirements/{}/{}/edit/role/title'
                    .format(specialist_brief.framework.slug, specialist_brief.lot.slug, specialist_brief.id))


@pytest.mark.parametrize('brief, lot', [(outcome_brief, outcome_lot), (specialist_brief, specialist_lot)])
def test_correct_path_returned_for_location(brief, framework, lot):
    test_brief = brief(framework, lot())
    path = brief_overview_business.get_path_for_brief_link(test_brief, '{path}/edit/location/location')
    assert path == ('/buyers/frameworks/{}/requirements/{}/{}/edit/location/location'
                    .format(test_brief.framework.slug, test_brief.lot.slug, test_brief.id))


@pytest.mark.parametrize('brief, lot', [(outcome_brief, outcome_lot), (specialist_brief, specialist_lot)])
def test_correct_path_returned_for_description_of_work(brief, framework, lot):
    test_brief = brief(framework, lot())
    path = brief_overview_business.get_path_for_brief_link(test_brief, '{path}/description-of-work')
    assert path == ('/buyers/frameworks/{}/requirements/{}/{}/description-of-work'
                    .format(test_brief.framework.slug, test_brief.lot.slug, test_brief.id))


@pytest.mark.parametrize('brief, lot', [(outcome_brief, outcome_lot), (specialist_brief, specialist_lot)])
def test_correct_path_returned_for_shortlist_and_evaluation(brief, framework, lot):
    test_brief = brief(framework, lot())
    path = brief_overview_business.get_path_for_brief_link(
        test_brief, '{path}/shortlist-and-evaluation-process')
    assert path == ('/buyers/frameworks/{}/requirements/{}/{}/shortlist-and-evaluation-process'
                    .format(test_brief.framework.slug, test_brief.lot.slug, test_brief.id))


@pytest.mark.parametrize('brief, lot', [(outcome_brief, outcome_lot), (specialist_brief, specialist_lot)])
def test_correct_path_returned_for_brief_window(brief, framework, lot):
    test_brief = brief(framework, lot())
    path = brief_overview_business \
        .get_path_for_brief_link(test_brief, '{path}/edit/how-long-your-brief-will-be-open/requirementsLength')
    assert path == (('/buyers/frameworks/{}/requirements/{}/{}/'
                     'edit/how-long-your-brief-will-be-open/requirementsLength')
                    .format(test_brief.framework.slug, test_brief.lot.slug, test_brief.id))


@pytest.mark.parametrize('brief, lot', [(outcome_brief, outcome_lot), (specialist_brief, specialist_lot)])
def test_correct_path_returned_for_question_and_answer_session(brief, framework, lot):
    test_brief = brief(framework, lot())
    path = brief_overview_business.get_path_for_brief_link(test_brief, '{path}/question-and-answer-session-details')
    assert path == ('/buyers/frameworks/{}/requirements/{}/{}/question-and-answer-session-details'
                    .format(test_brief.framework.slug, test_brief.lot.slug, test_brief.id))


@pytest.mark.parametrize('brief, lot', [(outcome_brief, outcome_lot), (specialist_brief, specialist_lot)])
def test_correct_path_returned_for_who_can_respond(brief, framework, lot):
    test_brief = brief(framework, lot())
    path = brief_overview_business.get_path_for_brief_link(test_brief, '{path}/edit/who-can-respond/specifySeller')
    assert path == ('/buyers/frameworks/{}/requirements/{}/{}/edit/who-can-respond/specifySeller'
                    .format(test_brief.framework.slug, test_brief.lot.slug, test_brief.id))


@pytest.mark.parametrize('brief, lot', [(outcome_brief, outcome_lot), (specialist_brief, specialist_lot)])
def test_correct_path_returned_for_review_and_publish(brief, framework, lot):
    test_brief = brief(framework, lot())
    path = brief_overview_business.get_path_for_brief_link(test_brief, '{path}/publish')
    assert path == ('/buyers/frameworks/{}/requirements/{}/{}/publish'
                    .format(test_brief.framework.slug, test_brief.lot.slug, test_brief.id))


@pytest.mark.parametrize('brief, lot', [(outcome_brief, outcome_lot), (specialist_brief, specialist_lot)])
def test_correct_path_returned_for_answer_a_question(brief, framework, lot):
    test_brief = brief(framework, lot())
    path = brief_overview_business.get_path_for_brief_link(test_brief, '{path}/supplier-questions/answer-question')
    assert path == ('/buyers/frameworks/{}/requirements/{}/{}/supplier-questions/answer-question'
                    .format(test_brief.framework.slug, test_brief.lot.slug, test_brief.id))


@pytest.mark.parametrize('brief, lot', [(outcome_brief, outcome_lot), (specialist_brief, specialist_lot)])
def test_correct_path_returned_for_view_responses(brief, framework, lot):
    test_brief = brief(framework, lot())
    path = brief_overview_business.get_path_for_brief_link(test_brief, '/2/brief/{brief_id}/download-responses')
    assert path == ('/2/brief/{}/download-responses'.format(test_brief.id))


@pytest.mark.parametrize('brief, lot', [(outcome_brief, outcome_lot), (specialist_brief, specialist_lot)])
def test_correct_path_returned_for_evaluation_template(brief, framework, lot):
    test_brief = brief(framework, lot())
    path = brief_overview_business.get_path_for_brief_link(test_brief, '/static/media/documents/Scoring_Template.xlsx')
    assert path == '/static/media/documents/Scoring_Template.xlsx'


@pytest.mark.parametrize('brief, lot', [(outcome_brief, outcome_lot), (specialist_brief, specialist_lot)])
def test_correct_path_returned_for_start_work_order(brief, framework, lot):
    test_brief = brief(framework, lot())
    path = brief_overview_business.get_path_for_brief_link(test_brief, '{path}/work-orders/create')
    assert path == ('/buyers/frameworks/{}/requirements/{}/{}/work-orders/create'
                    .format(test_brief.framework.slug, test_brief.lot.slug, test_brief.id))


@pytest.mark.parametrize('brief, lot', [(outcome_brief, outcome_lot), (specialist_brief, specialist_lot)])
def test_correct_path_returned_for_edit_work_order(brief, framework, lot, work_order):
    test_brief = brief(framework, lot())
    test_brief.work_order = work_order
    path = brief_overview_business.get_path_for_brief_link(test_brief, '/work-orders/{work_order_id}')
    assert path == '/work-orders/{}'.format(test_brief.work_order.id)
