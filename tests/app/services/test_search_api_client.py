from app.main.services.search_api_client import SearchApiClient
from nose.tools import assert_equal
import requests
import requests_mock
import os
from flask import json


class TestSearchApiClient():

    def __init__(self):
        os.environ['DM_SEARCH_API_URL'] = "http://localhost"
        self.search_api_client = SearchApiClient()
        self.session = requests.Session()
        self.adapter = requests_mock.Adapter()
        self.session.mount('mock', self.adapter)

    def test_should_convert_listing_for_indexing(self):
        listing = self.load_example_listing("G6-IaaS")
        converted = self.search_api_client.prepare_service_json_for_indexing(
            listing,
            "Supplier Name"
        )
        assert_equal("service" in converted, True)
        assert_equal(converted["service"]["id"], "1234567890123456")
        assert_equal(converted["service"]["lot"], "IaaS")
        assert_equal(converted["service"]["serviceName"], "My Iaas Service")
        assert_equal(
            converted["service"]["serviceSummary"],
            "IaaS Service Summary"
        )
        assert_equal(converted["service"]["serviceBenefits"], [
            "Free lollipop to every 10th customer",
            "It's just lovely"
        ])
        assert_equal(converted["service"]["serviceFeatures"], [
            "[To be completed]",
            "This is my second \"feture\""
        ]),
        assert_equal(converted["service"]["serviceTypes"],  [
            "Compute",
            "Storage"
        ]),
        assert_equal(converted["service"]["supplierName"], "Supplier Name")

    def test_should_convert_listing_with_minimum_fields_for_indexing(self):
        listing = self.load_example_listing("G6-IaaS")
        del listing["serviceTypes"]
        del listing["serviceBenefits"]
        del listing["serviceFeatures"]

        converted = self.search_api_client.prepare_service_json_for_indexing(
            listing,
            "Supplier Name"
        )
        assert_equal("service" in converted, True)
        assert_equal(converted["service"]["id"], "1234567890123456")
        assert_equal(converted["service"]["lot"], "IaaS")
        assert_equal(converted["service"]["serviceName"], "My Iaas Service")
        assert_equal(
            converted["service"]["serviceSummary"],
            "IaaS Service Summary"
        )
        assert_equal("serviceBenefits" in converted, False)
        assert_equal("serviceFeatures" in converted, False)
        assert_equal("serviceTypes" in converted, False)
        assert_equal(converted["service"]["supplierName"], "Supplier Name")

    def test_post_to_index_with_type_and_service_id(self):
        with requests_mock.mock() as m:
            m.post(
                'http://localhost/g-cloud/services/12345',
                json={'message': 'acknowledged'},
                status_code=200)
            payload = self.load_example_listing("G6-IaaS")
            res = self.search_api_client.index(
                "12345",
                payload,
                "Supplier Name"
            )
            assert_equal(res.status_code, 200)
            assert_equal(res.json(), {'message': 'acknowledged'})

    def test_should_return_response_from_es_to_caller(self):
        with requests_mock.mock() as m:
            m.post(
                'http://localhost/g-cloud/services/12345',
                json={'error': 'some error'},
                status_code=400)
            payload = self.load_example_listing("G6-IaaS")
            res = self.search_api_client.index(
                "12345",
                payload,
                "Supplier Name"
            )
            assert_equal(res.status_code, 400)
            assert_equal(res.json(), {'error': 'some error'})

    @staticmethod
    def load_example_listing(name):
        file_path = os.path.join("example_listings", "{}.json".format(name))
        with open(file_path) as f:
            return json.load(f)
