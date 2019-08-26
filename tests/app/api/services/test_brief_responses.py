import pytest

from app.api.services import (brief_responses_service, frameworks_service,
                              lots_service)
from app.models import Brief, BriefResponse, Framework, Lot, Supplier, db
from tests.app.helpers import BaseApplicationTest


class TestBriefResponseService(BaseApplicationTest):
    def setup(self):
        super(TestBriefResponseService, self).setup()

    @pytest.fixture()
    def briefs(self, app):
        with app.app_context():
            framework = frameworks_service.find(slug='digital-marketplace').one_or_none()
            digital_professional_lot = lots_service.find(slug='digital-professionals').one_or_none()
            specialist_lot = lots_service.find(slug='specialist').one_or_none()

            db.session.add(
                Brief(
                    id=1,
                    data={},
                    framework=framework,
                    lot=digital_professional_lot
                )
            )

            db.session.add(
                Brief(
                    id=2,
                    data={},
                    framework=framework,
                    lot=specialist_lot
                )
            )

            db.session.commit()
            yield db.session.query(Brief).all()

    @pytest.fixture()
    def brief_response_data(self):
        yield {
            "attachedDocumentURL": ["test.pdf"],
            "availability": "30/08/2019",
            "essentialRequirements": {
                "Did stuff": "I did stuff"
            },
            "hourRate": "605.00",
            "hourRateExcludingGST": "550",
            "niceToHaveRequirements": {
                "Did more stuff": "I did more stuff"
            },
            "previouslyWorked": "Yes",
            "respondToEmailAddress": "someone@biz.com.au",
            "securityClearance": "Yes",
            "visaStatus": "AustralianCitizen"
        }

    @pytest.fixture()
    def digital_professional_responses(self, app, briefs, brief_response_data, suppliers):
        with app.app_context():
            brief_response = BriefResponse(
                id=1,
                brief_id=1,
                data=brief_response_data,
                supplier_code=1
            )

            brief_response.data['specialistName'] = 'Klay Thompson'
            db.session.add(brief_response)

            brief_response = BriefResponse(
                id=2,
                brief_id=1,
                data=brief_response_data,
                supplier_code=1
            )

            brief_response.data['specialistName'] = 'steph curry'
            db.session.add(brief_response)

            brief_response = BriefResponse(
                id=3,
                brief_id=1,
                data=brief_response_data,
                supplier_code=1
            )

            brief_response.data['specialistName'] = 'kevin durant'
            db.session.add(brief_response)

            brief_response = BriefResponse(
                id=4,
                brief_id=1,
                data=brief_response_data,
                supplier_code=2
            )

            db.session.add(brief_response)

            brief_response = BriefResponse(
                id=5,
                brief_id=1,
                data=brief_response_data,
                supplier_code=3
            )

            db.session.add(brief_response)

            brief_response = BriefResponse(
                id=6,
                brief_id=1,
                data=brief_response_data,
                supplier_code=4
            )

            db.session.add(brief_response)

            db.session.commit()
            yield db.session.query(BriefResponse).all()

    @pytest.fixture()
    def specialist_responses(self, app, briefs, brief_response_data, suppliers):
        with app.app_context():
            brief_response = BriefResponse(
                id=1,
                brief_id=2,
                data=brief_response_data,
                supplier_code=1
            )

            brief_response.data['specialistGivenNames'] = 'Klay'
            brief_response.data['specialistSurname'] = 'Thompson'
            db.session.add(brief_response)

            brief_response = BriefResponse(
                id=2,
                brief_id=2,
                data=brief_response_data,
                supplier_code=1
            )

            brief_response.data['specialistGivenNames'] = 'steph'
            brief_response.data['specialistSurname'] = 'curry'
            db.session.add(brief_response)

            brief_response = BriefResponse(
                id=3,
                brief_id=2,
                data=brief_response_data,
                supplier_code=1
            )

            brief_response.data['specialistGivenNames'] = 'kevin'
            brief_response.data['specialistSurname'] = 'durant'
            db.session.add(brief_response)

            brief_response = BriefResponse(
                id=4,
                brief_id=2,
                data=brief_response_data,
                supplier_code=2
            )

            db.session.add(brief_response)

            brief_response = BriefResponse(
                id=5,
                brief_id=2,
                data=brief_response_data,
                supplier_code=3
            )

            db.session.add(brief_response)

            brief_response = BriefResponse(
                id=6,
                brief_id=2,
                data=brief_response_data,
                supplier_code=4
            )

            db.session.add(brief_response)

            db.session.commit()
            yield db.session.query(BriefResponse).all()

    @pytest.fixture()
    def suppliers(self, app):
        with app.app_context():
            db.session.add(
                Supplier(
                    id=1,
                    code=1,
                    is_recruiter=False,
                    name='Mega Bytes',
                    status='limited'
                )
            )

            db.session.add(
                Supplier(
                    id=2,
                    code=2,
                    is_recruiter=False,
                    name='qubits',
                    status='limited'
                )
            )

            db.session.add(
                Supplier(
                    id=3,
                    code=3,
                    is_recruiter=False,
                    name='Giga Bytes',
                    status='limited'
                )
            )

            db.session.add(
                Supplier(
                    id=4,
                    code=4,
                    is_recruiter=False,
                    name='bits',
                    status='limited'
                )
            )

            db.session.commit()
            yield db.session.query(Supplier).all()

    def test_responses_are_sorted_by_seller_name_for_digital_professional_briefs(self, digital_professional_responses):
        brief_responses = brief_responses_service.get_responses_to_zip(1, 'digital-professionals')

        assert len(brief_responses) == 6
        assert brief_responses[0].supplier.name == 'bits'
        assert brief_responses[1].supplier.name == 'Giga Bytes'
        assert brief_responses[2].supplier.name == 'Mega Bytes'
        assert brief_responses[3].supplier.name == 'Mega Bytes'
        assert brief_responses[4].supplier.name == 'Mega Bytes'
        assert brief_responses[5].supplier.name == 'qubits'

    def test_responses_are_sorted_by_specialist_name_for_digital_professional_briefs(self,
                                                                                     digital_professional_responses):
        brief_responses = brief_responses_service.get_responses_to_zip(1, 'digital-professionals')

        assert brief_responses[2].data['specialistName'] == 'kevin durant'
        assert brief_responses[3].data['specialistName'] == 'Klay Thompson'
        assert brief_responses[4].data['specialistName'] == 'steph curry'

    def test_responses_are_sorted_by_seller_name_for_specialist_briefs(self, specialist_responses):
        brief_responses = brief_responses_service.get_responses_to_zip(2, 'specialist')

        assert len(brief_responses) == 6
        assert brief_responses[0].supplier.name == 'bits'
        assert brief_responses[1].supplier.name == 'Giga Bytes'
        assert brief_responses[2].supplier.name == 'Mega Bytes'
        assert brief_responses[3].supplier.name == 'Mega Bytes'
        assert brief_responses[4].supplier.name == 'Mega Bytes'
        assert brief_responses[5].supplier.name == 'qubits'

    def test_responses_are_sorted_by_specialist_name_for_specialist_briefs(self, specialist_responses):
        brief_responses = brief_responses_service.get_responses_to_zip(2, 'specialist')

        assert brief_responses[2].data['specialistGivenNames'] == 'kevin'
        assert brief_responses[2].data['specialistSurname'] == 'durant'
        assert brief_responses[3].data['specialistGivenNames'] == 'Klay'
        assert brief_responses[3].data['specialistSurname'] == 'Thompson'
        assert brief_responses[4].data['specialistGivenNames'] == 'steph'
        assert brief_responses[4].data['specialistSurname'] == 'curry'
