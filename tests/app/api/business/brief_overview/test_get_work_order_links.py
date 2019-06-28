from app.api.business import brief_overview_business
from app.models import utcnow


def test_work_order_section_has_start_work_order_link_for_specialist_brief(app, specialist_brief):
    with app.app_context():
        specialist_brief.published_at = utcnow().subtract(weeks=1)
        specialist_brief.questions_closed_at = utcnow().subtract(days=2)
        specialist_brief.closed_at = utcnow().subtract(days=1)

        links = brief_overview_business.get_work_order_links(specialist_brief)
        start_work_order_link = next(iter(links))

        assert start_work_order_link['path']
        assert start_work_order_link['text'] == 'Start a work order'


def test_work_order_section_has_edit_work_order_link_for_specialist_brief(app, specialist_brief, work_order):
    with app.app_context():
        specialist_brief.published_at = utcnow().subtract(weeks=1)
        specialist_brief.questions_closed_at = utcnow().subtract(days=2)
        specialist_brief.closed_at = utcnow().subtract(days=1)
        specialist_brief.work_order = work_order

        links = brief_overview_business.get_work_order_links(specialist_brief)
        edit_work_order_link = next(iter(links))

        assert edit_work_order_link['path']
        assert edit_work_order_link['text'] == 'Edit work order'
