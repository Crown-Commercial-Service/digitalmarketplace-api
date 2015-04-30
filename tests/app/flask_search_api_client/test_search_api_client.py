from app.flask_search_api_client.search_api_client import SearchApiClient
from nose.tools import assert_equal
import requests
import requests_mock
import os
from flask import json
from app import create_app


class TestSearchApiClient():
    search_api_client = None

    def __init__(self):
        app = create_app('test')
        app.config['ES_ENABLED'] = True
        self.search_api_client = SearchApiClient(app)
        self.session = requests.Session()
        self.adapter = requests_mock.Adapter()
        self.session.mount('mock', self.adapter)

    def test_should_convert_listing_for_indexing(self):
        listing = self.load_example_listing("G6-IaaS")
        converted = self.search_api_client.prepare_service_json_for_indexing(
            listing,
            "Supplier Name",
            listing['id']
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
        assert_equal(converted["service"]["serviceTypes"], [
            "Compute",
            "Storage"
        ]),
        assert_equal(converted["service"]["supplierName"], "Supplier Name")

        assert_equal(converted["service"]["freeOption"], False)
        assert_equal(converted["service"]["trialOption"], True)
        assert_equal(converted["service"]["minimumContractPeriod"], "Month")
        assert_equal(converted["service"]["supportForThirdParties"], False)
        assert_equal(converted["service"]["selfServiceProvisioning"], False)
        assert_equal(converted["service"]["datacentresEUCode"], False)
        assert_equal(converted["service"]["dataBackupRecovery"], True)
        assert_equal(converted["service"]["dataExtractionRemoval"], False)
        assert_equal(converted["service"]["networksConnected"], [
            "Public Services Network (PSN)",
            "Government Secure intranet (GSi)"
        ])
        assert_equal(converted["service"]["apiAccess"], True)
        assert_equal(converted["service"]["openStandardsSupported"], True)
        assert_equal(converted["service"]["openSource"], False)
        assert_equal(converted["service"]["persistentStorage"], True)
        assert_equal(converted["service"]["guaranteedResources"], False)
        assert_equal(converted["service"]["elasticCloud"], True)


    def test_should_convert_listing_with_minimum_fields_for_indexing(self):
        listing = self.load_example_listing("G6-IaaS")
        del listing["serviceTypes"]
        del listing["serviceBenefits"]
        del listing["serviceFeatures"]

        converted = self.search_api_client.prepare_service_json_for_indexing(
            listing,
            "Supplier Name",
            listing['id']
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
            assert_equal(res, True)

    def test_should_not_call_search_api_is_es_disabled(self):
        with requests_mock.mock() as m:
            os.environ['ES_ENABLED'] = 'False'
            local_app = create_app('test')
            local_search_api_client = SearchApiClient(local_app)

            m.post(
                'http://localhost/g-cloud/services/12345',
                json={'message': 'acknowledged'},
                status_code=200)
            payload = self.load_example_listing("G6-IaaS")
            res = local_search_api_client.index(
                "12345",
                payload,
                "Supplier Name"
            )

            assert_equal(res, True)
            assert_equal(m.called, False)

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
            assert_equal(res, False)

    @staticmethod
    def load_example_listing(name):
        file_path = os.path.join("example_listings", "{}.json".format(name))
        with open(file_path) as f:
            return json.load(f)
