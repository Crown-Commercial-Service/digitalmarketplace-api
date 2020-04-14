import pendulum
import pytest

from app.api.business.brief import brief_business
from app.api.services import briefs as briefs_service
from app.api.services import lots_service
from tests.app.helpers import BaseApplicationTest


class TestOpportunityIsOpenToAll(BaseApplicationTest):
    def setup(self):
        super(TestOpportunityIsOpenToAll, self).setup()

    @pytest.mark.parametrize('open_to', ['all', 'category'])
    def test_atm_opportunity_is_open_to_all(self, briefs, open_to):
        lot = lots_service.find(slug='atm').one_or_none()
        brief = briefs_service.find(lot=lot).one_or_none()

        # Open to category is still considered to be open to all because a seller can
        # join a category after an opportunity has been published and submit a response
        brief.data['openTo'] = open_to

        open_to_all = brief_business.is_open_to_all(brief)
        assert open_to_all is True

    def test_specialist_opportunity_is_open_to_all(self, briefs):
        lot = lots_service.find(slug='specialist').one_or_none()
        brief = briefs_service.find(lot=lot).one_or_none()
        brief.data['openTo'] = 'all'

        open_to_all = brief_business.is_open_to_all(brief)
        assert open_to_all is True

    def test_specialist_opportunity_is_not_open_to_all(self, briefs):
        lot = lots_service.find(slug='specialist').one_or_none()
        brief = briefs_service.find(lot=lot).one_or_none()
        brief.data['openTo'] = 'selected'

        open_to_all = brief_business.is_open_to_all(brief)
        assert open_to_all is False

    def test_rfx_opportunity_is_not_open_to_all(self, briefs):
        lot = lots_service.find(slug='rfx').one_or_none()
        brief = briefs_service.find(lot=lot).one_or_none()
        open_to_all = brief_business.is_open_to_all(brief)
        assert open_to_all is False

    def test_training_opportunity_is_not_open_to_all(self, briefs):
        lot = lots_service.find(slug='training2').one_or_none()
        brief = briefs_service.find(lot=lot).one_or_none()
        open_to_all = brief_business.is_open_to_all(brief)
        assert open_to_all is False
