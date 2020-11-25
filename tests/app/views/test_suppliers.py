from flask import json
import pytest
import mock
from six.moves.urllib import parse as urlparse
import time
from freezegun import freeze_time
from flask import current_app
from nose.tools import assert_equal, assert_in, assert_is_none, assert_is_not_none, assert_true, assert_false

from app import db
from app.models import Address, Supplier, AuditEvent, SupplierFramework, Framework, Domain, User, utcnow, Product
from ..helpers import BaseApplicationTest, JSONTestMixin, JSONUpdateTestMixin, assert_api_compatible, is_sorted
from decimal import Decimal

import pendulum
from pendulum import create as dt

from collections import Mapping, Iterable
from six import string_types
import six


class TestGetSupplier(BaseApplicationTest):
    def setup(self):
        super(TestGetSupplier, self).setup()

        with self.app.app_context():
            payload = self.load_example_listing("Supplier")
            self.supplier = payload
            self.supplier_code = payload['code']

            response = self.client.post(
                '/suppliers'.format(self.supplier_code),
                data=json.dumps({
                    'supplier': self.supplier
                }),
                content_type='application/json')
            json.loads(response.get_data())
            assert_equal(response.status_code, 201)

    def test_get_non_existent_supplier(self):
        response = self.client.get('/suppliers/100')
        assert_equal(404, response.status_code)

    def test_invalid_supplier_code(self):
        response = self.client.get('/suppliers/abc123')
        assert_equal(404, response.status_code)

    @mock.patch('app.tasks.publish_tasks.supplier')
    def test_deleted_supplier_code(self, supplier):
        self.client.delete('/suppliers/{}'.format(self.supplier_code))
        response = self.client.get('/suppliers/{}'.format(self.supplier_code))
        assert_equal(404, response.status_code)
        supplier.delay.called is False

    def test_get_supplier(self):
        response = self.client.get('/suppliers/{}'.format(self.supplier_code))

        data = json.loads(response.get_data())
        assert_equal(200, response.status_code)
        assert_equal(self.supplier_code, data['supplier']['code'])
        assert_equal(self.supplier['name'], data['supplier']['name'])


class TestListSuppliers(BaseApplicationTest):
    def setup(self):
        super(TestListSuppliers, self).setup()

        # Supplier names like u"Supplier {n}"
        self.setup_dummy_suppliers(7)

    def test_query_string_missing(self):
        response = self.client.get('/suppliers')
        assert_equal(200, response.status_code)
        data = json.loads(response.get_data())
        assert 'suppliers' in data
        assert 'links' in data

    def test_example_supplier_not_listed_by_default(self):
        with self.app.app_context():
            example_supplier = Supplier(
                code=0,
                name='Example Pty Ltd',
                description='',
                summary='',
                abn=Supplier.DUMMY_ABN,
                contacts=[],
                references=[],
                prices=[]
            )
            db.session.add(example_supplier)
        response = self.client.get('/suppliers')
        assert_equal(200, response.status_code)
        data = json.loads(response.get_data())
        assert 'suppliers' in data
        names = [s['name'] for s in data['suppliers']]
        assert 'Example Pty Ltd' not in names

    def test_results_per_page(self):
        response = self.client.get('/suppliers?per_page=2')
        assert_equal(200, response.status_code)
        data = json.loads(response.get_data())
        assert 'suppliers' in data
        assert len(data['suppliers']) == 2

    @mock.patch('app.tasks.publish_tasks.supplier')
    def test_results_after_delete(self, supplier):
        self.client.delete('/suppliers/{}'.format(1))
        response = self.client.get('/suppliers')
        assert_equal(200, response.status_code)
        data = json.loads(response.get_data())
        assert 'suppliers' in data
        assert len(data['suppliers']) == 5
        assert supplier.delay.called is True

    def test_invalid_results_per_page(self):
        response = self.client.get('/suppliers?per_page=bork')
        assert_equal(400, response.status_code)
        assert 'per_page' in response.get_data(as_text=True)

    def test_query_string_prefix_empty(self):
        response = self.client.get('/suppliers?prefix=')
        assert_equal(200, response.status_code)

    def test_query_string_prefix_returns_none(self):
        response = self.client.get('/suppliers?prefix=canada')
        assert_equal(200, response.status_code)
        data = json.loads(response.get_data())
        assert_equal(0, len(data['suppliers']))

    def test_other_prefix_returns_non_alphanumeric_suppliers(self):
        with self.app.app_context():
            db.session.add(
                Supplier(code=999, name=u"999 Supplier",
                         addresses=[Address(address_line="Asdf",
                                            suburb="Asdf",
                                            state="ZZZ",
                                            postal_code="0000",
                                            country='Australia')]
                         )
            )
            self.setup_dummy_service(service_id='1230000000', supplier_code=999)
            db.session.commit()

            response = self.client.get('/suppliers?prefix=other')

            data = json.loads(response.get_data())
            assert_equal(200, response.status_code)
            assert_equal(1, len(data['suppliers']))
            assert_equal(999, data['suppliers'][0]['code'])
            assert_equal(
                u"999 Supplier",
                data['suppliers'][0]['name']
            )

    def test_query_string_prefix_returns_paginated_page_one(self):
        response = self.client.get('/suppliers?prefix=s')
        data = json.loads(response.get_data())

        assert_equal(200, response.status_code)
        assert_equal(5, len(data['suppliers']))
        next_link = data['links']['next']
        assert_in('page=2', next_link)

    def test_query_string_prefix_returns_paginated_page_two(self):
        response = self.client.get('/suppliers?prefix=s&page=2')
        data = json.loads(response.get_data())

        assert_equal(response.status_code, 200)
        assert_equal(len(data['suppliers']), 2)
        prev_link = data['links']['prev']
        assert_in('page=1', prev_link)

    def test_query_string_prefix_returns_no_pagination_for_single_page(self):
        self.setup_additional_dummy_suppliers(5, 'T')
        response = self.client.get('/suppliers?prefix=t')
        data = json.loads(response.get_data())

        assert_equal(200, response.status_code)
        assert_equal(5, len(data['suppliers']))
        assert_equal(['self'], list(data['links'].keys()))

    def test_query_string_prefix_page_out_of_range(self):
        response = self.client.get('/suppliers?prefix=s&page=10')

        assert_equal(response.status_code, 404)

    def test_query_string_prefix_invalid_page_argument(self):
        response = self.client.get('/suppliers?prefix=s&page=a')

        assert_equal(response.status_code, 400)

    def test_below_one_page_number_is_404(self):
        response = self.client.get('/suppliers?page=0')

        assert_equal(response.status_code, 404)


class TestUpdateSupplier(BaseApplicationTest, JSONUpdateTestMixin):
    method = 'patch'
    endpoint = '/suppliers/1'

    def setup(self):
        super(TestUpdateSupplier, self).setup()

        with self.app.app_context():
            payload = self.load_example_listing("Supplier")
            self.supplier = payload
            self.supplier_code = payload['code']

            self.client.post('/suppliers'.format(self.supplier_code),
                             data=json.dumps({'supplier': self.supplier}),
                             content_type='application/json')

    def update_request(self, data=None, user=None, full_data=None):
        return self.client.patch(
            self.endpoint,
            data=json.dumps({
                'supplier': data,
                'updated_by': user or 'supplier@user.dmdev',
            } if full_data is None else full_data),
            content_type='application/json',
        )

    def get_supplier(self):
        return Supplier.query.filter_by(code=1).first()

    def test_update_timestamp(self):
        NOW = pendulum.now()

        with pendulum.test(NOW):
            response = self.update_request({'name': 'Changed Name'})
            assert_equal(response.status_code, 200)

            with self.app.app_context():
                supplier = self.get_supplier()
                assert supplier is not None
                assert supplier.last_update_time == NOW

    def test_empty_update_supplier(self):
        response = self.update_request({})
        assert_equal(response.status_code, 200)

    def test_name_update(self):
        response = self.update_request({'name': "New Name"})
        assert_equal(response.status_code, 200)

        with self.app.app_context():
            supplier = self.get_supplier()

            assert_equal(supplier.name, "New Name")

    def test_price_update(self):
        response = self.update_request({"prices": [{
            "serviceRole": {"category": "Business Analysis", "role": "Junior Business Analyst"},
            "hourlyRate": "1.10",
            "dailyRate": "2.90"}]})
        assert_equal(response.status_code, 200)

        with self.app.app_context():
            supplier = self.get_supplier()

            price = supplier.prices[0]
            assert_equal(price.hourly_rate, Decimal('1.10'))
            assert_equal(price.daily_rate, Decimal('2.90'))

    @pytest.mark.skipif(True, reason="failing for AU")
    def test_supplier_update_creates_audit_event(self):
        self.update_request({'name': "Name"})

        with self.app.app_context():
            supplier = self.get_supplier()

            audit = AuditEvent.query.filter(
                AuditEvent.object == supplier
            ).first()

            assert_equal(audit.type, "supplier_update")
            assert_equal(audit.user, "supplier@user.dmdev")
            assert_equal(audit.data, {
                'update': {'name': "Name"},
            })

    def test_update_response_matches_payload(self):
        payload = self.load_example_listing("Supplier")
        response = self.update_request({'name': "New Name"})
        assert_equal(response.status_code, 200)

        payload.update({'name': 'New Name'})
        supplier = json.loads(response.get_data())['supplier']

        supplier.pop('creationTime')
        supplier.pop('lastUpdateTime')

        for k, v in dict(supplier).items():
            if v is None:
                supplier.pop(k)

        assert_api_compatible(payload, supplier)

    def test_update_all_fields(self):
        response = self.update_request({
            'name': "New Name",
            'description': "New Description",
        })

        assert_equal(response.status_code, 200)

        with self.app.app_context():
            supplier = self.get_supplier()

        assert_equal(supplier.name, 'New Name')
        assert_equal(supplier.description, "New Description")

    def test_update_missing_supplier(self):
        response = self.client.patch(
            '/suppliers/234567',
            data=json.dumps({'supplier': {}}),
            content_type='application/json',
        )

        assert_equal(response.status_code, 404)

    def test_update_with_unexpected_keys(self):
        response = self.update_request({
            'new_key': "value",
            'name': "New Name"
        })

        assert_equal(response.status_code, 200)

        response_data = response.get_data(as_text=True)
        response_json = json.loads(response_data)
        assert 'new_key' in response_json['supplier']

    @pytest.mark.skipif(True, reason="failing for AU")
    def test_update_without_updated_by(self):
        response = self.update_request(full_data={
            'supplier': {'name': "New Name"},
        })

        assert_equal(response.status_code, 400)


class TestPostSupplier(BaseApplicationTest, JSONTestMixin):
    method = "post"
    endpoint = "/suppliers"

    def setup(self):
        super(TestPostSupplier, self).setup()

    def post_supplier(self, supplier):
        return self.client.post(
            '/suppliers',
            data=json.dumps({
                'supplier': supplier
            }),
            content_type='application/json')

    def test_add_a_new_supplier(self):
        with self.app.app_context():
            NOW = pendulum.now('UTC')

            with pendulum.test(NOW):
                payload = self.load_example_listing("Supplier")
                response = self.post_supplier(payload)
                assert_equal(response.status_code, 201)
                assert_is_not_none(Supplier.query.filter(
                    Supplier.name == payload['name']
                ).first())
                supplier =\
                    Supplier.query.filter_by(code=payload['code']).first()
                assert_is_not_none(supplier)

                assert supplier.creation_time == NOW
                assert supplier.last_update_time == NOW

    def test_when_supplier_has_a_missing_name(self):
        payload = self.load_example_listing("Supplier")
        payload['name'] = ''

        response = self.post_supplier(payload)
        assert_equal(response.status_code, 400)
        assert_equal('Supplier name required', json.loads(response.get_data())['error'])

    def test_abn_normalisation(self):
        payload = self.load_example_listing("Supplier")
        payload['abn'] = '50110219460 '

        with self.app.app_context():
            response = self.post_supplier(payload)
            assert_equal(response.status_code, 201)

            # just returns the same string now because abns get validated/formatted client side
            assert_equal(Supplier.query.filter_by(code=payload['code']).first().abn, '50110219460 ')

    def test_bad_abn(self):
        payload = self.load_example_listing("Supplier")
        payload['abn'] = 'bad'

        response = self.post_supplier(payload)
        assert_equal(response.status_code, 201)

    def test_acn_normalisation(self):
        payload = self.load_example_listing("Supplier")
        payload['acn'] = '071408449 '

        with self.app.app_context():
            response = self.post_supplier(payload)
            assert_equal(response.status_code, 201)
            assert_equal(Supplier.query.filter_by(code=payload['code']).first().acn, '071 408 449')

    def test_bad_acn(self):
        payload = self.load_example_listing("Supplier")
        payload['acn'] = 'bad'

        response = self.post_supplier(payload)
        assert_equal(response.status_code, 400)
        assert_in('ACN', json.loads(response.get_data())['error'])

    def test_bad_postal_code(self):
        payload = self.load_example_listing("Supplier")
        payload['addresses'][0]['postal_code'] = 'bad'

        response = self.post_supplier(payload)
        assert_equal(response.status_code, 400)
        assert_in('postal code', json.loads(response.get_data())['error'])

    def test_bad_hourly_rate(self):
        payload = self.load_example_listing("Supplier")
        payload['prices'][0]['hourlyRate'] = 'bad'

        response = self.post_supplier(payload)
        assert_equal(response.status_code, 400)
        assert_in('money format', json.loads(response.get_data())['error'])

    def test_bad_daily_rate(self):
        payload = self.load_example_listing("Supplier")
        payload['prices'][0]['dailyRate'] = 'bad'

        response = self.post_supplier(payload)
        assert_equal(response.status_code, 400)
        assert_in('money format', json.loads(response.get_data())['error'])

    def test_bad_price_category(self):
        payload = self.load_example_listing("Supplier")
        payload['prices'][0]['serviceRole']['category'] = 'bad'

        response = self.post_supplier(payload)
        assert_equal(response.status_code, 400)
        assert_in('category', json.loads(response.get_data())['error'])

    def test_bad_price_role(self):
        payload = self.load_example_listing("Supplier")
        payload['prices'][0]['serviceRole']['role'] = 'bad'

        response = self.post_supplier(payload)
        assert_equal(response.status_code, 400)
        assert_in('role', json.loads(response.get_data())['error'])

    def test_when_supplier_has_extra_keys(self):
        payload = self.load_example_listing("Supplier")

        payload.update({'newKey': 1})

        response = self.post_supplier(payload)
        assert_equal(response.status_code, 201)
        assert 'newKey' in json.loads(response.data)['supplier']

    def test_multiple_addresses_in_dict(self):
        payload = self.load_example_listing("Supplier")
        addresses = {
            'addresses': {
                '0': {
                    'address_line': 'commonwealth st',
                    'suburb': 'surrey hills',
                    'state': 'NSW',
                    'postal_code': '2001'
                },
                '1': {
                    'address_line': 'line2',
                    'suburb': 'suburb2',
                    'state': 'ACT',
                    'postal_code': '5001'

                }
            }
        }

        payload.update(addresses)
        response = self.post_supplier(payload)
        assert_equal(response.status_code, 201)

        data = json.loads(response.data)['supplier']
        assert 'addresses' in data

        def assert_subset(d_sub, d_super):
            assert six.viewitems(d_sub) <= six.viewitems(d_super)

        assert_subset(
            addresses['addresses']['0'],
            data['addresses'][0]
        )

        assert_subset(
            addresses['addresses']['1'],
            data['addresses'][1]
        )

        assert_subset(
            addresses['addresses']['0'],
            data['address']
        )


class TestSupplierSearch(BaseApplicationTest):
    def search(self, query_body, **args):
        if args:
            params = '&'.join('{}={}'.format(k, urlparse.quote(v)) for k, v in args.items())
            q = "?{}".format(params)
        else:
            q = ''
        return self.client.get('/suppliers/search{}'.format(q),
                               data=json.dumps(query_body),
                               content_type='application/json')

    def search_products(self, query_body, **args):
        if args:
            params = '&'.join('{}={}'.format(k, urlparse.quote(v)) for k, v in args.items())
            q = "?{}".format(params)
        else:
            q = ''
        return self.client.get('/products/search{}'.format(q),
                               data=json.dumps(query_body),
                               content_type='application/json')

    def post_supplier(self, supplier):
        return self.client.post(
            '/suppliers',
            data=json.dumps({
                'supplier': supplier
            }),
            content_type='application/json')

    def do_search(self, search_json, products=False):
        with self.app.app_context():
            if products:
                response = self.search_products(search_json, framework='digital-outcomes-and-specialists')
            else:
                response = self.search(search_json, framework='digital-outcomes-and-specialists')

            assert_equal(response.status_code, 200)
            result = json.loads(response.get_data())

        hits = result['hits']['hits']
        return [h['_source'] for h in hits]

    def test_basic_search_hit(self):
        payload = self.load_example_listing("Supplier")
        response = self.post_supplier(payload)
        json_result = json.loads(response.get_data())

        with self.app.app_context():
            self.set_framework_status('digital-outcomes-and-specialists', 'open')
            self.client.put(
                '/suppliers/{}/frameworks/{}'.format(
                    json_result['supplier']['code'], 'digital-outcomes-and-specialists'),
                data=json.dumps({'updated_by': 'interested@example.com'}),
                content_type='application/json')

            response = self.search({'query': {'term': {'code': 1}}}, framework='digital-outcomes-and-specialists')
            assert_equal(response.status_code, 200)
            result = json.loads(response.get_data())
            assert_equal(result['hits']['total'], 1)
            assert_equal(len(result['hits']['hits']), 1)
            assert_equal(result['hits']['hits'][0]['_source']['code'], 1)

    def test_basic_search_miss(self):
        response = self.search({'query': {'term': {'code': 654321}}})
        assert_equal(response.status_code, 200)

        result = json.loads(response.get_data())
        assert_equal(result['hits']['total'], 0)
        assert_equal(len(result['hits']['hits']), 0)

    def test_search_results(self):
        self.setup_dummy_suppliers_with_old_and_new_domains(5)

        MATCH_ALL_SEARCH = {
            "query": {
                "match_all": {
                }
            },
            "sort": [{'name': {"order": "desc", "mode": "min"}}]
        }

        CODE_SEARCH = {'query': {'term': {'code': 1}}}

        KEYWORD_NAME_SEARCH = {
            "query": {
                "match_phrase_prefix": {
                    'name': 'suppler 2'  # (sic)
                }
            }
        }

        LEGACY_DOMAIN_SEARCH = {
            "query": {
                "filtered": {
                    "filter": {
                        "terms": {
                            "prices.serviceRole.role": [
                                {'role': 'Senior Ethical Hacker'},
                                {'role': 'Junior Ethical Hacker'},
                            ]
                        }
                    }
                }
            },
        }

        NEW_DOMAIN_SEARCH = {
            "query": {
                "filtered": {
                    "filter": {
                        "terms": {
                            "domains.assessed": ['Data science']
                        }
                    }
                }
            },
        }

        SELLER_TYPES_SEARCH = {
            "query": {
                "filtered": {
                    "filter": {
                        "terms": {
                            "seller_types": ['sme', 'start_up']
                        }
                    }
                }
            },
        }

        SORT_BY_SEARCH = {
            "query": {
                "match_all": {
                }
            },
            "sort": [{'name': {"sort_by": "latest", "mode": "min"}}]
        }

        results = self.do_search(MATCH_ALL_SEARCH)

        assert len(results) == 5
        for result in results:
            if result['code'] == 4:
                pass
            if result['code'] == 5:
                assert result['name'] == "Supplier 4"

        results = self.do_search(CODE_SEARCH)
        assert len(results) == 1

        results = self.do_search(KEYWORD_NAME_SEARCH)
        assert len(results) == 0  # eliminates non-matching example supplier

        results = self.do_search(LEGACY_DOMAIN_SEARCH)
        assert len(results) == 1
        assert results[0]['name'] == 'Supplier 1'

        results = self.do_search(SELLER_TYPES_SEARCH)
        assert len(results) == 1
        assert [_['name'] for _ in results] == ['Supplier 1']

        results = self.do_search(SORT_BY_SEARCH)
        assert len(results) == 5

        with self.app.app_context():
            results = self.do_search(NEW_DOMAIN_SEARCH)
            assert [_['name'] for _ in results] == ['Supplier 2']

    def test_product_search_results(self):
        self.setup_dummy_suppliers_with_old_and_new_domains(5)

        PRODUCT_SEARCH = {
            'sort_dir': 'z-a',
            'domains': ['Content and Publishing', 'Data science'],
        }

        results = self.do_search(PRODUCT_SEARCH, products=True)
        titles = [_['name'] for _ in results]

        assert titles == ['zzz 3', 'otherproduct 3']

        PRODUCT_SEARCH_WITH_TERM_AND_SELLER_TYPE = {
            'seller_types': ['start_up'],
            'search_term': 'otherproduct'
        }
        results = self.do_search(PRODUCT_SEARCH_WITH_TERM_AND_SELLER_TYPE, products=True)

        titles = [_['name'] for _ in results]

        assert titles == [
            'otherproduct 2'
        ]


class TestCounts(BaseApplicationTest):
    def test_get_suppliers(self):
        response = self.client.get('/suppliers/count')
        assert response.status_code == 200


class TestDomains(BaseApplicationTest):

    def test_get_domain_by_id(self):
        response = self.client.get('/domain/1')
        assert_equal(200, response.status_code)
        data = json.loads(response.get_data())
        assert 'domain' in data
        assert 'name' in data['domain']

    def test_get_domain_by_name(self):
        response = self.client.get('/domain/Emerging Technology')
        assert_equal(200, response.status_code)
        data = json.loads(response.get_data())
        assert 'domain' in data
        assert 'name' in data['domain']

    def test_get_domains(self):
        response = self.client.get('/domains')

        assert response.status_code == 200
        domains_json = json.loads(response.get_data())['domains']

        assert [_['name'] for _ in domains_json] == [
            'Strategy and Policy',
            'Change, Training and Transformation',
            'User research and Design',
            'Agile delivery and Governance',
            'Recruitment',
            'Software engineering and Development',
            'Content and Publishing',
            'Cyber security',
            'Marketing, Communications and Engagement',
            'Support and Operations',
            'Data science',
            'Digital products',
            'Emerging technology',
            'ICT risk management and audit activities',
            'ICT managed services',
            'Digital sourcing and ICT procurement',
            'Training, Learning and Development',
            'Platforms integration'
        ]

    @mock.patch('app.tasks.publish_tasks.supplier_domain')
    def test_domain_approvals(self, supplier_domain):
        SAMPLE_DOMAIN = 'data science'

        with self.app.app_context():
            payload = self.setup_dummy_suppliers(1)
            payload = self.setup_dummy_briefs(1)

            supplier = Supplier.query.first()
            supplier.add_unassessed_domain(SAMPLE_DOMAIN)

            suppliers_url = '/suppliers/{}'.format(
                supplier.id,
            )

            supplier_id = supplier.id
            domain_id = Domain.get_by_name_or_id('data science').id

            assessment_url = '/suppliers/{}/domains/{}/assessed'.format(
                supplier.id,
                Domain.get_by_name_or_id('data science').id
            )

            response = self.client.post(assessment_url,
                                        data=json.dumps({'update_details': {'updated_by': 'test@example.com'}}),
                                        content_type='application/json')
            assert_equal(response.status_code, 200)

            supplier = json.loads(response.get_data(as_text=True))['supplier']
            assessed = supplier['domains']['assessed']
            assert 'Data science' in assessed
            assert supplier_domain.delay.called is True


class TestDeleteSupplier(BaseApplicationTest):
    def setup(self):
        super(TestDeleteSupplier, self).setup()

        with self.app.app_context():
            payload = self.load_example_listing("Supplier")
            self.supplier = payload
            self.supplier_code = payload['code']

            response = self.client.post(
                '/suppliers'.format(self.supplier_code),
                data=json.dumps({
                    'supplier': self.supplier
                }),
                content_type='application/json')
            assert_equal(response.status_code, 201)

    @mock.patch('app.tasks.publish_tasks.supplier')
    def test_delete(self, supplier):
        with self.app.app_context():
            assert_is_not_none(Supplier.query.filter_by(code=self.supplier_code).first())
            response = self.client.delete('/suppliers/{}'.format(self.supplier_code))
            assert_equal(200, response.status_code)
            assert_is_not_none(Supplier.query.filter_by(code=self.supplier_code, status='deleted').first())
            assert supplier.delay.called is True

    def test_nonexistant_delete(self):
        with self.app.app_context():
            response = self.client.delete('/suppliers/789012')
            assert_equal(404, response.status_code)


class TestDeleteAllSuppliers(BaseApplicationTest):
    def setup(self):
        super(TestDeleteAllSuppliers, self).setup()

        with self.app.app_context():
            payload = self.load_example_listing("Suppliers")
            for supplier in payload:
                response = self.client.post(
                    '/suppliers',
                    data=json.dumps({
                        'supplier': supplier
                    }),
                    content_type='application/json')
                assert_equal(response.status_code, 201)


class TestSupplierFrameworkUpdates(BaseApplicationTest):
    def setup(self):
        super(TestSupplierFrameworkUpdates, self).setup()

        self.setup_dummy_suppliers(1)
        self.setup_dummy_user(1, role='supplier')

        with self.app.app_context():
            self.set_framework_status('digital-outcomes-and-specialists', 'open')
            self.client.put(
                '/suppliers/0/frameworks/digital-outcomes-and-specialists',
                data=json.dumps({'updated_by': 'interested@example.com'}),
                content_type='application/json')

            answers = SupplierFramework(
                supplier_code=0, framework_id=2,
                declaration={'an_answer': 'Yes it is'},
                on_framework=True,
                agreement_returned_at=dt(2015, 10, 10, 10, 10, 10),
                countersigned_at=dt(2015, 11, 12, 13, 14, 15),
                agreement_details={
                    u'signerName': u'thing',
                    u'signerRole': u'thing',
                    u'uploaderUserId': 20
                },
            )
            db.session.add(answers)

            g_cloud_8 = Framework(
                slug='g-cloud-8',
                name='G-Cloud 8',
                framework='g-cloud',
                framework_agreement_details={'frameworkAgreementVersion': 'v1.0'},
                status='open',
                clarification_questions_open=False
            )
            db.session.add(g_cloud_8)
            db.session.commit()

            self.client.put(
                '/suppliers/0/frameworks/g-cloud-8',
                data=json.dumps({'updated_by': 'interested@example.com'}),
                content_type='application/json')

    def teardown(self):
        with self.app.app_context():
            g_cloud_8 = Framework.query.filter(Framework.slug == 'g-cloud-8').first()
            SupplierFramework.query.filter(SupplierFramework.framework_id == g_cloud_8.id).delete()
            Framework.query.filter(Framework.id == g_cloud_8.id).delete()
            db.session.commit()

        super(TestSupplierFrameworkUpdates, self).teardown()

    def supplier_framework_update(self, supplier_id, framework_slug, update={}):
        return self.client.post(
            '/suppliers/{}/frameworks/{}'.format(supplier_id, framework_slug),
            data=json.dumps(
                {
                    'updated_by': 'interested@example.com',
                    'frameworkInterest': update
                }),
            content_type='application/json')

    def test_get_supplier_framework_info(self):
        response = self.client.get(
            '/suppliers/0/frameworks/g-cloud-4')

        data = json.loads(response.get_data())
        assert response.status_code, 200
        assert data['frameworkInterest']['supplierCode'] == 0
        assert data['frameworkInterest']['frameworkSlug'] == 'g-cloud-4'
        assert data['frameworkInterest']['declaration'] == {'an_answer': 'Yes it is'}
        assert data['frameworkInterest']['onFramework'] is True
        assert data['frameworkInterest']['agreementReturned'] is True
        assert data['frameworkInterest']['agreementReturnedAt'] == '2015-10-10T10:10:10.000000+00:00'
        assert data['frameworkInterest']['countersigned'] is True
        assert data['frameworkInterest']['countersignedAt'] == '2015-11-12T13:14:15.000000+00:00'
        assert data['frameworkInterest']['agreementDetails'] == {
            'signerName': 'thing',
            'signerRole': 'thing',
            'uploaderUserId': 20
        }

    def test_get_supplier_framework_info_non_existent_by_framework(self):
        response = self.client.get(
            '/suppliers/0/frameworks/g-cloud-5')

        assert response.status_code == 404

    def test_get_supplier_framework_info_non_existent_by_supplier(self):
        response = self.client.get(
            '/suppliers/123/frameworks/g-cloud-4')

        assert response.status_code == 404

    def test_adding_supplier_has_passed(self):
        response = self.supplier_framework_update(
            0,
            'digital-outcomes-and-specialists',
            update={'onFramework': True}
        )
        assert response.status_code == 200
        data = json.loads(response.get_data())
        assert data['frameworkInterest']['supplierCode'] == 0
        assert data['frameworkInterest']['frameworkSlug'], 'digital-outcomes-and-specialists'
        assert data['frameworkInterest']['onFramework'] is True
        assert data['frameworkInterest']['agreementReturned'] is False
        assert data['frameworkInterest']['agreementReturnedAt'] is None
        assert data['frameworkInterest']['countersigned'] is False
        assert data['frameworkInterest']['countersignedAt'] is None
        assert data['frameworkInterest']['agreementDetails'] is None

    def test_adding_supplier_has_not_passed(self):
        response = self.supplier_framework_update(
            0,
            'digital-outcomes-and-specialists',
            update={'onFramework': False}
        )
        assert response.status_code == 200
        data = json.loads(response.get_data())
        assert data['frameworkInterest']['supplierCode'] == 0
        assert data['frameworkInterest']['frameworkSlug'], 'digital-outcomes-and-specialists'
        assert data['frameworkInterest']['onFramework'] is False

    def test_can_set_agreement_returned_without_agreement_details_for_framework_with_no_agreement_version(self):
        with freeze_time('2012-12-12'):
            response = self.supplier_framework_update(
                0,
                'digital-outcomes-and-specialists',
                update={'agreementReturned': True}
            )
            assert response.status_code == 200, response.get_data()
            data = json.loads(response.get_data())
            assert data['frameworkInterest']['supplierCode'] == 0
            assert data['frameworkInterest']['frameworkSlug'] == 'digital-outcomes-and-specialists'
            assert data['frameworkInterest']['agreementReturned'] is True
            assert data['frameworkInterest']['agreementReturnedAt'] == "2012-12-12T00:00:00.000000+00:00"
            assert data['frameworkInterest']['countersigned'] is False
            assert data['frameworkInterest']['countersignedAt'] is None
            assert data['frameworkInterest']['agreementDetails'] is None

    def test_can_set_agreement_returned_with_agreement_details_for_framework_with_agreement_version(self):
        with freeze_time('2012-12-12'):
            response = self.supplier_framework_update(
                0,
                'g-cloud-8',
                update={
                    'agreementReturned': True,
                    'agreementDetails': {
                        'signerName': 'name',
                        'signerRole': 'role',
                        'uploaderUserId': 1
                    }
                }
            )
            assert response.status_code == 200
            data = json.loads(response.get_data())
            assert data['frameworkInterest']['supplierCode'] == 0
            assert data['frameworkInterest']['frameworkSlug'] == 'g-cloud-8'
            assert data['frameworkInterest']['agreementReturned'] is True
            assert data['frameworkInterest']['agreementReturnedAt'] == "2012-12-12T00:00:00.000000+00:00"
            assert data['frameworkInterest']['countersigned'] is False
            assert data['frameworkInterest']['countersignedAt'] is None
            assert data['frameworkInterest']['agreementDetails'] == {
                'signerName': 'name',
                'signerRole': 'role',
                'uploaderUserEmail': 'test+1@digital.gov.au',
                'uploaderUserId': 1,
                'uploaderUserName': 'my name',
                'frameworkAgreementVersion': 'v1.0'
            }

    def test_can_not_set_agreement_returned_without_agreement_details_for_framework_with_agreement_version(self):
        with freeze_time('2012-12-12'):
            response = self.supplier_framework_update(
                0,
                'g-cloud-8',
                update={'agreementReturned': True}
            )
            assert response.status_code == 400
            data = json.loads(response.get_data())
            assert data['error'] == {
                'uploaderUserId': 'answer_required',
                'signerRole': 'answer_required',
                'signerName': 'answer_required'
            }

    def test_adding_that_agreement_has_been_countersigned(self):
        with freeze_time('2012-12-12'):
            response = self.supplier_framework_update(
                0,
                'digital-outcomes-and-specialists',
                update={'countersigned': True}
            )
            assert response.status_code == 200
            data = json.loads(response.get_data())
            assert data['frameworkInterest']['supplierCode'] == 0
            assert data['frameworkInterest']['frameworkSlug'] == 'digital-outcomes-and-specialists'
            assert data['frameworkInterest']['agreementReturned'] is False
            assert data['frameworkInterest']['agreementReturnedAt'] is None
            assert data['frameworkInterest']['countersigned'] is True
            assert data['frameworkInterest']['countersignedAt'] == "2012-12-12T00:00:00.000000+00:00"
            assert data['frameworkInterest']['agreementDetails'] is None

    def test_agreement_returned_at_timestamp_cannot_be_set(self):
        with freeze_time('2012-12-12'):
            response = self.supplier_framework_update(
                0,
                'digital-outcomes-and-specialists',
                update={'agreementReturned': True, 'agreementReturnedAt': '2013-13-13T00:00:00.000000+00:00'}
            )
            assert response.status_code == 200
            data = json.loads(response.get_data())
            assert data['frameworkInterest']['agreementReturnedAt'] == '2012-12-12T00:00:00.000000+00:00'

    def test_agreement_returned_at_and_agreement_details_are_unset_when_agreement_returned_is_false(self):
        response = self.supplier_framework_update(
            0, 'g-cloud-8',
            update={
                'agreementReturned': True,
                'agreementDetails': {
                    'signerName': 'name',
                    'signerRole': 'role',
                    'uploaderUserId': 1
                }
            })
        data = json.loads(response.get_data())
        assert response.status_code == 200
        assert data['frameworkInterest']['agreementDetails']['frameworkAgreementVersion'] == "v1.0"

        response2 = self.supplier_framework_update(
            0, 'g-cloud-8',
            update={'agreementReturned': False})

        assert response2.status_code == 200
        data2 = json.loads(response2.get_data())
        assert data2['frameworkInterest']['agreementReturned'] is False
        assert data2['frameworkInterest']['agreementReturnedAt'] is None
        assert data2['frameworkInterest']['agreementDetails'] is None

    def test_countersigned_at_timestamp_cannot_be_set(self):
        with freeze_time('2012-12-12'):
            response = self.supplier_framework_update(
                0,
                'digital-outcomes-and-specialists',
                update={
                    'agreementReturned': True,
                    'countersigned': True,
                    'countersignedAt': '2013-13-13T00:00:00.000000+00:00',
                }
            )
            assert response.status_code == 200
            data = json.loads(response.get_data())
            assert data['frameworkInterest']['countersignedAt'] == '2012-12-12T00:00:00.000000+00:00'

    def test_setting_signer_details_and_then_returning_agreement(self):
        agreement_details_payload = {
            "signerName": "name",
            "signerRole": "role",
        }
        response = self.supplier_framework_update(
            0, 'g-cloud-8',
            update={'agreementDetails': agreement_details_payload})

        assert response.status_code == 200
        data = json.loads(response.get_data())
        assert data['frameworkInterest']['agreementDetails'] == agreement_details_payload

        # while we're at it let's test the agreementDetails partial updating behaviour
        agreement_details_update_payload = {
            "uploaderUserId": 1,
        }
        response2 = self.supplier_framework_update(
            0, 'g-cloud-8',
            update={
                'agreementReturned': True,
                'agreementDetails': agreement_details_update_payload
            }
        )

        agreement_details_payload.update(agreement_details_update_payload)
        assert response2.status_code == 200
        data2 = json.loads(response2.get_data())
        assert data2['frameworkInterest']['agreementDetails'] == {
            "signerName": "name",
            "signerRole": "role",
            "uploaderUserId": 1,
            "uploaderUserName": "my name",
            "uploaderUserEmail": "test+1@digital.gov.au",
            "frameworkAgreementVersion": "v1.0",
        }

    def test_can_not_set_agreement_details_on_frameworks_without_framework_agreement_version(self):
        agreement_details_payload = {
            "signerName": "name",
            "signerRole": "role",
            "uploaderUserId": 1,
        }
        response = self.supplier_framework_update(
            0, 'digital-outcomes-and-specialists',
            update={'agreementDetails': agreement_details_payload})

        assert response.status_code == 400
        data = json.loads(response.get_data())
        strings_we_expect_in_the_error_message = [
            'Framework', 'digital-outcomes-and-specialists', 'does not accept', 'agreementDetails']
        for error_string in strings_we_expect_in_the_error_message:
            assert error_string in data['error']

    def test_can_not_set_agreement_details_with_nonexistent_user_id(self):
        agreement_details_payload = {
            "signerName": "name",
            "signerRole": "role",
            "uploaderUserId": 999
        }
        response = self.supplier_framework_update(
            0, 'g-cloud-8',
            update={'agreementDetails': agreement_details_payload})

        data = json.loads(response.get_data())
        assert response.status_code == 400
        strings_we_expect_in_the_error_message = [
            'No user found with id', '999']
        for error_string in strings_we_expect_in_the_error_message:
            assert error_string in data['error']

    def test_schema_validation_fails_if_unknown_fields_present_in_agreement_details(self):
        agreement_details_payload = {
            "signerName": "Normal Person",
            "disallowedKey": "value",
        }
        response = self.supplier_framework_update(
            0, 'g-cloud-8',
            update={'agreementDetails': agreement_details_payload}
        )

        assert response.status_code == 400
        data = json.loads(response.get_data())
        # split assertions into keyphrases due to nested unicode string in python 2
        strings_we_expect_in_the_error_message = [
            'Additional properties are not allowed', 'disallowedKey', 'was unexpected']
        for error_string in strings_we_expect_in_the_error_message:
            assert error_string in data['error']['_form'][0]

    def test_schema_validation_fails_if_empty_object_sent_as_agreement_details(self):
        response = self.supplier_framework_update(
            0, 'g-cloud-8',
            update={'agreementDetails': {}}
        )

        assert response.status_code == 400
        data = json.loads(response.get_data())
        error_message = '{} does not have enough properties'
        assert error_message in data['error']['_form'][0]

    def test_schema_validation_fails_if_empty_strings_sent_as_agreement_details(self):
        agreement_details_payload = {
            "signerName": "",
            "signerRole": "",
        }
        response = self.supplier_framework_update(
            0, 'g-cloud-8',
            update={'agreementDetails': agreement_details_payload}
        )

        assert response.status_code == 400
        data = json.loads(response.get_data())
        expected_error_dict = {'signerName': 'answer_required', 'signerRole': 'answer_required'}
        assert expected_error_dict == data['error']

    def test_cannot_save_if_required_signer_field_is_missing_from_not_yet_set_agreement_details(self):
        # missing signerRole
        agreement_details_payload = {
            "signerName": "name",
        }
        response = self.supplier_framework_update(
            0, 'g-cloud-8',
            update={'agreementDetails': agreement_details_payload}
        )

        assert response.status_code == 400
        data = json.loads(response.get_data())
        expected_error_dict = {'signerRole': 'answer_required'}
        assert expected_error_dict == data['error']

    def test_cannot_return_agreement_if_signer_details_fields_are_missing_from_agreement_details(self):
        # missing signerName and signerRole
        agreement_details_payload = {
            "uploaderUserId": 1,
        }
        response = self.supplier_framework_update(
            0, 'g-cloud-8',
            update={
                'agreementReturned': True,
                'agreementDetails': agreement_details_payload
            }
        )

        assert response.status_code == 400
        data = json.loads(response.get_data())
        expected_error_dict = {'signerName': 'answer_required', 'signerRole': 'answer_required'}
        assert expected_error_dict == data['error']

    def test_can_manually_override_framework_agreement_version_for_returned_framework_agreement(self):
        response = self.supplier_framework_update(
            0,
            'g-cloud-8',
            update={
                'agreementReturned': True,
                'agreementDetails': {
                    'signerName': 'name',
                    'signerRole': 'role',
                    'uploaderUserId': 1
                }
            }
        )
        assert response.status_code == 200
        data = json.loads(response.get_data())
        assert data['frameworkInterest']['agreementDetails']['frameworkAgreementVersion'] == 'v1.0'

        response2 = self.supplier_framework_update(
            0, 'g-cloud-8',
            update={'agreementDetails': {'frameworkAgreementVersion': 'v2.0'}}
        )
        assert response2.status_code == 200
        data2 = json.loads(response2.get_data())
        assert data2['frameworkInterest']['agreementDetails']['frameworkAgreementVersion'] == 'v2.0'

    def test_changing_on_framework_from_failed_to_passed(self):
        response = self.supplier_framework_update(
            0,
            'digital-outcomes-and-specialists',
            update={'onFramework': False}
        )
        assert response.status_code == 200
        data = json.loads(response.get_data())
        assert data['frameworkInterest']['onFramework'] is False
        assert data['frameworkInterest']['agreementReturned'] is False

        response2 = self.supplier_framework_update(
            0,
            'digital-outcomes-and-specialists',
            update={'onFramework': True}
        )
        assert response2.status_code, 200
        data = json.loads(response2.get_data())
        assert data['frameworkInterest']['onFramework'] is True
        assert data['frameworkInterest']['agreementReturned'] is False

    def test_changing_on_framework_from_passed_to_failed(self):
        response = self.supplier_framework_update(
            0,
            'digital-outcomes-and-specialists',
            update={'onFramework': True}
        )
        assert response.status_code == 200
        data = json.loads(response.get_data())
        assert data['frameworkInterest']['onFramework'] is True
        assert data['frameworkInterest']['agreementReturned'] is False

        response2 = self.supplier_framework_update(
            0,
            'digital-outcomes-and-specialists',
            update={'onFramework': False}
        )
        assert response2.status_code == 200
        data = json.loads(response2.get_data())
        assert data['frameworkInterest']['onFramework'] is False
        assert data['frameworkInterest']['agreementReturned'] is False

    def test_changing_on_framework_to_passed_creates_audit_event(self):
        self.supplier_framework_update(
            0,
            'digital-outcomes-and-specialists',
            update={'onFramework': True, 'agreementReturned': True}
        )
        with self.app.app_context():
            supplier = Supplier.query.filter(
                Supplier.code == 0
            ).first()

            audit = AuditEvent.query.filter(
                AuditEvent.object == supplier,
                AuditEvent.type == "supplier_update"
            ).first()
            assert audit.type == "supplier_update"
            assert audit.user == "interested@example.com"
            assert audit.data['supplierId'] == 0
            assert audit.data['frameworkSlug'] == 'digital-outcomes-and-specialists'
            assert audit.data['update']['onFramework'] is True
            assert audit.data['update']['agreementReturned'] is True


class TestSupplierApplication(BaseApplicationTest):
    def setup(self):
        super(TestSupplierApplication, self).setup()
        with self.app.app_context():
            payload = self.load_example_listing("Supplier")
            self.supplier = payload
            self.supplier_code = payload['code']

            response = self.client.post(
                '/suppliers'.format(self.supplier_code),
                data=json.dumps({
                    'supplier': self.supplier
                }),
                content_type='application/json')
            json.loads(response.get_data())
            assert_equal(response.status_code, 201)

    @mock.patch('app.tasks.publish_tasks.application')
    def test_supplier_already_has_application(self, application):
        application_id = self.setup_dummy_application()

        with self.app.app_context():
            response = self.client.patch(
                '/applications/{}'.format(application_id),
                data=json.dumps({
                    'application': {'status': 'saved', 'supplier_code': self.supplier_code},
                }),
                content_type='application/json')

            response = self.client.post(
                '/suppliers/{}/application'.format(self.supplier_code),
                data=json.dumps({'current_user': ''}),
                content_type='application/json'
            )

            assert response.status_code == 200
            data = json.loads(response.get_data())
            assert 'application' in data
            assert six.viewitems(self.application_data) <= six.viewitems(data['application'])
            assert application.delay.called is True

    @mock.patch('app.tasks.publish_tasks.application')
    def test_supplier_create_application(self, application_task):
        with self.app.app_context():
            user = User(
                id=1,
                email_address="test+1@digital.gov.au".format(id),
                name="my name",
                password="fake password",
                active=True,
                role='supplier',
                password_changed_at=utcnow(),
                supplier_code=self.supplier_code
            )
            db.session.add(user)
            db.session.commit()

            response = self.client.post(
                '/suppliers/{}/application'.format(self.supplier_code),
                data=json.dumps({'current_user': {
                    'name': 'my name',
                    'email_address': 'test+1@digital.gov.au'}
                }),
                content_type='application/json'
            )

            assert response.status_code == 200
            data = json.loads(response.get_data())
            assert 'application' in data
            application = data['application']
            assert application['status'] == 'saved'
            assert application['type'] == 'upgrade'
            assert application_task.delay.called is True

            user = User.query.filter(User.id == 1).first()
            assert user.application_id == application['id']

            supplier = Supplier.query.filter(Supplier.code == self.supplier_code).first()
            assert supplier.data['application_id'] == application['id']

            audit = AuditEvent.query.filter(
                AuditEvent.type == "create_application"
            ).first()
            assert audit.object_id == application['id']
