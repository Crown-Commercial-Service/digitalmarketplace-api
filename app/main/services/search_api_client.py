import requests
import os
from flask import json


class SearchApiClient():
    INDEX_NAME = "g-cloud"
    DOC_TYPE = "services"

    def __init__(self):
        self.root_url = os.environ.get('DM_SEARCH_API_URL', '')
        self.token = os.environ.get('DM_SEARCH_API_AUTH_TOKEN', '')
        self.url = "{}/{}/{}".format(
            self.root_url,
            self.INDEX_NAME,
            self.DOC_TYPE
        )
        self.headers = {
            "content-type": "application/json",
            "Authorization": "Bearer {}".format(self.token)
        }

    def index(self, service_id, index_data, supplier_name):
        res = requests.post(
            "{}/{}".format(self.url, service_id),
            data=json.dumps(index_data),
            headers=self.headers
        )

        return res

    @staticmethod
    def prepare_service_json_for_indexing(json_to_index, supplier_name):
        # TODO fields here matches same in Search API
        # TODO need to extract to common place
        fields = [
            "id",
            "lot",
            "serviceName",
            "serviceSummary",
            "serviceBenefits",
            "serviceFeatures",
            "serviceTypes",
            "supplierName"
        ]
        service = dict(
            [(k, json_to_index[k]) for k in fields if k in json_to_index]
        )
        service["supplierName"] = supplier_name
        return {
            "service": service
        }
