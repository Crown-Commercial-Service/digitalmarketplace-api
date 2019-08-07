import pytest
from mock import patch

from app.api.business import brief_overview_business
from app.models import utcnow


@pytest.fixture()
def shortlist_links():
    return ['View responses']


@patch('app.api.business.brief_overview_business.current_user')
def test_shortlist_section_has_all_links_for_closed_specialist_brief(
    current_user,
    app,
    specialist_brief,
    shortlist_links
):
    with app.app_context():
        specialist_brief.published_at = utcnow().subtract(weeks=1)
        specialist_brief.questions_closed_at = utcnow().subtract(days=2)
        specialist_brief.closed_at = utcnow().subtract(days=1)
        links = brief_overview_business.get_shortlist_links(specialist_brief)

        for link in links:
            assert link['path']
            assert any(link['text'] == text for text in shortlist_links)


@patch('app.api.business.brief_overview_business.current_user')
def test_shortlist_section_links_are_disabled_for_draft_specialist_brief(current_user, specialist_brief):
    links = brief_overview_business.get_shortlist_links(specialist_brief)

    for link in links:
        assert all(not link['path'] for link in links)


@patch('app.api.business.brief_overview_business.current_user')
def test_shortlist_section_links_are_disabled_for_live_specialist_brief(current_user, app, specialist_brief):
    with app.app_context():
        specialist_brief.status = 'live'

        links = brief_overview_business.get_shortlist_links(specialist_brief)

        for link in links:
            assert all(not link['path'] for link in links)


@patch('app.api.business.brief_overview_business.current_user')
def test_shortlist_section_links_are_disabled_for_withdrawn_specialist_brief(current_user, app, specialist_brief):
    with app.app_context():
        specialist_brief.status = 'live'
        specialist_brief.status = 'withdrawn'

        links = brief_overview_business.get_shortlist_links(specialist_brief)

        for link in links:
            assert all(not link['path'] for link in links)
