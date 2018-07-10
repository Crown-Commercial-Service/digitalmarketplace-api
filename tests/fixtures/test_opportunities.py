import json
import pytest
from datetime import date
from tests.app.helpers import COMPLETE_DIGITAL_SPECIALISTS_BRIEF

briefs_data_all_sellers = COMPLETE_DIGITAL_SPECIALISTS_BRIEF.copy()
briefs_data_all_sellers.update({'sellerSelector': 'allSellers'})

briefs_data_one_seller = COMPLETE_DIGITAL_SPECIALISTS_BRIEF.copy()
briefs_data_one_seller.update({'sellerSelector': 'oneSeller'})

briefs_data_selected_sellers = COMPLETE_DIGITAL_SPECIALISTS_BRIEF.copy()
briefs_data_selected_sellers.update({'sellerSelector': 'someSellers'})

briefs_data_training_aoe = COMPLETE_DIGITAL_SPECIALISTS_BRIEF.copy()
briefs_data_training_aoe.update({'areaOfExpertise': 'Training, Learning and Development'})

briefs_data_location = COMPLETE_DIGITAL_SPECIALISTS_BRIEF.copy()
briefs_data_location.update({'location': ['New South Wales', 'Offsite']})


def test_opportunities_success_no_filters(client, briefs):
    res = client.get(
        '/2/opportunities',
        content_type='application/json'
    )
    assert res.status_code == 200

    data = json.loads(res.get_data(as_text=True))
    assert 'opportunities' in data
    assert len(data['opportunities']) == 5


@pytest.mark.parametrize(
    'briefs',
    [{'published_at': '%s-01-01' % (date.today().year - 1)}],
    indirect=True
)
def test_opportunities_success_status_filter_closed(client, briefs):
    res = client.get(
        '/2/opportunities?statusFilters=closed',
        content_type='application/json'
    )
    assert res.status_code == 200

    data = json.loads(res.get_data(as_text=True))
    assert 'opportunities' in data
    assert len(data['opportunities']) == 5

    res = client.get(
        '/2/opportunities?statusFilters=live',
        content_type='application/json'
    )
    assert res.status_code == 200

    data = json.loads(res.get_data(as_text=True))
    assert 'opportunities' in data
    assert len(data['opportunities']) == 0


def test_opportunities_success_status_filter_open(client, briefs):
    res = client.get(
        '/2/opportunities?statusFilters=closed',
        content_type='application/json'
    )
    assert res.status_code == 200

    data = json.loads(res.get_data(as_text=True))
    assert 'opportunities' in data
    assert len(data['opportunities']) == 0

    res = client.get(
        '/2/opportunities?statusFilters=live',
        content_type='application/json'
    )
    assert res.status_code == 200

    data = json.loads(res.get_data(as_text=True))
    assert 'opportunities' in data
    assert len(data['opportunities']) == 5


@pytest.mark.parametrize(
    'briefs',
    [{'data': briefs_data_all_sellers}],
    indirect=True
)
def test_opportunities_success_opento_filter_all(client, briefs):
    res = client.get(
        '/2/opportunities?openToFilters=all',
        content_type='application/json'
    )
    assert res.status_code == 200

    data = json.loads(res.get_data(as_text=True))
    assert 'opportunities' in data
    assert len(data['opportunities']) == 5

    res = client.get(
        '/2/opportunities?openToFilters=selected',
        content_type='application/json'
    )
    assert res.status_code == 200

    data = json.loads(res.get_data(as_text=True))
    assert 'opportunities' in data
    assert len(data['opportunities']) == 0

    res = client.get(
        '/2/opportunities?openToFilters=one',
        content_type='application/json'
    )
    assert res.status_code == 200

    data = json.loads(res.get_data(as_text=True))
    assert 'opportunities' in data
    assert len(data['opportunities']) == 0


@pytest.mark.parametrize(
    'briefs',
    [{'data': briefs_data_selected_sellers}],
    indirect=True
)
def test_opportunities_success_opento_filter_some(client, briefs):
    res = client.get(
        '/2/opportunities?openToFilters=all',
        content_type='application/json'
    )
    assert res.status_code == 200

    data = json.loads(res.get_data(as_text=True))
    assert 'opportunities' in data
    assert len(data['opportunities']) == 0

    res = client.get(
        '/2/opportunities?openToFilters=selected',
        content_type='application/json'
    )
    assert res.status_code == 200

    data = json.loads(res.get_data(as_text=True))
    assert 'opportunities' in data
    assert len(data['opportunities']) == 5

    res = client.get(
        '/2/opportunities?openToFilters=one',
        content_type='application/json'
    )
    assert res.status_code == 200

    data = json.loads(res.get_data(as_text=True))
    assert 'opportunities' in data
    assert len(data['opportunities']) == 0


@pytest.mark.parametrize(
    'briefs',
    [{'data': briefs_data_one_seller}],
    indirect=True
)
def test_opportunities_success_opento_filter_one(client, briefs):
    res = client.get(
        '/2/opportunities?openToFilters=all',
        content_type='application/json'
    )
    assert res.status_code == 200

    data = json.loads(res.get_data(as_text=True))
    assert 'opportunities' in data
    assert len(data['opportunities']) == 0

    res = client.get(
        '/2/opportunities?openToFilters=selected',
        content_type='application/json'
    )
    assert res.status_code == 200

    data = json.loads(res.get_data(as_text=True))
    assert 'opportunities' in data
    assert len(data['opportunities']) == 0

    res = client.get(
        '/2/opportunities?openToFilters=one',
        content_type='application/json'
    )
    assert res.status_code == 200

    data = json.loads(res.get_data(as_text=True))
    assert 'opportunities' in data
    assert len(data['opportunities']) == 5


def test_opportunities_success_type_specialists(client, briefs):
    res = client.get(
        '/2/opportunities?typeFilters=specialists',
        content_type='application/json'
    )
    assert res.status_code == 200

    data = json.loads(res.get_data(as_text=True))
    assert 'opportunities' in data
    assert len(data['opportunities']) == 5

    res = client.get(
        '/2/opportunities?typeFilters=outcomes',
        content_type='application/json'
    )
    assert res.status_code == 200

    data = json.loads(res.get_data(as_text=True))
    assert 'opportunities' in data
    assert len(data['opportunities']) == 0


@pytest.mark.parametrize(
    'briefs',
    [{'lot_slug': 'digital-outcome'}],
    indirect=True
)
def test_opportunities_success_type_outcomes(client, briefs):
    res = client.get(
        '/2/opportunities?typeFilters=specialists',
        content_type='application/json'
    )
    assert res.status_code == 200

    data = json.loads(res.get_data(as_text=True))
    assert 'opportunities' in data
    assert len(data['opportunities']) == 0

    res = client.get(
        '/2/opportunities?typeFilters=outcomes',
        content_type='application/json'
    )
    assert res.status_code == 200

    data = json.loads(res.get_data(as_text=True))
    assert 'opportunities' in data
    assert len(data['opportunities']) == 5


@pytest.mark.parametrize(
    'briefs',
    [{'data': briefs_data_training_aoe}],
    indirect=True
)
def test_opportunities_success_type_training_via_area_of_expertise(client, briefs):
    res = client.get(
        '/2/opportunities?typeFilters=outcomes',
        content_type='application/json'
    )
    assert res.status_code == 200

    data = json.loads(res.get_data(as_text=True))
    assert 'opportunities' in data
    assert len(data['opportunities']) == 0

    res = client.get(
        '/2/opportunities?typeFilters=training',
        content_type='application/json'
    )
    assert res.status_code == 200

    data = json.loads(res.get_data(as_text=True))
    assert 'opportunities' in data
    assert len(data['opportunities']) == 5


@pytest.mark.parametrize(
    'briefs',
    [{'data': briefs_data_location}],
    indirect=True
)
def test_opportunities_success_location(client, briefs):
    res = client.get(
        '/2/opportunities?locationFilters=ACT',
        content_type='application/json'
    )
    assert res.status_code == 200

    data = json.loads(res.get_data(as_text=True))
    assert 'opportunities' in data
    assert len(data['opportunities']) == 0

    res = client.get(
        '/2/opportunities?locationFilters=NSW,ACT',
        content_type='application/json'
    )
    assert res.status_code == 200

    data = json.loads(res.get_data(as_text=True))
    assert 'opportunities' in data
    assert len(data['opportunities']) == 5

    res = client.get(
        '/2/opportunities?locationFilters=ACT,Remote',
        content_type='application/json'
    )
    assert res.status_code == 200

    data = json.loads(res.get_data(as_text=True))
    assert 'opportunities' in data
    assert len(data['opportunities']) == 5
