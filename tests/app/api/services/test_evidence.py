import pytest

from app.api.services import evidence_assessment_service, evidence_service
from app.models import Evidence, EvidenceAssessment, Supplier, User, db, utcnow
from tests.app.helpers import BaseApplicationTest


class TestEvidenceService(BaseApplicationTest):
    def setup(self):
        super(TestEvidenceService, self).setup()

    @pytest.fixture()
    def suppliers(self, app):
        with app.app_context():
            db.session.add(
                Supplier(
                    id=1,
                    code=123,
                    name='BizBang',
                    status='limited',
                    is_recruiter=False
                )
            )

            db.session.commit()

            yield db.session.query(Supplier).all()

    @pytest.fixture()
    def users(self, app):
        with app.app_context():
            db.session.add(
                User(
                    id=1,
                    name='Seller',
                    email_address='sell@biz.com.au',
                    password='test',
                    active=True,
                    password_changed_at=utcnow(),
                    role='supplier'
                )
            )

            db.session.commit()

            yield db.session.query(User).all()

    @pytest.fixture()
    def evidence_response(self):
        yield {
            "startDate": "2016",
            "refereeNumber": "0412 345 678",
            "endDate": "2017",
            "refereeName": "Rafael Referee",
            "client": "DTA",
            "background": "Did stuff",
            "sameAsFirst": True,
            "response": "Agile on court"
        }

    @pytest.fixture()
    def evidence(self, app, suppliers, users, evidence_response):
        with app.app_context():
            db.session.add(
                Evidence(
                    id=1,
                    domain_id=1,
                    user_id=users[0].id,
                    supplier_code=suppliers[0].code,
                    data={
                        "criteria": [100],
                        "domainId": 1,
                        "evidence": {
                            "100": evidence_response
                        },
                        "id": 1,
                        "maxDailyRate": 123
                    }
                )
            )

            db.session.add(
                Evidence(
                    id=2,
                    domain_id=2,
                    user_id=users[0].id,
                    supplier_code=suppliers[0].code,
                    data={
                        "criteria": [200, 201],
                        "domainId": 2,
                        "evidence": {
                            "200": evidence_response,
                            "201": evidence_response
                        },
                        "id": 2,
                        "maxDailyRate": 123
                    }
                )
            )

            db.session.add(
                Evidence(
                    id=3,
                    domain_id=2,
                    user_id=users[0].id,
                    supplier_code=suppliers[0].code,
                    data={
                        "criteria": [200, 201, 202],
                        "domainId": 2,
                        "evidence": {
                            "200": evidence_response,
                            "201": evidence_response,
                            "202": evidence_response
                        },
                        "id": 3,
                        "maxDailyRate": 123
                    }
                )
            )

            db.session.commit()

            yield db.session.query(Evidence).all()

    @pytest.fixture()
    def evidence_assessments(self, app, evidence, users):
        with app.app_context():
            db.session.add(
                EvidenceAssessment(
                    id=1,
                    evidence_id=2,
                    user_id=users[0].id,
                    status='rejected',
                    data={
                        "failed_criteria": {
                            "200": {
                                "reason": "The evidence does not contain enough detail to assess",
                                "feedback": "Need more detail"
                            }
                        },
                        "vfm": False
                    }
                )
            )

            db.session.commit()

            yield db.session.query(Evidence).all()

    def test_approved_criteria_is_empty_when_no_previous_evidence_assessment_exists(self, evidence):
        submission = evidence_service.get(1)
        approved_criteria = evidence_service.get_approved_domain_criteria(submission.id, None)

        assert approved_criteria == []

    def test_approved_criteria_is_returned_when_not_in_failed_criteria(self, evidence, evidence_assessments):
        submission = evidence_service.get(3)
        previous_submission = evidence_service.get(2)
        approved_criteria = evidence_service.get_approved_domain_criteria(submission.id, previous_submission.id)

        assert approved_criteria == ['201']

    def test_unassessed_criteria_is_not_in_approved_criteria(self, evidence, evidence_assessments):
        submission = evidence_service.get(3)
        previous_submission = evidence_service.get(2)
        approved_criteria = evidence_service.get_approved_domain_criteria(submission.id, previous_submission.id)

        assert '202' not in approved_criteria
