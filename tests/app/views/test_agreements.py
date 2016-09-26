import json
import pytest
from datetime import datetime
from freezegun import freeze_time
from app.models import AuditEvent, db, Framework, FrameworkAgreement
from ..helpers import BaseApplicationTest, fixture_params


class BaseFrameworkAgreementTest(BaseApplicationTest):
    def create_agreement(self, supplier_framework, **framework_agreement_kwargs):
        with self.app.app_context():
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

        with self.app.app_context():
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

    def test_can_not_make_more_than_one_framework_agreement_per_supplier_framework(self, supplier_framework):
        res = self.post_create_agreement(
            supplier_id=supplier_framework['supplierId'],
            framework_slug=supplier_framework['frameworkSlug']
        )

        assert res.status_code == 201

        res = self.post_create_agreement(
            supplier_id=supplier_framework['supplierId'],
            framework_slug=supplier_framework['frameworkSlug']
        )

        assert res.status_code == 400
        assert (
            json.loads(res.get_data(as_text=True))['error'] ==
            "supplier_id '{}' already has a framework agreement for framework '{}'".format(
                supplier_framework['supplierId'], supplier_framework['frameworkSlug']
            )
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
            'frameworkSlug': supplier_framework['frameworkSlug']
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
            'signedAgreementDetails': {'details': 'here'},
            'signedAgreementPath': 'path',
            'signedAgreementReturnedAt': '2016-10-01T01:01:01.000000Z',
            'signedAgreementPutOnHoldAt': '2016-11-01T01:01:01.000000Z',
        }

    def test_it_gets_a_countersigned_framework_agreement_by_id(self, supplier_framework):
        agreement_id = self.create_agreement(
            supplier_framework,
            signed_agreement_returned_at=datetime(2016, 10, 1, 1, 1, 1),
            signed_agreement_details={'details': 'here'},
            signed_agreement_path='path',
            countersigned_agreement_details={'countersigneddetails': 'here'},
            countersigned_agreement_returned_at=datetime(2016, 11, 1, 1, 1, 1)
        )
        res = self.client.get('/agreements/{}'.format(agreement_id))

        assert res.status_code == 200
        assert json.loads(res.get_data(as_text=True))['agreement'] == {
            'id': agreement_id,
            'supplierId': supplier_framework['supplierId'],
            'frameworkSlug': supplier_framework['frameworkSlug'],
            'signedAgreementDetails': {'details': 'here'},
            'signedAgreementPath': 'path',
            'signedAgreementReturnedAt': '2016-10-01T01:01:01.000000Z',
            'countersignedAgreementDetails': {'countersigneddetails': 'here'},
            'countersignedAgreementReturnedAt': '2016-11-01T01:01:01.000000Z',
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

        with self.app.app_context():
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

    # TODO Behaviour to be introduced after next step of refactoring
    # @fixture_params('live_example_framework', {'framework_agreement_details': {'frameworkAgreementVersion': 'v1.0'}})
    # def test_400_cannot_update_signed_agreement(self, supplier_framework):
    #     agreement_id = self.create_agreement(supplier_framework, signed_agreement_returned_at=datetime.utcnow())
    #     res = self.post_agreement_update(agreement_id, {
    #         'signedAgreementPath': '/example.pdf'
    #     })

    #     assert res.status_code == 400
    #     assert json.loads(res.get_data(as_text=True)) == {
    #         'error': 'Can not update signedAgreementDetails or signedAgreementPath if agreement has been signed'
    #     }

    @fixture_params('live_example_framework', {'framework_agreement_details': {'frameworkAgreementVersion': 'v1.0'}})
    def test_400_if_some_random_key_in_update_json(self, supplier_framework):
        agreement_id = self.create_agreement(supplier_framework)
        res = self.post_agreement_update(agreement_id, {
            'signedRandomKey': 'banana'
        })

        assert res.status_code == 400
        assert json.loads(res.get_data(as_text=True)) == {
            'error': "Invalid JSON should not have 'signedRandomKey' keys"
        }

    @fixture_params('live_example_framework', {'framework_agreement_details': {'frameworkAgreementVersion': 'v1.0'}})
    def test_400_if_signed_agreement_details_contains_some_random_key(self, supplier_framework):
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

        with self.app.app_context():
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
                'signedAgreementReturnedAt': '2016-12-12T00:00:00.000000Z'
            }

    def test_signing_framework_agreement_produces_audit_event(self, supplier_framework):
        agreement_id = self.create_agreement(supplier_framework)
        res = self.sign_agreement(agreement_id)
        assert res.status_code == 200

        with self.app.app_context():
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
                'signedAgreementReturnedAt': '2016-12-12T00:00:00.000000Z'
            }
