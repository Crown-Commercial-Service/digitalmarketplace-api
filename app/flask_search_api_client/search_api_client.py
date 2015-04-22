import requests
from flask import json


class SearchApiClient:
    __INDEX_NAME__ = "g-cloud"
    __DOC_TYPE__ = "services"
    root_url = None
    token = None
    enabled = False

    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        self.root_url = app.config['DM_SEARCH_API_URL']
        self.token = app.config['DM_SEARCH_API_AUTH_TOKEN']
        self.enabled = app.config['ES_ENABLED']

    def headers(self):
        return {
            "content-type": "application/json",
            "Authorization": "Bearer {}".format(self.token)
        }

    def url(self):
        return "{}/{}/{}".format(
            self.root_url,
            self.__INDEX_NAME__,
            self.__DOC_TYPE__
        )

    def index(self, service_id, index_data, supplier_name):
        if self.enabled:
            res = requests.post(
                "{}/{}".format(self.url(), service_id),
                data=json.dumps(
                    self.prepare_service_json_for_indexing(
                        index_data,
                        supplier_name,
                        service_id)
                ),
                headers=self.headers()
            )
            return res.status_code is 200
        else:
            return True

    @staticmethod
    def prepare_service_json_for_indexing(json_to_index, supplier_name, service_id):
        # TODO fields here matches same in Search API
        # TODO need to extract to common place
        fields = [
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
        service["id"] = service_id
        return {
            "service": service
        }
