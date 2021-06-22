import pytest

from app.api.business import brief_overview_business


def test_outcome_brief_correct_path_returned(outcome_brief, work_order):
    outcome_brief.work_order = work_order
    path = brief_overview_business.get_path_for_brief_link(
        outcome_brief,
        '{path}/random/string/{work_order_id}/foo/bar'
    )

    assert path == (
        '/buyers/frameworks/{framework_slug}/requirements/{lot_slug}/{work_order_id}'
        '/random/string/{work_order_id}/foo/bar'
        .format(
            framework_slug=outcome_brief.framework.slug,
            lot_slug=outcome_brief.lot.slug,
            work_order_id=outcome_brief.id
        )
    )


def test_specialist_brief_correct_path_returned(specialist_brief, work_order):
    specialist_brief.work_order = work_order
    path = brief_overview_business.get_path_for_brief_link(
        specialist_brief,
        '{path}/random/string/{work_order_id}/foo/bar'
    )

    assert path == (
        '/buyers/frameworks/{framework_slug}/requirements/{lot_slug}/{work_order_id}/'
        'random/string/{work_order_id}/foo/bar'
        .format(
            framework_slug=specialist_brief.framework.slug,
            lot_slug=specialist_brief.lot.slug,
            work_order_id=work_order.id
        )
    )


def test_correct_path_returned_for_title(outcome_brief):
    path = brief_overview_business.get_path_for_brief_link(outcome_brief, '{path}/edit/title/title')
    assert path == (
        '/buyers/frameworks/{}/requirements/{}/{}/edit/title/title'
        .format(
            outcome_brief.framework.slug,
            outcome_brief.lot.slug,
            outcome_brief.id
        )
    )


def test_correct_path_returned_for_role(specialist_brief):
    path = brief_overview_business.get_path_for_brief_link(specialist_brief, '{path}/edit/role/title')
    assert path == (
        '/buyers/frameworks/{}/requirements/{}/{}/edit/role/title'
        .format(
            specialist_brief.framework.slug,
            specialist_brief.lot.slug,
            specialist_brief.id
        )
    )


def test_outcome_brief_correct_path_returned_for_location(outcome_brief):
    path = brief_overview_business.get_path_for_brief_link(outcome_brief, '{path}/edit/location/location')
    assert path == (
        '/buyers/frameworks/{}/requirements/{}/{}/edit/location/location'
        .format(
            outcome_brief.framework.slug,
            outcome_brief.lot.slug,
            outcome_brief.id
        )
    )


def test_specialist_brief_correct_path_returned_for_location(specialist_brief):
    path = brief_overview_business.get_path_for_brief_link(specialist_brief, '{path}/edit/location/location')
    assert path == (
        '/buyers/frameworks/{}/requirements/{}/{}/edit/location/location'
        .format(
            specialist_brief.framework.slug,
            specialist_brief.lot.slug,
            specialist_brief.id
        )
    )


def test_outcome_brief_correct_path_returned_for_description_of_work(outcome_brief):
    path = brief_overview_business.get_path_for_brief_link(outcome_brief, '{path}/description-of-work')
    assert path == (
        '/buyers/frameworks/{}/requirements/{}/{}/description-of-work'
        .format(
            outcome_brief.framework.slug,
            outcome_brief.lot.slug,
            outcome_brief.id
        )
    )


def test_specialist_brief_correct_path_returned_for_description_of_work(specialist_brief):
    path = brief_overview_business.get_path_for_brief_link(specialist_brief, '{path}/description-of-work')
    assert path == (
        '/buyers/frameworks/{}/requirements/{}/{}/description-of-work'
        .format(
            specialist_brief.framework.slug,
            specialist_brief.lot.slug,
            specialist_brief.id
        )
    )


def test_outcome_brief_correct_path_returned_for_shortlist_and_evaluation(outcome_brief):
    path = brief_overview_business.get_path_for_brief_link(
        outcome_brief,
        '{path}/shortlist-and-evaluation-process'
    )

    assert path == (
        '/buyers/frameworks/{}/requirements/{}/{}/shortlist-and-evaluation-process'
        .format(
            outcome_brief.framework.slug,
            outcome_brief.lot.slug,
            outcome_brief.id
        )
    )


def test_specialist_brief_correct_path_returned_for_shortlist_and_evaluation(specialist_brief):
    path = brief_overview_business.get_path_for_brief_link(
        specialist_brief,
        '{path}/shortlist-and-evaluation-process'
    )

    assert path == (
        '/buyers/frameworks/{}/requirements/{}/{}/shortlist-and-evaluation-process'
        .format(
            specialist_brief.framework.slug,
            specialist_brief.lot.slug,
            specialist_brief.id
        )
    )


def test_outcome_brief_correct_path_returned_for_brief_window(outcome_brief):
    path = brief_overview_business.get_path_for_brief_link(
        outcome_brief,
        '{path}/edit/how-long-your-brief-will-be-open/requirementsLength'
    )

    assert path == (
        '/buyers/frameworks/{}/requirements/{}/{}/edit/how-long-your-brief-will-be-open/requirementsLength'
        .format(
            outcome_brief.framework.slug,
            outcome_brief.lot.slug,
            outcome_brief.id
        )
    )


def test_specialist_brief_correct_path_returned_for_brief_window(specialist_brief):
    path = brief_overview_business.get_path_for_brief_link(
        specialist_brief,
        '{path}/edit/how-long-your-brief-will-be-open/requirementsLength'
    )

    assert path == (
        '/buyers/frameworks/{}/requirements/{}/{}/edit/how-long-your-brief-will-be-open/requirementsLength'
        .format(
            specialist_brief.framework.slug,
            specialist_brief.lot.slug,
            specialist_brief.id
        )
    )


def test_outcome_brief_correct_path_returned_for_question_and_answer_session(outcome_brief):
    path = brief_overview_business.get_path_for_brief_link(
        outcome_brief,
        '{path}/question-and-answer-session-details'
    )

    assert path == (
        '/buyers/frameworks/{}/requirements/{}/{}/question-and-answer-session-details'
        .format(
            outcome_brief.framework.slug,
            outcome_brief.lot.slug,
            outcome_brief.id
        )
    )


def test_specialist_brief_correct_path_returned_for_question_and_answer_session(specialist_brief):
    path = brief_overview_business.get_path_for_brief_link(
        specialist_brief,
        '{path}/question-and-answer-session-details'
    )

    assert path == (
        '/buyers/frameworks/{}/requirements/{}/{}/question-and-answer-session-details'
        .format(
            specialist_brief.framework.slug,
            specialist_brief.lot.slug,
            specialist_brief.id
        )
    )


def test_outcome_brief_correct_path_returned_for_who_can_respond(outcome_brief):
    path = brief_overview_business.get_path_for_brief_link(
        outcome_brief,
        '{path}/edit/who-can-respond/specifySeller'
    )

    assert path == (
        '/buyers/frameworks/{}/requirements/{}/{}/edit/who-can-respond/specifySeller'
        .format(
            outcome_brief.framework.slug,
            outcome_brief.lot.slug,
            outcome_brief.id
        )
    )


def test_specialist_brief_outcome_brief_correct_path_returned_for_who_can_respond(specialist_brief):
    path = brief_overview_business.get_path_for_brief_link(
        specialist_brief,
        '{path}/edit/who-can-respond/specifySeller'
    )

    assert path == (
        '/buyers/frameworks/{}/requirements/{}/{}/edit/who-can-respond/specifySeller'
        .format(
            specialist_brief.framework.slug,
            specialist_brief.lot.slug,
            specialist_brief.id
        )
    )


def test_outcome_brief_correct_path_returned_for_review_and_publish(outcome_brief):
    path = brief_overview_business.get_path_for_brief_link(
        outcome_brief,
        '{path}/publish'
    )

    assert path == (
        '/buyers/frameworks/{}/requirements/{}/{}/publish'
        .format(
            outcome_brief.framework.slug,
            outcome_brief.lot.slug,
            outcome_brief.id
        )
    )


def test_specialist_brief_correct_path_returned_for_review_and_publish(specialist_brief):
    path = brief_overview_business.get_path_for_brief_link(
        specialist_brief,
        '{path}/publish'
    )

    assert path == (
        '/buyers/frameworks/{}/requirements/{}/{}/publish'
        .format(
            specialist_brief.framework.slug,
            specialist_brief.lot.slug,
            specialist_brief.id
        )
    )


def test_outcome_brief_correct_path_returned_for_answer_a_question(outcome_brief):
    path = brief_overview_business.get_path_for_brief_link(
        outcome_brief,
        '{path}/supplier-questions/answer-question'
    )

    assert path == (
        '/buyers/frameworks/{}/requirements/{}/{}/supplier-questions/answer-question'
        .format(
            outcome_brief.framework.slug,
            outcome_brief.lot.slug,
            outcome_brief.id
        )
    )


def test_specialist_brief_correct_path_returned_for_answer_a_question(specialist_brief):
    path = brief_overview_business.get_path_for_brief_link(
        specialist_brief,
        '{path}/supplier-questions/answer-question'
    )

    assert path == (
        '/buyers/frameworks/{}/requirements/{}/{}/supplier-questions/answer-question'
        .format(
            specialist_brief.framework.slug,
            specialist_brief.lot.slug,
            specialist_brief.id
        )
    )


def test_outcome_brief_correct_path_returned_for_view_responses(outcome_brief):
    path = brief_overview_business.get_path_for_brief_link(
        outcome_brief,
        '/2/brief/{brief_id}/download-responses'
    )

    assert path == '/2/brief/{}/download-responses'.format(outcome_brief.id)


def test_specialist_brief_correct_path_returned_for_view_responses(specialist_brief):
    path = brief_overview_business.get_path_for_brief_link(
        specialist_brief,
        '/2/brief/{brief_id}/download-responses'
    )

    assert path == '/2/brief/{}/download-responses'.format(specialist_brief.id)


def test_outcome_brief_correct_path_returned_for_evaluation_template(outcome_brief):
    path = brief_overview_business.get_path_for_brief_link(
        outcome_brief,
        '/static/media/documents/Scoring_Template.xlsx'
    )

    assert path == '/static/media/documents/Scoring_Template.xlsx'


def test_specialist_brief_correct_path_returned_for_evaluation_template(specialist_brief):
    path = brief_overview_business.get_path_for_brief_link(
        specialist_brief,
        '/static/media/documents/Scoring_Template.xlsx'
    )

    assert path == '/static/media/documents/Scoring_Template.xlsx'


def test_outcome_brief_correct_path_returned_for_start_work_order(outcome_brief):
    path = brief_overview_business.get_path_for_brief_link(outcome_brief, '{path}/work-orders/create')
    assert path == (
        '/buyers/frameworks/{}/requirements/{}/{}/work-orders/create'
        .format(
            outcome_brief.framework.slug,
            outcome_brief.lot.slug,
            outcome_brief.id
        )
    )


def test_specialist_brief_correct_path_returned_for_start_work_order(specialist_brief):
    path = brief_overview_business.get_path_for_brief_link(specialist_brief, '{path}/work-orders/create')
    assert path == (
        '/buyers/frameworks/{}/requirements/{}/{}/work-orders/create'
        .format(
            specialist_brief.framework.slug,
            specialist_brief.lot.slug,
            specialist_brief.id
        )
    )


def test_outcome_brief_correct_path_returned_for_edit_work_order(outcome_brief, work_order):
    outcome_brief.work_order = work_order
    path = brief_overview_business.get_path_for_brief_link(
        outcome_brief,
        '/work-orders/{work_order_id}'
    )

    assert path == '/work-orders/{}'.format(outcome_brief.work_order.id)


def test_specialist_brief_correct_path_returned_for_edit_work_order(specialist_brief, work_order):
    specialist_brief.work_order = work_order
    path = brief_overview_business.get_path_for_brief_link(
        specialist_brief,
        '/work-orders/{work_order_id}'
    )

    assert path == '/work-orders/{}'.format(specialist_brief.work_order.id)
