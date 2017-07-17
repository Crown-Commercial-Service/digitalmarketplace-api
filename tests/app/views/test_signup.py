# coding: utf-8
from __future__ import unicode_literals

from dmapiclient import HTTPError
from dmapiclient.audit import AuditTypes
from dmutils.email import generate_token, EmailError
from ..helpers import BaseApplicationTest
import mock
import json


class TestSignupAPI(BaseApplicationTest):
    test_seller = {
        'name': 'matt',
        'email_address': 'email+s@company.com',
    }
    test_buyer = {
        'name': 'matt',
        'email_address': 'email+b@company.com',
        'employment_type': 'employee'
    }

    def setup(self):
        super(TestSignupAPI, self).setup()

    def test_duplicate_supplier_with_same_domain(self):
        response = self.client.post(
            '/signup',
            data=json.dumps({
                'email_address': 'm@examplecompany.biz',
                'name': 'Jeff Labowski'
            }),
            content_type='application/json')
        assert response.status_code == 200

    @mock.patch('app.auth.views.send_account_activation_email')
    def test_send_seller_type_signup_invite_email(self, send_email):
        response = self.client.post(
            '/signup',
            data=json.dumps(self.test_seller),
            content_type='application/json')
        assert response.status_code == 200

        send_email.assert_called_once_with(
            email_address=self.test_seller['email_address'],
            name=self.test_seller['name'],
            user_type='seller'
        )

    @mock.patch('app.auth.views.send_account_activation_email')
    def test_send_buyer_type_signup_invite_email(self, send_email):
        response = self.client.post(
            '/signup',
            data=json.dumps(self.test_buyer),
            content_type='application/json')
        assert response.status_code == 200

        send_email.assert_called_once_with(
            email_address=self.test_buyer['email_address'],
            name=self.test_buyer['name'],
            user_type='buyer'
        )
