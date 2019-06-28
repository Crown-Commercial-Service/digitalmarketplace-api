import pytest

from app.api.business import brief_overview_business


@pytest.fixture()
def evaluation_link_texts():
    return ['Evaluation template (XLSX 13KB)']


def test_evaluation_section_has_all_links_for_specialist_brief(specialist_brief, evaluation_link_texts):
    links = brief_overview_business.get_evaluation_links(specialist_brief)

    for link in links:
        assert link['path']
        assert any(link['text'] == text for text in evaluation_link_texts)
