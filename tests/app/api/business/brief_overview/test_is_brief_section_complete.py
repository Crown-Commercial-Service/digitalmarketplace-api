from app.api.business import brief_overview_business


def test_section_is_complete_when_brief_contains_all_required_fields(specialist_brief):
    section = {
        'name': 'Role',
        'optional': [],
        'required': ['title']
    }

    specialist_brief.data = {'title': 'Python Developer'}
    complete = brief_overview_business.is_brief_section_complete(specialist_brief, section)

    assert complete


def test_section_is_not_complete_when_brief_is_missing_a_required_field(specialist_brief):
    section = {
        'name': 'Role',
        'optional': [],
        'required': ['title']
    }

    specialist_brief.data = {}
    complete = brief_overview_business.is_brief_section_complete(specialist_brief, section)

    assert not complete


def test_section_is_complete_when_brief_contains_an_optional_field(specialist_brief):
    section = {
        'name': 'Question and answer session details',
        'optional': ['questionAndAnswerSessionDetails'],
        'required': []
    }

    specialist_brief.data = {'questionAndAnswerSessionDetails': 'Next Monday 3pm'}
    complete = brief_overview_business.is_brief_section_complete(specialist_brief, section)

    assert complete


def test_section_is_not_complete_when_brief_is_missing_all_optional_fields(specialist_brief):
    section = {
        'name': 'Question and answer session details',
        'optional': ['questionAndAnswerSessionDetails'],
        'required': []
    }

    specialist_brief.data = {}
    complete = brief_overview_business.is_brief_section_complete(specialist_brief, section)

    assert not complete
