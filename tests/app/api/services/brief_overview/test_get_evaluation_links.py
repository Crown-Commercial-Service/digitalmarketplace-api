import pytest

from app.api.services import brief_overview_service


@pytest.fixture()
def evaluation_link_texts():
    return [brief_overview_service.EVALUATION_TEMPLATE_TEXT]


def test_evaluation_section_has_all_links_for_specialist_brief(specialist_brief, evaluation_link_texts):
    links = brief_overview_service.get_evaluation_links(specialist_brief)

    for link in links:
        assert link['path']
        assert any(link['text'] == text for text in evaluation_link_texts)
