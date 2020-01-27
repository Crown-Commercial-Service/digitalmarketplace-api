import pendulum
import pytest

from app.api.business.brief_overview_business import can_close_opportunity_early
from app.api.services import briefs as briefs_service
from app.api.services import lots_service
from app.models import BriefResponse, db
from tests.app.helpers import BaseApplicationTest


class TestCanCloseOpportunity(BaseApplicationTest):
    def setup(self):
        super(TestCanCloseOpportunity, self).setup()

    @pytest.mark.parametrize('status', ['draft', 'closed', 'withdrawn'])
    def test_can_not_close_opportunity_early_with_incorrect_status(self, briefs, status):
        brief = briefs_service.find(status=status).one_or_none()

        can_close = can_close_opportunity_early(brief)
        assert can_close is False

    def test_can_not_close_published_atm_opportunity_early(self, briefs):
        lot = lots_service.find(slug='atm').one_or_none()
        brief = briefs_service.find(lot=lot, status='live').one_or_none()

        can_close = can_close_opportunity_early(brief)
        assert can_close is False

    @pytest.mark.parametrize('lot_slug', ['rfx', 'specialist', 'training2'])
    def test_can_close_published_opportunity_early_with_single_invited_seller_that_responded(
        self, briefs, brief_responses, lot_slug
    ):
        lot = lots_service.find(slug=lot_slug).one_or_none()
        brief = briefs_service.find(lot=lot, status='live').one_or_none()

        can_close = can_close_opportunity_early(brief)
        assert can_close is True

    @pytest.mark.parametrize('lot_slug', ['rfx', 'specialist', 'training2'])
    def test_can_not_close_published_opportunity_early_with_multiple_invited_sellers(self, briefs, lot_slug):
        lot = lots_service.find(slug=lot_slug).one_or_none()
        brief = briefs_service.find(lot=lot, status='live').one_or_none()
        brief.data['sellers'].update({'456': 'Big Corp'})

        can_close = can_close_opportunity_early(brief)
        assert can_close is False

    @pytest.mark.parametrize('brief_data', [
        {'lot_slug': 'rfx', 'seller_selector': 'someSellers'},
        {'lot_slug': 'specialist', 'seller_selector': 'allSellers'},
        {'lot_slug': 'training2', 'seller_selector': 'someSellers'}
    ])
    def test_can_not_close_published_opportunity_early_with_incorrect_seller_selector(self, briefs, brief_data):
        lot = lots_service.find(slug=brief_data['lot_slug']).one_or_none()
        brief = briefs_service.find(lot=lot, status='live').one_or_none()
        brief.data['sellerSelector'] = brief_data['seller_selector']

        can_close = can_close_opportunity_early(brief)
        assert can_close is False

    @pytest.mark.parametrize('lot_slug', ['rfx', 'specialist', 'training2'])
    def test_can_not_close_published_opportunity_early_with_multiple_seller_responses(
        self, briefs, suppliers, lot_slug
    ):
        lot = lots_service.find(slug=lot_slug).one_or_none()
        brief = briefs_service.find(lot=lot, status='live').one_or_none()

        db.session.add(
            BriefResponse(
                id=6,
                brief_id=brief.id,
                data={},
                supplier_code=456
            )
        )

        can_close = can_close_opportunity_early(brief)
        assert can_close is False
