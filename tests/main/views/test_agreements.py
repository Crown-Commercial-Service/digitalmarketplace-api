import json
from datetime import datetime
from freezegun import freeze_time
from app.models import AuditEvent, db, Framework, FrameworkAgreement, User
from tests.helpers import fixture_params
from tests.bases import BaseApplicationTest


class BaseFrameworkAgreementTest(BaseApplicationTest):
    def create_agreement(self, supplier_framework, **framework_agreement_kwargs):
        framework = Framework.query.filter(Framework.slug == supplier_framework['frameworkSlug']).first()

        agreement = FrameworkAgreement(
            supplier_id=supplier_framework['supplierId'],
            framework_id=framework.id,
            **framework_agreement_kwargs)
        db.session.add(agreement)
        db.session.commit()

        return agreement.id


class TestCreateFrameworkAgreement(BaseApplicationTest):
    def post_create_agreement(self, supplier_id=None, framework_slug=None):
        agreement_data = {}
        if supplier_id:
            agreement_data['supplierId'] = supplier_id
        if framework_slug:
            agreement_data['frameworkSlug'] = framework_slug

        return self.client.post(
            '/agreements',
            data=json.dumps(
                {
                    'updated_by': 'interested@example.com',
                    'agreement': agreement_data
                }),
            content_type='application/json')

    def test_can_create_framework_agreement(self, supplier_framework):
        res = self.post_create_agreement(
            supplier_id=supplier_framework['supplierId'],
            framework_slug=supplier_framework['frameworkSlug']
        )

        assert res.status_code == 201

        res_agreement_json = json.loads(res.get_data(as_text=True))['agreement']
        assert res_agreement_json['id'] > 0
        assert res_agreement_json['supplierId'] == supplier_framework['supplierId']
        assert res_agreement_json['frameworkSlug'] == supplier_framework['frameworkSlug']
        assert res_agreement_json['status'] == 'draft'

        res2 = self.client.get('/agreements/{}'.format(res_agreement_json['id']))

        assert res2.status_code == 200
        assert json.loads(res2.get_data(as_text=True))['agreement'] == res_agreement_json

    def test_create_framework_agreement_makes_an_audit_event(self, supplier_framework):
        res = self.post_create_agreement(
            supplier_id=supplier_framework['supplierId'],
            framework_slug=supplier_framework['frameworkSlug']
        )

        assert res.status_code == 201

        agreement_id = json.loads(res.get_data(as_text=True))['agreement']['id']

        agreement = FrameworkAgreement.query.filter(
            FrameworkAgreement.id == agreement_id
        ).first()

        audit = AuditEvent.query.filter(
            AuditEvent.object == agreement
        ).first()

        assert audit.type == "create_agreement"
        assert audit.user == "interested@example.com"
        assert audit.data == {
            'supplierId': supplier_framework['supplierId'],
            'frameworkSlug': supplier_framework['frameworkSlug']
        }

    def test_404_if_creating_framework_agreement_with_no_supplier_framework(self, supplier_framework):
        res = self.post_create_agreement(
            supplier_id=7,
            framework_slug='dos'
        )

        assert res.status_code == 404
        assert json.loads(res.get_data(as_text=True))['error'] == "supplier_id '7' is not on framework 'dos'"

    @fixture_params('supplier_framework', {'on_framework': False})
    def test_404_if_creating_framework_agreement_with_supplier_framework_not_on_framework(self, supplier_framework):
        res = self.post_create_agreement(
            supplier_id=supplier_framework['supplierId'],
            framework_slug=supplier_framework['frameworkSlug']
        )

        assert res.status_code == 404
        assert (
            json.loads(res.get_data(as_text=True))['error'] ==
            "supplier_id '{}' is not on framework '{}'".format(
                supplier_framework['supplierId'], supplier_framework['frameworkSlug']
            )
        )

    def test_can_not_create_framework_agreement_if_no_supplier_id_provided(self, supplier_framework):
        res = self.post_create_agreement(
            framework_slug=supplier_framework['frameworkSlug']
        )

        assert res.status_code == 400
        assert (
            json.loads(res.get_data(as_text=True))['error'] ==
            "Invalid JSON must have 'supplierId' keys"
        )

    def test_can_not_create_framework_agreement_if_no_framework_slug_provided(self, supplier_framework):
        res = self.post_create_agreement(
            supplier_id=supplier_framework['supplierId']
        )

        assert res.status_code == 400
        assert (
            json.loads(res.get_data(as_text=True))['error'] ==
            "Invalid JSON must have 'frameworkSlug' keys"
        )


class TestGetFrameworkAgreement(BaseFrameworkAgreementTest):
    def test_it_gets_a_newly_created_framework_agreement_by_id(self, supplier_framework):
        agreement_id = self.create_agreement(
            supplier_framework
        )
        res = self.client.get('/agreements/{}'.format(agreement_id))

        assert res.status_code == 200
        assert json.loads(res.get_data(as_text=True))['agreement'] == {
            'id': agreement_id,
            'supplierId': supplier_framework['supplierId'],
            'frameworkSlug': supplier_framework['frameworkSlug'],
            'status': 'draft'
        }

    def test_it_returns_a_framework_agreement_with_details_only(self, supplier_framework):
        agreement_id = self.create_agreement(
            supplier_framework,
            signed_agreement_details={'details': 'here'}
        )
        res = self.client.get('/agreements/{}'.format(agreement_id))

        assert res.status_code == 200
        assert json.loads(res.get_data(as_text=True))['agreement'] == {
            'id': agreement_id,
            'supplierId': supplier_framework['supplierId'],
            'frameworkSlug': supplier_framework['frameworkSlug'],
            'signedAgreementDetails': {'details': 'here'},
            'status': 'draft'
        }

    def test_it_gets_a_signed_framework_agreement_by_id(self, supplier_framework):
        agreement_id = self.create_agreement(
            supplier_framework,
            signed_agreement_returned_at=datetime(2016, 10, 1, 1, 1, 1),
            signed_agreement_details={'details': 'here'},
            signed_agreement_path='path'
        )
        res = self.client.get('/agreements/{}'.format(agreement_id))

        assert res.status_code == 200
        assert json.loads(res.get_data(as_text=True))['agreement'] == {
            'id': agreement_id,
            'supplierId': supplier_framework['supplierId'],
            'frameworkSlug': supplier_framework['frameworkSlug'],
            'status': 'signed',
            'signedAgreementDetails': {'details': 'here'},
            'signedAgreementPath': 'path',
            'signedAgreementReturnedAt': '2016-10-01T01:01:01.000000Z',
        }

    def test_it_gets_an_on_hold_framework_agreement_by_id(self, supplier_framework):
        agreement_id = self.create_agreement(
            supplier_framework,
            signed_agreement_returned_at=datetime(2016, 10, 1, 1, 1, 1),
            signed_agreement_details={'details': 'here'},
            signed_agreement_path='path',
            signed_agreement_put_on_hold_at=datetime(2016, 11, 1, 1, 1, 1),
        )
        res = self.client.get('/agreements/{}'.format(agreement_id))

        assert res.status_code == 200
        assert json.loads(res.get_data(as_text=True))['agreement'] == {
            'id': agreement_id,
            'supplierId': supplier_framework['supplierId'],
            'frameworkSlug': supplier_framework['frameworkSlug'],
            'status': 'on-hold',
            'signedAgreementDetails': {'details': 'here'},
            'signedAgreementPath': 'path',
            'signedAgreementReturnedAt': '2016-10-01T01:01:01.000000Z',
            'signedAgreementPutOnHoldAt': '2016-11-01T01:01:01.000000Z',
        }

    def test_it_gets_an_approved_framework_agreement_by_id(self, supplier_framework):
        agreement_id = self.create_agreement(
            supplier_framework,
            signed_agreement_returned_at=datetime(2016, 10, 1, 1, 1, 1),
            signed_agreement_details={'details': 'here'},
            signed_agreement_path='path',
            countersigned_agreement_details={'countersigneddetails': 'here'},
            countersigned_agreement_returned_at=datetime(2016, 11, 1, 1, 1, 1),
        )
        res = self.client.get('/agreements/{}'.format(agreement_id))

        assert res.status_code == 200
        assert json.loads(res.get_data(as_text=True))['agreement'] == {
            'id': agreement_id,
            'supplierId': supplier_framework['supplierId'],
            'frameworkSlug': supplier_framework['frameworkSlug'],
            'status': 'approved',
            'signedAgreementDetails': {'details': 'here'},
            'signedAgreementPath': 'path',
            'signedAgreementReturnedAt': '2016-10-01T01:01:01.000000Z',
            'countersignedAgreementDetails': {'countersigneddetails': 'here'},
            'countersignedAgreementReturnedAt': '2016-11-01T01:01:01.000000Z',
        }

    def test_it_gets_a_countersigned_framework_agreement_by_id(self, supplier_framework):
        agreement_id = self.create_agreement(
            supplier_framework,
            signed_agreement_returned_at=datetime(2016, 10, 1, 1, 1, 1),
            signed_agreement_details={'details': 'here'},
            signed_agreement_path='path',
            countersigned_agreement_details={'countersigneddetails': 'here'},
            countersigned_agreement_returned_at=datetime(2016, 11, 1, 1, 1, 1),
            countersigned_agreement_path='path'
        )
        res = self.client.get('/agreements/{}'.format(agreement_id))

        assert res.status_code == 200
        assert json.loads(res.get_data(as_text=True))['agreement'] == {
            'id': agreement_id,
            'supplierId': supplier_framework['supplierId'],
            'frameworkSlug': supplier_framework['frameworkSlug'],
            'status': 'countersigned',
            'signedAgreementDetails': {'details': 'here'},
            'signedAgreementPath': 'path',
            'signedAgreementReturnedAt': '2016-10-01T01:01:01.000000Z',
            'countersignedAgreementDetails': {'countersigneddetails': 'here'},
            'countersignedAgreementReturnedAt': '2016-11-01T01:01:01.000000Z',
            'countersignedAgreementPath': 'path'
        }

    def test_it_gets_a_countersigned_and_uploaded_framework_agreement_by_id(self, supplier_framework):
        agreement_id = self.create_agreement(
            supplier_framework,
            signed_agreement_returned_at=datetime(2016, 10, 1, 1, 1, 1),
            signed_agreement_details={'details': 'here'},
            signed_agreement_path='path',
            countersigned_agreement_details={'countersigneddetails': 'here'},
            countersigned_agreement_returned_at=datetime(2016, 11, 1, 1, 1, 1),
            countersigned_agreement_path='/example.pdf'
        )
        res = self.client.get('/agreements/{}'.format(agreement_id))

        assert res.status_code == 200
        assert json.loads(res.get_data(as_text=True))['agreement'] == {
            'id': agreement_id,
            'supplierId': supplier_framework['supplierId'],
            'frameworkSlug': supplier_framework['frameworkSlug'],
            'status': 'countersigned',
            'signedAgreementDetails': {'details': 'here'},
            'signedAgreementPath': 'path',
            'signedAgreementReturnedAt': '2016-10-01T01:01:01.000000Z',
            'countersignedAgreementDetails': {'countersigneddetails': 'here'},
            'countersignedAgreementReturnedAt': '2016-11-01T01:01:01.000000Z',
            'countersignedAgreementPath': '/example.pdf'
        }


class TestUpdateFrameworkAgreement(BaseFrameworkAgreementTest):
    def post_agreement_update(self, agreement_id, agreement):
        return self.client.post(
            '/agreements/{}'.format(agreement_id),
            data=json.dumps(
                {
                    'updated_by': 'interested@example.com',
                    'agreement': agreement
                }),
            content_type='application/json')

    @fixture_params('live_example_framework', {'framework_agreement_details': None})
    def test_cant_set_agreement_details_for_framework_without_agreement_version(self, supplier_framework):
        agreement_id = self.create_agreement(supplier_framework)
        res = self.client.post(
            '/agreements/{}'.format(agreement_id),
            data=json.dumps(
                {
                    'updated_by': 'interested@example.com',
                    'agreement': {
                        'signedAgreementDetails': {
                            'signerName': 'name',
                            'signerRole': 'role',
                        }
                    }
                }),
            content_type='application/json')

        assert res.status_code == 400
        assert (
            json.loads(res.get_data(as_text=True))['error'] ==
            "Can not update signedAgreementDetails for a framework agreement without a frameworkAgreementVersion"
        )

    @fixture_params('live_example_framework', {'framework_agreement_details': {'frameworkAgreementVersion': 'v1.0'}})
    def test_can_update_framework_agreement_details(self, supplier_framework):
        agreement_id = self.create_agreement(supplier_framework)
        res = self.post_agreement_update(agreement_id, {
            'signedAgreementDetails': {
                'signerName': 'name',
                'signerRole': 'role',
            }
        })

        assert res.status_code == 200
        data = json.loads(res.get_data(as_text=True))

        expected_agreement_json = {
            'id': agreement_id,
            'supplierId': supplier_framework['supplierId'],
            'frameworkSlug': supplier_framework['frameworkSlug'],
            'status': 'draft',
            'signedAgreementDetails': {
                'signerName': 'name',
                'signerRole': 'role',
            }
        }
        assert data['agreement'] == expected_agreement_json

        res2 = self.client.get('/agreements/{}'.format(agreement_id))
        assert res2.status_code == 200
        assert json.loads(res2.get_data(as_text=True))['agreement'] == expected_agreement_json

    @fixture_params('live_example_framework', {'framework_agreement_details': {'frameworkAgreementVersion': 'v1.0'}})
    def test_can_update_signed_agreement_path(self, supplier_framework):
        agreement_id = self.create_agreement(supplier_framework)
        res = self.post_agreement_update(agreement_id, {
            'signedAgreementPath': '/example.pdf'
        })

        assert res.status_code == 200
        data = json.loads(res.get_data(as_text=True))

        expected_agreement_json = {
            'id': agreement_id,
            'supplierId': supplier_framework['supplierId'],
            'frameworkSlug': supplier_framework['frameworkSlug'],
            'status': 'draft',
            'signedAgreementPath': '/example.pdf'
        }
        assert data['agreement'] == expected_agreement_json

        res2 = self.client.get('/agreements/{}'.format(agreement_id))
        assert res2.status_code == 200
        assert json.loads(res2.get_data(as_text=True))['agreement'] == expected_agreement_json

    @fixture_params('live_example_framework', {'framework_agreement_details': {'frameworkAgreementVersion': 'v1.0'}})
    def test_can_update_signed_agreement_details_and_signed_agreement_path(self, supplier_framework):
        agreement_id = self.create_agreement(supplier_framework)
        res = self.post_agreement_update(agreement_id, {
            'signedAgreementDetails': {
                'signerName': 'name',
                'signerRole': 'role',
            },
            'signedAgreementPath': '/example.pdf'
        })

        assert res.status_code == 200
        data = json.loads(res.get_data(as_text=True))

        expected_agreement_json = {
            'id': agreement_id,
            'supplierId': supplier_framework['supplierId'],
            'frameworkSlug': supplier_framework['frameworkSlug'],
            'status': 'draft',
            'signedAgreementPath': '/example.pdf',
            'signedAgreementDetails': {
                'signerName': 'name',
                'signerRole': 'role',
            }
        }
        assert data['agreement'] == expected_agreement_json

        res2 = self.client.get('/agreements/{}'.format(agreement_id))
        assert res2.status_code == 200
        assert json.loads(res2.get_data(as_text=True))['agreement'] == expected_agreement_json

    @fixture_params('live_example_framework', {'framework_agreement_details': {'frameworkAgreementVersion': 'v1.0'}})
    def test_audit_event_created_when_updating_framework_agreement(self, supplier_framework):
        agreement_id = self.create_agreement(supplier_framework)
        res = self.post_agreement_update(agreement_id, {
            'signedAgreementDetails': {
                'signerName': 'name',
                'signerRole': 'role',
            },
            'signedAgreementPath': '/example.pdf'
        })

        assert res.status_code == 200

        agreement = FrameworkAgreement.query.filter(
            FrameworkAgreement.id == agreement_id
        ).first()

        audit = AuditEvent.query.filter(
            AuditEvent.object == agreement
        ).first()

        assert audit.type == "update_agreement"
        assert audit.user == "interested@example.com"
        assert audit.data == {
            'supplierId': supplier_framework['supplierId'],
            'frameworkSlug': supplier_framework['frameworkSlug'],
            'update': {
                'signedAgreementDetails': {
                    'signerName': 'name',
                    'signerRole': 'role',
                },
                'signedAgreementPath': '/example.pdf'
            }
        }

    @fixture_params('live_example_framework', {'framework_agreement_details': {'frameworkAgreementVersion': 'v1.0'}})
    def test_can_not_set_framework_agreement_version_directly(self, supplier_framework):
        agreement_id = self.create_agreement(supplier_framework)
        res = self.post_agreement_update(agreement_id, {
            'frameworkAgreementVersion': 'v23.4'
        })
        assert res.status_code == 400
        assert json.loads(res.get_data(as_text=True)) == {
            'error': "Invalid JSON should not have 'frameworkAgreementVersion' keys"
        }

    @fixture_params('live_example_framework', {'framework_agreement_details': {'frameworkAgreementVersion': 'v1.0'}})
    def test_agreement_returned_at_timestamp_cannot_be_set(self, supplier_framework):
        agreement_id = self.create_agreement(supplier_framework)
        res = self.post_agreement_update(agreement_id, {
            'signedAgreementReturnedAt': '2013-13-13T00:00:00.000000Z'
        })

        assert res.status_code == 400
        assert json.loads(res.get_data(as_text=True)) == {
            'error': "Invalid JSON should not have 'signedAgreementReturnedAt' keys"
        }

    @fixture_params('live_example_framework', {'framework_agreement_details': {'frameworkAgreementVersion': 'v1.0'}})
    def test_400_cannot_update_signed_agreement(self, supplier_framework):
        agreement_id = self.create_agreement(supplier_framework, signed_agreement_returned_at=datetime.utcnow())
        res = self.post_agreement_update(agreement_id, {
            'signedAgreementPath': '/example.pdf'
        })

        assert res.status_code == 400
        assert json.loads(res.get_data(as_text=True)) == {
            'error': 'Can not update signedAgreementDetails or signedAgreementPath if agreement has been signed'
        }

    @fixture_params('live_example_framework', {'framework_agreement_details': {'frameworkAgreementVersion': 'v1.0'}})
    def test_400_if_unknown_field_present_in_update_json(self, supplier_framework):
        agreement_id = self.create_agreement(supplier_framework)
        res = self.post_agreement_update(agreement_id, {
            'signedRandomKey': 'banana'
        })

        assert res.status_code == 400
        assert json.loads(res.get_data(as_text=True)) == {
            'error': "Invalid JSON should not have 'signedRandomKey' keys"
        }

    @fixture_params('live_example_framework', {'framework_agreement_details': {'frameworkAgreementVersion': 'v1.0'}})
    def test_400_if_unknown_field_present_in_signed_agreement_details(self, supplier_framework):
        agreement_id = self.create_agreement(supplier_framework)
        res = self.post_agreement_update(agreement_id, {
            'signedAgreementDetails': {
                'signerName': 'name',
                'randomKey': 'value',
            }
        })

        assert res.status_code == 400

        data = json.loads(res.get_data(as_text=True))
        # split assertions into keyphrases due to nested unicode string in python 2
        strings_we_expect_in_the_error_message = [
            'Additional properties are not allowed', 'randomKey', 'was unexpected']
        for error_string in strings_we_expect_in_the_error_message:
            assert error_string in data['error']['_form'][0]

    @fixture_params('live_example_framework', {'framework_agreement_details': {'frameworkAgreementVersion': 'v1.0'}})
    def test_200_if_signed_agreement_details_is_empty_object(self, supplier_framework):
        agreement_id = self.create_agreement(supplier_framework)
        res = self.post_agreement_update(agreement_id, {'signedAgreementDetails': {}})

        assert res.status_code == 200

    @fixture_params('live_example_framework', {'framework_agreement_details': {'frameworkAgreementVersion': 'v1.0'}})
    def test_400_if_signed_agreement_details_contains_empty_strings_as_values(self, supplier_framework):
        agreement_id = self.create_agreement(supplier_framework)
        res = self.post_agreement_update(agreement_id, {
            'signedAgreementDetails': {
                'signerName': '',
                'signerRole': '',
            }
        })

        assert res.status_code == 400

        assert json.loads(res.get_data(as_text=True)) == {
            'error': {'signerName': 'answer_required', 'signerRole': 'answer_required'}
        }

    @fixture_params('live_example_framework', {'framework_agreement_details': {'frameworkAgreementVersion': 'v1.0'}})
    def test_can_update_countersigned_agreement_path_for_framework_with_agreement_version(self, supplier_framework):
        agreement_id = self.create_agreement(
            supplier_framework,
            signed_agreement_details={
                'signerName': 'name',
                'signerRole': 'role',
            },
            signed_agreement_path='path/file.pdf',
            signed_agreement_returned_at=datetime(2016, 10, 1, 1, 1, 1),
            countersigned_agreement_returned_at=datetime(2016, 11, 1, 1, 1, 1)
        )
        res = self.post_agreement_update(agreement_id, {
            'countersignedAgreementPath': 'countersigned/file.jpg'
        })

        assert res.status_code == 200
        data = json.loads(res.get_data(as_text=True))

        expected_agreement_json = {
            'id': agreement_id,
            'supplierId': supplier_framework['supplierId'],
            'frameworkSlug': supplier_framework['frameworkSlug'],
            'status': 'countersigned',
            'signedAgreementPath': 'path/file.pdf',
            'signedAgreementDetails': {
                'signerName': 'name',
                'signerRole': 'role',
            },
            'signedAgreementReturnedAt': '2016-10-01T01:01:01.000000Z',
            'countersignedAgreementReturnedAt': '2016-11-01T01:01:01.000000Z',
            'countersignedAgreementPath': 'countersigned/file.jpg'
        }
        assert data['agreement'] == expected_agreement_json

        res2 = self.client.get('/agreements/{}'.format(agreement_id))
        assert res2.status_code == 200
        assert json.loads(res2.get_data(as_text=True))['agreement'] == expected_agreement_json

    @fixture_params('live_example_framework', {'framework_agreement_details': None})
    def test_can_update_countersigned_agreement_path_for_framework_without_agreement_version(self, supplier_framework):
        agreement_id = self.create_agreement(
            supplier_framework,
            signed_agreement_path='path/file.pdf',
            signed_agreement_returned_at=datetime(2016, 10, 1, 1, 1, 1),
            countersigned_agreement_returned_at=datetime(2016, 11, 1, 1, 1, 1)
        )
        res = self.post_agreement_update(agreement_id, {
            'countersignedAgreementPath': 'countersigned/file.jpg'
        })

        assert res.status_code == 200
        data = json.loads(res.get_data(as_text=True))

        expected_agreement_json = {
            'id': agreement_id,
            'supplierId': supplier_framework['supplierId'],
            'frameworkSlug': supplier_framework['frameworkSlug'],
            'status': 'countersigned',
            'signedAgreementPath': 'path/file.pdf',
            'signedAgreementReturnedAt': '2016-10-01T01:01:01.000000Z',
            'countersignedAgreementReturnedAt': '2016-11-01T01:01:01.000000Z',
            'countersignedAgreementPath': 'countersigned/file.jpg'
        }
        assert data['agreement'] == expected_agreement_json

        res2 = self.client.get('/agreements/{}'.format(agreement_id))
        assert res2.status_code == 200
        assert json.loads(res2.get_data(as_text=True))['agreement'] == expected_agreement_json

    def test_cannot_update_countersigned_agreement_path_if_agreement_has_not_been_approved(self, supplier_framework):
        agreement_id = self.create_agreement(
            supplier_framework,
            signed_agreement_path='path/file.pdf',
            signed_agreement_returned_at=datetime(2016, 10, 1, 1, 1, 1)
        )
        res = self.post_agreement_update(agreement_id, {
            'countersignedAgreementPath': 'countersigned/file.jpg'
        })

        assert res.status_code == 400
        assert json.loads(res.get_data(as_text=True)) == {
            'error': 'Can not update countersignedAgreementPath if agreement has not been approved for countersigning'
        }

    @fixture_params(
        'live_example_framework', {
            'framework_agreement_details': {'frameworkAgreementVersion': 'v1.0'},
            'slug': 'g-cloud-12',
            'framework_live_at_utc': '2020-09-28T09:00:00.000000Z',  # Past the G12 go-live date
        }
    )
    def test_can_update_countersigned_agreement_path_without_approval_for_esignature_framework(
        self, supplier_framework
    ):
        agreement_id = self.create_agreement(
            supplier_framework,
            signed_agreement_path='path/file.pdf',
            signed_agreement_returned_at=datetime(2016, 10, 1, 1, 1, 1)
        )
        res = self.post_agreement_update(agreement_id, {
            'countersignedAgreementPath': 'countersigned/file.jpg'
        })

        assert res.status_code == 200
        data = json.loads(res.get_data(as_text=True))

        expected_agreement_json = {
            'id': agreement_id,
            'supplierId': supplier_framework['supplierId'],
            'frameworkSlug': supplier_framework['frameworkSlug'],
            'status': 'countersigned',
            'signedAgreementPath': 'path/file.pdf',
            'signedAgreementReturnedAt': '2016-10-01T01:01:01.000000Z',
            'countersignedAgreementPath': 'countersigned/file.jpg'
        }
        assert data['agreement'] == expected_agreement_json

        res2 = self.client.get('/agreements/{}'.format(agreement_id))
        assert res2.status_code == 200
        assert json.loads(res2.get_data(as_text=True))['agreement'] == expected_agreement_json

    def test_can_unset_countersigned_agreement_path(self, supplier_framework):
        agreement_id = self.create_agreement(
            supplier_framework,
            signed_agreement_path='path/file.pdf',
            signed_agreement_returned_at=datetime(2016, 10, 1, 1, 1, 1),
            countersigned_agreement_returned_at=datetime(2016, 11, 1, 1, 1, 1),
            countersigned_agreement_path='countersigned/that/bad/boy.pdf'
        )
        res = self.post_agreement_update(agreement_id, {
            'countersignedAgreementPath': None
        })

        assert res.status_code == 200
        data = json.loads(res.get_data(as_text=True))

        expected_agreement_json = {
            'id': agreement_id,
            'supplierId': supplier_framework['supplierId'],
            'frameworkSlug': supplier_framework['frameworkSlug'],
            'status': 'approved',
            'signedAgreementPath': 'path/file.pdf',
            'signedAgreementReturnedAt': '2016-10-01T01:01:01.000000Z',
            'countersignedAgreementReturnedAt': '2016-11-01T01:01:01.000000Z'
        }
        assert data['agreement'] == expected_agreement_json

        res2 = self.client.get('/agreements/{}'.format(agreement_id))
        assert res2.status_code == 200
        assert json.loads(res2.get_data(as_text=True))['agreement'] == expected_agreement_json


@fixture_params('live_example_framework', {'framework_agreement_details': {'frameworkAgreementVersion': 'v1.0'}})
class TestSignFrameworkAgreementThatHasFrameworkAgreementVersion(BaseFrameworkAgreementTest):
    def sign_agreement(self, agreement_id, agreement):
        return self.client.post(
            '/agreements/{}/sign'.format(agreement_id),
            data=json.dumps(
                {
                    'updated_by': 'interested@example.com',
                    'agreement': agreement
                }),
            content_type='application/json')

    def test_can_sign_framework_agreement(self, user_role_supplier, supplier_framework):
        agreement_id = self.create_agreement(
            supplier_framework,
            signed_agreement_details={'signerName': 'name', 'signerRole': 'role'},
            signed_agreement_path='/example.pdf'
        )
        with freeze_time('2016-12-12'):
            res = self.sign_agreement(agreement_id, {'signedAgreementDetails': {'uploaderUserId': 1}})
            assert res.status_code == 200

            data = json.loads(res.get_data(as_text=True))
            assert data['agreement'] == {
                'id': agreement_id,
                'supplierId': supplier_framework['supplierId'],
                'frameworkSlug': supplier_framework['frameworkSlug'],
                'status': 'signed',
                'signedAgreementPath': '/example.pdf',
                'signedAgreementDetails': {
                    'signerName': 'name',
                    'signerRole': 'role',
                    'uploaderUserId': user_role_supplier,
                    'frameworkAgreementVersion': 'v1.0'
                },
                'signedAgreementReturnedAt': '2016-12-12T00:00:00.000000Z'
            }

    def test_signing_framework_agreement_produces_audit_event(self, user_role_supplier, supplier_framework):
        agreement_id = self.create_agreement(
            supplier_framework,
            signed_agreement_details={'signerName': 'name', 'signerRole': 'role'},
            signed_agreement_path='/example.pdf'
        )
        res = self.sign_agreement(agreement_id, {'signedAgreementDetails': {'uploaderUserId': user_role_supplier}})
        assert res.status_code == 200

        agreement = FrameworkAgreement.query.filter(
            FrameworkAgreement.id == agreement_id
        ).first()

        audit = AuditEvent.query.filter(
            AuditEvent.object == agreement
        ).first()

        assert audit.type == "sign_agreement"
        assert audit.user == "interested@example.com"
        assert audit.data == {
            'supplierId': supplier_framework['supplierId'],
            'frameworkSlug': supplier_framework['frameworkSlug'],
            'update': {'signedAgreementDetails': {'uploaderUserId': user_role_supplier}}
        }

    def test_can_re_sign_framework_agreement(self, user_role_supplier, supplier_framework):
        agreement_id = self.create_agreement(
            supplier_framework,
            signed_agreement_details={
                'signerName': 'name',
                'signerRole': 'role',
                'uploaderUserId': 2,
                'frameworkAgreementVersion': 'v1.0'
            },
            signed_agreement_path='/example.pdf',
            signed_agreement_returned_at=datetime.utcnow()
        )
        with freeze_time('2016-12-12'):
            res = self.sign_agreement(agreement_id, {'signedAgreementDetails': {'uploaderUserId': user_role_supplier}})
            assert res.status_code == 200

            data = json.loads(res.get_data(as_text=True))
            assert data['agreement'] == {
                'id': agreement_id,
                'supplierId': supplier_framework['supplierId'],
                'frameworkSlug': supplier_framework['frameworkSlug'],
                'status': 'signed',
                'signedAgreementPath': '/example.pdf',
                'signedAgreementDetails': {
                    'signerName': 'name',
                    'signerRole': 'role',
                    'uploaderUserId': 1,
                    'frameworkAgreementVersion': 'v1.0'
                },
                'signedAgreementReturnedAt': '2016-12-12T00:00:00.000000Z'
            }

    def test_can_not_sign_framework_agreement_that_has_no_signer_name(self, user_role_supplier, supplier_framework):
        agreement_id = self.create_agreement(
            supplier_framework,
            signed_agreement_details={'signerRole': 'role'},
            signed_agreement_path='/example.pdf'
        )
        res = self.sign_agreement(agreement_id, {'signedAgreementDetails': {'uploaderUserId': user_role_supplier}})

        assert res.status_code == 400
        assert (
            json.loads(res.get_data(as_text=True))['error'] == {'signerName': 'answer_required'})

    def test_can_not_sign_framework_agreement_that_has_no_signer_role(self, user_role_supplier, supplier_framework):
        agreement_id = self.create_agreement(
            supplier_framework,
            signed_agreement_details={'signerName': 'name'},
            signed_agreement_path='/example.pdf'
        )
        res = self.sign_agreement(agreement_id, {'signedAgreementDetails': {'uploaderUserId': user_role_supplier}})

        assert res.status_code == 400
        assert (
            json.loads(res.get_data(as_text=True))['error'] == {'signerRole': 'answer_required'})

    def test_400_if_user_signing_framework_agreement_does_not_exist(self, user_role_supplier, supplier_framework):
        agreement_id = self.create_agreement(
            supplier_framework,
            signed_agreement_details={'signerName': 'name', 'signerRole': 'role'},
            signed_agreement_path='/example.pdf'
        )
        # The user_role_supplier fixture sets up user with ID 1; there is no user with ID 20
        res = self.sign_agreement(agreement_id, {'signedAgreementDetails': {'uploaderUserId': 20}})

        assert res.status_code == 400
        assert (
            json.loads(res.get_data(as_text=True))['error'] == "No user found with id '20'")


# Frameworks prior to G-Cloud 8 do not have framework_agreement_version set, and signing these stores only the timestamp
class TestSignFrameworkAgreementThatHasNoFrameworkAgreementVersion(BaseFrameworkAgreementTest):
    def sign_agreement(self, agreement_id):
        return self.client.post(
            '/agreements/{}/sign'.format(agreement_id),
            data=json.dumps(
                {
                    'updated_by': 'interested@example.com'
                }),
            content_type='application/json')

    def test_can_sign_framework_agreement(self, supplier_framework):
        agreement_id = self.create_agreement(supplier_framework)
        with freeze_time('2016-12-12'):
            res = self.sign_agreement(agreement_id)
            assert res.status_code == 200

            data = json.loads(res.get_data(as_text=True))
            assert data['agreement'] == {
                'id': agreement_id,
                'supplierId': supplier_framework['supplierId'],
                'frameworkSlug': supplier_framework['frameworkSlug'],
                'status': 'signed',
                'signedAgreementReturnedAt': '2016-12-12T00:00:00.000000Z'
            }

    def test_signing_framework_agreement_produces_audit_event(self, supplier_framework):
        agreement_id = self.create_agreement(supplier_framework)
        res = self.sign_agreement(agreement_id)
        assert res.status_code == 200

        agreement = FrameworkAgreement.query.filter(
            FrameworkAgreement.id == agreement_id
        ).first()

        audit = AuditEvent.query.filter(
            AuditEvent.object == agreement
        ).first()

        assert audit.type == "sign_agreement"
        assert audit.user == "interested@example.com"
        assert audit.data == {
            'supplierId': supplier_framework['supplierId'],
            'frameworkSlug': supplier_framework['frameworkSlug'],
        }

    def test_can_re_sign_framework_agreement(self, supplier_framework):
        agreement_id = self.create_agreement(
            supplier_framework,
            signed_agreement_returned_at=datetime.utcnow()
        )
        with freeze_time('2016-12-12'):
            res = self.sign_agreement(agreement_id)
            assert res.status_code == 200

            data = json.loads(res.get_data(as_text=True))
            assert data['agreement'] == {
                'id': agreement_id,
                'supplierId': supplier_framework['supplierId'],
                'frameworkSlug': supplier_framework['frameworkSlug'],
                'status': 'signed',
                'signedAgreementReturnedAt': '2016-12-12T00:00:00.000000Z'
            }


class TestPutFrameworkAgreementOnHold(BaseFrameworkAgreementTest):
    def put_framework_agreement_on_hold(self, agreement_id):
        return self.client.post(
            '/agreements/{}/on-hold'.format(agreement_id),
            data=json.dumps(
                {
                    'updated_by': 'interested@example.com'
                }),
            content_type='application/json')

    @fixture_params('live_example_framework', {'framework_agreement_details': {'frameworkAgreementVersion': 'v1.0'}})
    def test_can_put_framework_agreement_on_hold(self, supplier_framework):
        agreement_id = self.create_agreement(
            supplier_framework,
            signed_agreement_returned_at=datetime(2016, 10, 1),
        )

        with freeze_time('2016-12-12'):
            res = self.put_framework_agreement_on_hold(agreement_id)

        assert res.status_code == 200

        data = json.loads(res.get_data(as_text=True))

        assert data['agreement'] == {
            'id': agreement_id,
            'supplierId': supplier_framework['supplierId'],
            'frameworkSlug': supplier_framework['frameworkSlug'],
            'status': 'on-hold',
            'signedAgreementReturnedAt': '2016-10-01T00:00:00.000000Z',
            'signedAgreementPutOnHoldAt': '2016-12-12T00:00:00.000000Z'
        }

        agreement = FrameworkAgreement.query.filter(
            FrameworkAgreement.id == agreement_id
        ).first()

        audit = AuditEvent.query.filter(
            AuditEvent.object == agreement
        ).first()

        assert audit.type == "update_agreement"
        assert audit.user == "interested@example.com"
        assert audit.data == {
            'supplierId': supplier_framework['supplierId'],
            'frameworkSlug': supplier_framework['frameworkSlug'],
            'status': 'on-hold'
        }

    @fixture_params('live_example_framework', {'framework_agreement_details': {'frameworkAgreementVersion': 'v1.0'}})
    def test_can_not_put_unsigned_framework_agreement_on_hold(self, supplier_framework):
        agreement_id = self.create_agreement(supplier_framework)
        res = self.put_framework_agreement_on_hold(agreement_id)

        assert res.status_code == 400
        error_message = json.loads(res.get_data(as_text=True))['error']
        assert error_message == "Framework agreement must have status 'signed' to be put on hold"

    @fixture_params('live_example_framework', {'framework_agreement_details': {'frameworkAgreementVersion': 'v1.0'}})
    def test_can_not_put_countersigned_framework_agreement_on_hold(self, supplier_framework):
        agreement_id = self.create_agreement(
            supplier_framework,
            signed_agreement_returned_at=datetime(2016, 9, 1),
            countersigned_agreement_returned_at=datetime(2016, 10, 1)
        )
        res = self.put_framework_agreement_on_hold(agreement_id)

        assert res.status_code == 400
        error_message = json.loads(res.get_data(as_text=True))['error']
        assert error_message == "Framework agreement must have status 'signed' to be put on hold"

    def test_can_not_put_framework_agreement_on_hold_that_has_no_framework_agreement_version(self, supplier_framework):
        agreement_id = self.create_agreement(
            supplier_framework,
            signed_agreement_returned_at=datetime(2016, 10, 1)
        )
        res = self.put_framework_agreement_on_hold(agreement_id)

        assert res.status_code == 400
        error_message = json.loads(res.get_data(as_text=True))['error']
        assert error_message == "Framework agreement must have a 'frameworkAgreementVersion' to be put on hold"


class TestApproveFrameworkAgreement(BaseFrameworkAgreementTest):
    def approve_framework_agreement(self, agreement_id):
        return self.client.post(
            '/agreements/{}/approve'.format(agreement_id),
            data=json.dumps(
                {
                    'updated_by': 'chris@example.com',
                    'agreement': {'userId': '1234'}
                }),
            content_type='application/json')

    def unapprove_framework_agreement(self, agreement_id):
        return self.client.post(
            '/agreements/{}/approve'.format(agreement_id),
            data=json.dumps(
                {
                    'updated_by': 'made-a-whoopsie@example.com',
                    'agreement': {'userId': '1234', 'unapprove': True}
                }),
            content_type='application/json')

    @fixture_params(
        'live_example_framework', {
            'framework_agreement_details': {
                'frameworkAgreementVersion': 'v1.0',
                'countersignerName': 'The Boss',
                'countersignerRole': 'Director of Strings'
            }
        }
    )
    def test_can_approve_signed_framework_agreement(self, supplier_framework):
        agreement_id = self.create_agreement(
            supplier_framework,
            signed_agreement_returned_at=datetime(2016, 10, 1),
        )

        with freeze_time('2016-12-12'):
            res = self.approve_framework_agreement(agreement_id)

        assert res.status_code == 200

        data = json.loads(res.get_data(as_text=True))

        assert data['agreement'] == {
            'id': agreement_id,
            'supplierId': supplier_framework['supplierId'],
            'frameworkSlug': supplier_framework['frameworkSlug'],
            'status': 'approved',
            'signedAgreementReturnedAt': '2016-10-01T00:00:00.000000Z',
            'countersignedAgreementReturnedAt': '2016-12-12T00:00:00.000000Z',
            'countersignedAgreementDetails': {
                'countersignerName': 'The Boss',
                'countersignerRole': 'Director of Strings',
                'approvedByUserId': '1234'
            }
        }

        agreement = FrameworkAgreement.query.filter(
            FrameworkAgreement.id == agreement_id
        ).first()

        audit = AuditEvent.query.filter(
            AuditEvent.object == agreement
        ).first()

        assert audit.type == "countersign_agreement"
        assert audit.user == "chris@example.com"
        assert audit.data == {
            'supplierId': supplier_framework['supplierId'],
            'frameworkSlug': supplier_framework['frameworkSlug'],
            'status': 'approved'
        }

    @fixture_params(
        'live_example_framework', {
            'framework_agreement_details': {
                'frameworkAgreementVersion': 'v1.0',
                'countersignerName': 'The Boss',
                'countersignerRole': 'Director of Strings'
            }
        }
    )
    def test_can_approve_on_hold_framework_agreement(self, supplier_framework):
        agreement_id = self.create_agreement(
            supplier_framework,
            signed_agreement_returned_at=datetime(2016, 10, 1),
        )

        with freeze_time('2016-10-02'):
            on_hold_res = self.client.post(
                '/agreements/{}/on-hold'.format(agreement_id),
                data=json.dumps(
                    {
                        'updated_by': 'interested@example.com'
                    }),
                content_type='application/json')

        assert on_hold_res.status_code == 200

        on_hold_data = json.loads(on_hold_res.get_data(as_text=True))['agreement']
        assert on_hold_data['status'] == 'on-hold'

        with freeze_time('2016-10-03'):
            res = self.approve_framework_agreement(agreement_id)
        assert res.status_code == 200

        data = json.loads(res.get_data(as_text=True))

        assert 'signedAgreementPutOnHoldAt' not in data['agreement']
        assert data['agreement'] == {
            'id': agreement_id,
            'supplierId': supplier_framework['supplierId'],
            'frameworkSlug': supplier_framework['frameworkSlug'],
            'status': 'approved',
            'signedAgreementReturnedAt': '2016-10-01T00:00:00.000000Z',
            'countersignedAgreementReturnedAt': '2016-10-03T00:00:00.000000Z',
            'countersignedAgreementDetails': {
                'countersignerName': 'The Boss',
                'countersignerRole': 'Director of Strings',
                'approvedByUserId': '1234'
            }
        }

    @fixture_params('live_example_framework', {'framework_agreement_details': {'frameworkAgreementVersion': 'v1.0'}})
    def test_can_not_approve_unsigned_framework_agreement(self, supplier_framework):
        agreement_id = self.create_agreement(supplier_framework)
        res = self.approve_framework_agreement(agreement_id)

        assert res.status_code == 400
        error_message = json.loads(res.get_data(as_text=True))['error']
        assert error_message == "Framework agreement must have status 'signed' or 'on hold' to be countersigned"

    def test_can_approve_framework_agreement_that_has_no_framework_agreement_version(self, supplier_framework):
        agreement_id = self.create_agreement(
            supplier_framework,
            signed_agreement_returned_at=datetime(2016, 10, 1)
        )

        with freeze_time('2016-10-03'):
            res = self.approve_framework_agreement(agreement_id)
        assert res.status_code == 200

        data = json.loads(res.get_data(as_text=True))

        assert data['agreement'] == {
            'id': agreement_id,
            'supplierId': supplier_framework['supplierId'],
            'frameworkSlug': supplier_framework['frameworkSlug'],
            'status': 'approved',
            'signedAgreementReturnedAt': '2016-10-01T00:00:00.000000Z',
            'countersignedAgreementReturnedAt': '2016-10-03T00:00:00.000000Z',
            'countersignedAgreementDetails': {'approvedByUserId': '1234'}
        }

    @fixture_params('live_example_framework', {'framework_agreement_details': {'frameworkAgreementVersion': 'v1.0'}})
    def test_can_approve_framework_agreement_with_agreement_version_but_no_name_or_role(self, supplier_framework):
        agreement_id = self.create_agreement(
            supplier_framework,
            signed_agreement_returned_at=datetime(2016, 10, 1)
        )

        with freeze_time('2016-10-03'):
            res = self.approve_framework_agreement(agreement_id)
        assert res.status_code == 200

        data = json.loads(res.get_data(as_text=True))

        assert data['agreement'] == {
            'id': agreement_id,
            'supplierId': supplier_framework['supplierId'],
            'frameworkSlug': supplier_framework['frameworkSlug'],
            'status': 'approved',
            'signedAgreementReturnedAt': '2016-10-01T00:00:00.000000Z',
            'countersignedAgreementReturnedAt': '2016-10-03T00:00:00.000000Z',
            'countersignedAgreementDetails': {'approvedByUserId': '1234'}
        }

    @fixture_params(
        'live_example_framework', {
            'framework_agreement_details': {
                'frameworkAgreementVersion': 'v1.0',
                'countersignerName': 'The Boss',
                'countersignerRole': 'Director of Strings'
            }
        }
    )
    def test_serialized_supplier_framework_contains_updater_details_after_approval(self, supplier_framework):
        user = User(
            id=1234,
            name='Chris',
            email_address='chris@crowncommercial.gov.uk',
            password='password',
            active=True,
            created_at=datetime.now(),
            password_changed_at=datetime.now(),
            role='admin-ccs-sourcing'
        )
        db.session.add(user)
        db.session.commit()

        agreement_id = self.create_agreement(
            supplier_framework,
            signed_agreement_returned_at=datetime(2016, 10, 1),
            signed_agreement_details={},
            countersigned_agreement_details={
                "countersignerRole": "Director of Strings",
                "approvedByUserId": 1234,
                "countersignerName": "The Boss"
            },
            countersigned_agreement_returned_at=datetime.now()
        )

        agreement = FrameworkAgreement.query.filter(FrameworkAgreement.id == agreement_id).first()
        supplier_framework = agreement.supplier_framework.serialize(with_users=True)

        assert supplier_framework['countersignedDetails']['approvedByUserName'] == 'Chris'
        assert supplier_framework['countersignedDetails']['approvedByUserEmail'] == 'chris@crowncommercial.gov.uk'

    def test_can_unapprove_approved_agreement(self, supplier_framework):
        agreement_id = self.create_agreement(
            supplier_framework,
            signed_agreement_returned_at=datetime(2016, 10, 1)
        )

        with freeze_time('2016-12-12'):
            res1 = self.approve_framework_agreement(agreement_id)
            agreement_before_unapprove_data = json.loads(res1.get_data(as_text=True))

            # Check that the agreement is definitely approved
            assert agreement_before_unapprove_data['agreement'] == {
                'id': agreement_id,
                'supplierId': supplier_framework['supplierId'],
                'frameworkSlug': supplier_framework['frameworkSlug'],
                'status': 'approved',
                'signedAgreementReturnedAt': '2016-10-01T00:00:00.000000Z',
                'countersignedAgreementReturnedAt': '2016-12-12T00:00:00.000000Z',
                'countersignedAgreementDetails': {'approvedByUserId': '1234'}
            }

        res2 = self.unapprove_framework_agreement(agreement_id)
        assert res2.status_code == 200

        unapproved_agreement_data = json.loads(res2.get_data(as_text=True))
        # Check that status is reverted to 'signed' and countersigned info has been removed
        assert unapproved_agreement_data['agreement'] == {
            'id': agreement_id,
            'supplierId': supplier_framework['supplierId'],
            'frameworkSlug': supplier_framework['frameworkSlug'],
            'status': 'signed',
            'signedAgreementReturnedAt': '2016-10-01T00:00:00.000000Z',
        }

        agreement = FrameworkAgreement.query.filter(
            FrameworkAgreement.id == agreement_id
        ).first()

        # Get the most recent audit event and check it is the "unapprove" event
        audit = AuditEvent.query.filter(
            AuditEvent.object == agreement
        ).order_by(AuditEvent.created_at.desc()).first()

        assert audit.type == "countersign_agreement"
        assert audit.user == "made-a-whoopsie@example.com"
        assert audit.data == {
            'supplierId': supplier_framework['supplierId'],
            'frameworkSlug': supplier_framework['frameworkSlug'],
            'status': 'unapproved'
        }

    def test_can_not_unapprove_countersigned_agreement(self, supplier_framework):
        agreement_id = self.create_agreement(
            supplier_framework,
            signed_agreement_returned_at=datetime(2016, 10, 1),
            countersigned_agreement_returned_at=datetime(2016, 10, 2),
            countersigned_agreement_path='/path/to/countersigned/document'
        )
        res1 = self.client.get('/agreements/{}'.format(agreement_id))
        data1 = json.loads(res1.get_data(as_text=True))['agreement']
        assert data1['status'] == 'countersigned'

        res2 = self.unapprove_framework_agreement(agreement_id)
        data2 = json.loads(res2.get_data(as_text=True))
        assert res2.status_code == 400
        assert data2['error'] == "Framework agreement must have status 'approved' to be unapproved"

        # Check that status has not been changed
        res3 = self.client.get('/agreements/{}'.format(agreement_id))
        data3 = json.loads(res3.get_data(as_text=True))['agreement']
        assert data3 == {
            'id': agreement_id,
            'supplierId': supplier_framework['supplierId'],
            'frameworkSlug': supplier_framework['frameworkSlug'],
            'status': 'countersigned',
            'signedAgreementReturnedAt': '2016-10-01T00:00:00.000000Z',
            'countersignedAgreementReturnedAt': '2016-10-02T00:00:00.000000Z',
            'countersignedAgreementPath': '/path/to/countersigned/document'
        }
