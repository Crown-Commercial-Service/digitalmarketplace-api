from . import es_client

from flask import jsonify, abort, request, current_app
from elasticsearch import Elasticsearch
from elasticsearch.client import IndicesClient


def get_supplier_index_name():
    return 'suppliers' + current_app.config['DM_API_ELASTICSEARCH_INDEX_SUFFIX']


def _get_raw_elasticsearch_connection():
    host = current_app.config.get('ELASTICSEARCH_HOST')
    return Elasticsearch(hosts=[host])


def create_indices():
    es = _get_raw_elasticsearch_connection()
    ic = IndicesClient(es)
    ic.create(get_supplier_index_name())


def delete_indices():
    es = _get_raw_elasticsearch_connection()
    ic = IndicesClient(es)
    ic.delete(get_supplier_index_name())
