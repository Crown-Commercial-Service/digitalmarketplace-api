import pytest

from app.api.services import brief_overview_service


@pytest.fixture()
def publish_links():
    return [
        brief_overview_service.BRIEF_WINDOW_TEXT, brief_overview_service.DESCRIPTION_OF_WORK_TEXT,
        brief_overview_service.LOCATION_TEXT, brief_overview_service.PUBLISH_TEXT,
        brief_overview_service.QUESTION_AND_ANSWER_TEXT, brief_overview_service.ROLE_TEXT,
        brief_overview_service.SHORTLIST_AND_EVALUATION_TEXT, brief_overview_service.TITLE_TEXT,
        brief_overview_service.WHO_CAN_RESPOND_TEXT
    ]


def test_publish_section_has_all_links_for_draft_specialist_brief(specialist_brief, publish_links):
    links = brief_overview_service.get_publish_links(specialist_brief)

    for link in links:
        assert link['path']
        assert any(link['text'] == text for text in publish_links)


def test_publish_section_links_are_disabled_when_specialist_brief_has_been_published(app, specialist_brief):
    with app.app_context():
        specialist_brief.status = 'live'
        links = brief_overview_service.get_publish_links(specialist_brief)

        for link in links:
            assert all(not link['path'] for link in links)
