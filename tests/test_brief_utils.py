import mock
from app import db
from app.brief_utils import index_brief
from app.models import Brief, Lot, Framework
from tests.bases import BaseApplicationTest


@mock.patch('app.brief_utils.index_object', autospec=True)
class TestIndexBriefs(BaseApplicationTest):
    def test_live_dos_2_brief_is_indexed(self, index_object, live_dos2_framework):
        dos2 = Framework.query.filter(Framework.slug == 'digital-outcomes-and-specialists-2').first()

        with mock.patch.object(Brief, "serialize", return_value={'serialized': 'object'}):
            lot = Lot.query.filter(Lot.slug == 'digital-outcomes').one()
            brief = Brief(status='live', framework=dos2, data={'requirementsLength': '1 week'}, lot=lot)
            db.session.add(brief)
            db.session.commit()
            index_brief(brief)

        index_object.assert_called_once_with(
            framework='digital-outcomes-and-specialists-2',
            doc_type='briefs',
            object_id=brief.id,
            serialized_object={'serialized': 'object'},
        )

    def test_draft_dos_2_brief_is_not_indexed(self, index_object, live_dos2_framework):
        dos2 = Framework.query.filter(Framework.slug == 'digital-outcomes-and-specialists-2').first()

        with mock.patch.object(Brief, "serialize", return_value={'serialized': 'object'}):
            brief = Brief(status='draft', framework=dos2, data={'requirementsLength': '1 week'})
            index_brief(brief)

        assert index_object.called is False
