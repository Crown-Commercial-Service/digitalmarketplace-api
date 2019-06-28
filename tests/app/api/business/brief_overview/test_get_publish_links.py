import pytest

from app.api.business import brief_overview_business


@pytest.fixture()
def publish_links():
    return [
        'How long your brief will be open',
        'Description of work',
        'Location',
        'Review and publish your requirements',
        'Question and answer session details',
        'Role',
        'Shortlist and evaluation process',
        'Title',
        'Who can respond'
    ]


def test_publish_section_has_all_links_for_draft_specialist_brief(specialist_brief, publish_links):
    links = brief_overview_business.get_publish_links(specialist_brief)

    for link in links:
        assert link['path']
        assert any(link['text'] == text for text in publish_links)


def test_publish_section_links_are_disabled_when_specialist_brief_has_been_published(app, specialist_brief):
    with app.app_context():
        specialist_brief.status = 'live'
        links = brief_overview_business.get_publish_links(specialist_brief)

        for link in links:
            assert all(not link['path'] for link in links)
