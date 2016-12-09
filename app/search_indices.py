import json

from . import es_client, db


from flask import current_app
from elasticsearch import Elasticsearch
from elasticsearch.client import IndicesClient
from .modelsbase import jsondumps


SUPPLIER_DOC_TYPE = 'supplier'


def index_supplier(supplier):
    """
    Add supplier to search index.

    Raises TransportError on failure.
    """

    from models import Supplier

    if supplier.abn == Supplier.DUMMY_ABN:
        current_app.logger.info(
            'Not indexing example supplier "{supplier_name}"',
            extra={'supplier_name': supplier.name}
        )
    else:
        current_app.logger.info(
            'Attempting to add "{supplier_name}" to supplier search index',
            extra={'supplier_name': supplier.name}
        )
        supplier_json = jsondumps(supplier.serializable)

        es_client.index(index=get_supplier_index_name(),
                        doc_type=SUPPLIER_DOC_TYPE,
                        body=supplier_json,
                        id=supplier.code)


def get_supplier_index_name():
    return 'suppliers' + current_app.config['DM_API_ELASTICSEARCH_INDEX_SUFFIX']


def _get_raw_elasticsearch_connection():
    host = current_app.config.get('ELASTICSEARCH_HOST')
    return Elasticsearch(hosts=[host])


def create_supplier_index(index_client):
    from models import Supplier

    name = get_supplier_index_name()

    settings_json = jsondumps({
        'settings': {
            'index': {
                'analysis': {
                    'analyzer': {
                        'sortable': {  # A custom analyzer to make sorting case insensitive. Used in mapping.
                            'tokenizer': 'keyword',
                            'filter': 'lowercase'
                        }
                    }
                }
            }
        }
    })
    index_client.create(index=name, body=settings_json)

    mapping_json = jsondumps({
        'properties': {
            'name': {
                'type': 'multi_field',
                'fields': {
                    'name': {'type': 'string', 'index': 'analyzed'},
                    'not_analyzed': {'type': 'string', 'analyzer': 'sortable'},  # Custom analyzer from settings
                },
            },
            'abn': {
                'type': 'string',
                'index': 'not_analyzed',
            },
            'acn': {
                'type': 'string',
                'index': 'not_analyzed',
            },
            'contacts': {
                'properties': {
                    'phone': {
                        'type': 'string',
                        'index': 'not_analyzed',
                    },
                },
            },
            'creationTime': {
                'type': 'string',
                'index': 'no',
            },
            'lastUpdateTime': {
                'type': 'string',
                'index': 'no',
            },
            'domains': {
                'properties': {
                    'assessed': {
                        'type': 'string',
                        'index': 'not_analyzed'
                    }
                }
            },
            'prices': {
                'properties': {
                    'serviceRole': {
                        'properties': {
                            'category': {
                                'type': 'string',
                                'index': 'not_analyzed',
                            },
                            'role': {
                                'type': 'string',
                                'index': 'not_analyzed',
                            },
                        },
                    },
                },
            },
        },
    })
    index_client.put_mapping(index=name, doc_type=SUPPLIER_DOC_TYPE, body=mapping_json)

    db.session.execute('LOCK TABLE supplier IN SHARE MODE')  # block supplier updates but not reads

    for supplier in Supplier.query.all():
        index_supplier(supplier)


def create_indices(recreate=True):
    # TODO: use index alias juggling to create indices without downtime
    es = _get_raw_elasticsearch_connection()
    ic = IndicesClient(es)
    if not indices_exist(ic):
        create_supplier_index(ic)


def delete_indices():
    es = _get_raw_elasticsearch_connection()
    ic = IndicesClient(es)
    if indices_exist(ic):
        ic.delete(get_supplier_index_name())


def indices_exist(index_client=None):
    if index_client is None:
        index_client = IndicesClient(_get_raw_elasticsearch_connection())
    index_names = [get_supplier_index_name()]
    return index_client.exists(index=','.join(index_names))
