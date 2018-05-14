from app.api.services import brief_overview_service


def test_brief_link_has_complete_key():
    link = brief_overview_service.build_brief_link(True, '/title', 'Title')

    assert 'complete' in link
    assert link['complete']


def test_brief_link_has_path_key():
    link = brief_overview_service.build_brief_link(True, '/title', 'Title')

    assert 'path' in link
    assert link['path'] == '/title'


def test_brief_link_has_text_key():
    link = brief_overview_service.build_brief_link(True, '/title', 'Title')

    assert 'text' in link
    assert link['text'] == 'Title'
