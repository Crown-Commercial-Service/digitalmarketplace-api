from app.api.services import brief_overview_service


def test_section_has_links_key():
    links = ['test']
    section = brief_overview_service.build_section(links, 'Developer')

    assert 'links' in section
    assert section['links'] == ['test']


def test_section_has_title_key():
    section = brief_overview_service.build_section(['test'], 'Developer')

    assert 'title' in section
    assert section['title'] == 'Developer'
