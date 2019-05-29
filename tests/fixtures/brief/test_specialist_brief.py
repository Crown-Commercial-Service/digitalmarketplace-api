# -*- coding: utf-8 -*-
import json
import pytest
import mock

from app import encryption
from app.models import Brief, Lot, db, utcnow, Supplier, SupplierFramework, Contact, SupplierDomain, User,\
    Framework, UserFramework, AuditEvent, FrameworkLot
from app.api.business.validators import SpecialistDataValidator
from faker import Faker
from dmapiclient.audit import AuditTypes
from workdays import workday
import pendulum

fake = Faker()


@pytest.fixture()
def suppliers(app, request):
    with app.app_context():
        for i in range(1, 6):
            db.session.add(Supplier(
                abn=i,
                code=(i),
                name='Test Supplier{}'.format(i),
                contacts=[Contact(name='auth rep', email='auth@rep.com')],
                data={
                    'documents': {
                        "liability": {
                            "filename": "1.pdf",
                            "expiry": pendulum.tomorrow().date().to_date_string()
                        },
                        "workers": {
                            "filename": "2.pdf",
                            "expiry": pendulum.tomorrow().date().to_date_string()
                        },
                        "financial": {
                            "filename": "3.pdf"
                        }
                    },
                    'pricing': {
                        "Emerging technologies": {
                            "maxPrice": "1000"
                        },
                        "Support and Operations": {
                            "maxPrice": "100"
                        },
                        "Agile delivery and Governance": {
                            "maxPrice": "1000"
                        },
                        "Data science": {
                            "maxPrice": "100"
                        },
                        "Change, Training and Transformation": {
                            "maxPrice": "1000"
                        },
                        "Training, Learning and Development": {
                            "maxPrice": "1000"
                        },
                        "Strategy and Policy": {
                            "maxPrice": "1000"
                        },
                        "Software engineering and Development": {
                            "maxPrice": "1000"
                        },
                        "User research and Design": {
                            "maxPrice": "1000"
                        },
                        "Recruitment": {
                            "maxPrice": "1000"
                        }
                    }
                }
            ))

            db.session.flush()

        framework = Framework.query.filter(Framework.slug == "digital-marketplace").first()
        db.session.add(SupplierFramework(supplier_code=1, framework_id=framework.id))

        db.session.commit()
        yield Supplier.query.all()


@pytest.fixture()
def supplier_domains(app, request, suppliers):
    with app.app_context():
        for s in suppliers:
            for i in range(1, 3):
                db.session.add(SupplierDomain(
                    supplier_id=s.id,
                    domain_id=i,
                    status='assessed'
                ))

                db.session.flush()

        db.session.commit()
        yield SupplierDomain.query.all()


@pytest.fixture()
def supplier_user(app, request, suppliers):
    with app.app_context():
        db.session.add(User(
            id=100,
            email_address='j@examplecompany.biz',
            name=fake.name(),
            password=encryption.hashpw('testpassword'),
            active=True,
            role='supplier',
            supplier_code=suppliers[0].code,
            password_changed_at=utcnow()
        ))
        db.session.commit()
        db.session.flush()
        framework = Framework.query.filter(Framework.slug == "digital-outcomes-and-specialists").first()
        db.session.add(UserFramework(user_id=100, framework_id=framework.id))
        db.session.commit()
        yield User.query.first()


def test_validate_closed_at():
    assert SpecialistDataValidator({
        'closedAt': pendulum.today(tz='Australia/Sydney').add(days=21).format('%Y-%m-%d')
    }).validate_closed_at()

    assert SpecialistDataValidator({
        'closedAt': pendulum.today(tz='Australia/Sydney').add(days=2).format('%Y-%m-%d')
    }).validate_closed_at()

    assert not SpecialistDataValidator({
        'closedAt': pendulum.today(tz='Australia/Sydney').add(days=365).format('%Y-%m-%d')
    }).validate_closed_at()

    assert not SpecialistDataValidator({
        'closedAt': pendulum.today(tz='Australia/Sydney').add(days=1).format('%Y-%m-%d')
    }).validate_closed_at()

    assert not SpecialistDataValidator({
        'closedAt': ''
    }).validate_closed_at()


def test_validate_security_clearance_obtain():
    assert SpecialistDataValidator({
        'securityClearance': 'abilityToObtain',
        'securityClearanceObtain': 'baseline'
    }).validate_security_clearance_obtain()

    assert SpecialistDataValidator({
        'securityClearance': 'abilityToObtain',
        'securityClearanceObtain': 'nv1'
    }).validate_security_clearance_obtain()

    assert SpecialistDataValidator({
        'securityClearance': 'abilityToObtain',
        'securityClearanceObtain': 'nv2'
    }).validate_security_clearance_obtain()

    assert SpecialistDataValidator({
        'securityClearance': 'abilityToObtain',
        'securityClearanceObtain': 'pv'
    }).validate_security_clearance_obtain()

    assert not SpecialistDataValidator({
        'securityClearance': 'abilityToObtain',
        'securityClearanceObtain': 'foobar'
    }).validate_security_clearance_obtain()


def test_validate_security_clearance_current():
    assert SpecialistDataValidator({
        'securityClearance': 'mustHave',
        'securityClearanceCurrent': 'baseline'
    }).validate_security_clearance_current()

    assert SpecialistDataValidator({
        'securityClearance': 'mustHave',
        'securityClearanceCurrent': 'nv1'
    }).validate_security_clearance_current()

    assert SpecialistDataValidator({
        'securityClearance': 'mustHave',
        'securityClearanceCurrent': 'nv2'
    }).validate_security_clearance_current()

    assert SpecialistDataValidator({
        'securityClearance': 'mustHave',
        'securityClearanceCurrent': 'pv'
    }).validate_security_clearance_current()

    assert not SpecialistDataValidator({
        'securityClearance': 'mustHave',
        'securityClearanceCurrent': 'foobar'
    }).validate_security_clearance_current()


def test_validate_security_clearance_other():
    assert SpecialistDataValidator({
        'securityClearance': 'other',
        'securityClearanceOther': 'foobar'
    }).validate_security_clearance_other()

    assert not SpecialistDataValidator({
        'securityClearance': 'other',
        'securityClearanceOther': '   '
    }).validate_security_clearance_other()


def test_validate_start_date():
    assert SpecialistDataValidator({
        'startDate': pendulum.now('Australia/Canberra').start_of('day').format('%Y-%m-%d')
    }).validate_start_date()

    assert not SpecialistDataValidator({
        'startDate': pendulum.now('Australia/Canberra').subtract(days=1).start_of('day').format('%Y-%m-%d')
    }).validate_start_date()


def test_validate_evaluation_criteria_essential():
    assert SpecialistDataValidator({
        'includeWeightingsEssential': True,
        'essentialRequirements': [
            {
                'criteria': 'TEST',
                'weighting': '55'
            },
            {
                'criteria': 'TEST 2',
                'weighting': '45'
            },
            {
                'criteria': '',
                'weighting': ''
            }
        ]
    }).validate_evaluation_criteria_essential()

    assert SpecialistDataValidator({
        'includeWeightingsEssential': False,
        'essentialRequirements': [
            {
                'criteria': 'TEST'
            },
            {
                'criteria': 'TEST 2'
            },
            {
                'criteria': ''
            }
        ]
    }).validate_evaluation_criteria_essential()

    assert not SpecialistDataValidator({
        'includeWeightingsEssential': False,
        'essentialRequirements': [
            {
                'criteria': ''
            }
        ]
    }).validate_evaluation_criteria_essential()

    assert not SpecialistDataValidator({
        'includeWeightingsEssential': True,
        'essentialRequirements': [
            {
                'criteria': 'TEST'
            }
        ]
    }).validate_evaluation_criteria_essential()

    assert not SpecialistDataValidator({
        'includeWeightingsEssential': True,
        'essentialRequirements': [
            {
                'criteria': 'TEST',
                'weighting': ''
            }
        ]
    }).validate_evaluation_criteria_essential()

    assert not SpecialistDataValidator({
        'includeWeightingsEssential': True,
        'essentialRequirements': [
            {
                'criteria': 'TEST',
                'weighting': '0'
            }
        ]
    }).validate_evaluation_criteria_essential()

    assert not SpecialistDataValidator({
        'includeWeightingsEssential': True,
        'essentialRequirements': [
            {
                'criteria': 'TEST',
                'weighting': '80'
            },
            {
                'criteria': 'TEST 2',
                'weighting': '30'
            },
        ]
    }).validate_evaluation_criteria_essential()


def test_validate_evaluation_criteria_nice_to_have():
    assert SpecialistDataValidator({
        'includeWeightingsNiceToHave': True,
        'niceToHaveRequirements': [
            {
                'criteria': 'TEST',
                'weighting': '55'
            },
            {
                'criteria': 'TEST 2',
                'weighting': '45'
            },
            {
                'criteria': '',
                'weighting': ''
            }
        ]
    }).validate_evaluation_criteria_nice_to_have()

    assert SpecialistDataValidator({
        'includeWeightingsNiceToHave': False,
        'niceToHaveRequirements': [
            {
                'criteria': 'TEST'
            },
            {
                'criteria': 'TEST 2'
            },
            {
                'criteria': ''
            }
        ]
    }).validate_evaluation_criteria_nice_to_have()

    assert SpecialistDataValidator({
        'includeWeightingsNiceToHave': False,
        'niceToHaveRequirements': [
            {
                'criteria': ''
            }
        ]
    }).validate_evaluation_criteria_nice_to_have()

    assert not SpecialistDataValidator({
        'includeWeightingsNiceToHave': True,
        'niceToHaveRequirements': [
            {
                'criteria': 'TEST'
            }
        ]
    }).validate_evaluation_criteria_nice_to_have()

    assert not SpecialistDataValidator({
        'includeWeightingsNiceToHave': True,
        'niceToHaveRequirements': [
            {
                'criteria': 'TEST',
                'weighting': ''
            }
        ]
    }).validate_evaluation_criteria_nice_to_have()

    assert not SpecialistDataValidator({
        'includeWeightingsNiceToHave': True,
        'niceToHaveRequirements': [
            {
                'criteria': 'TEST',
                'weighting': '0'
            }
        ]
    }).validate_evaluation_criteria_nice_to_have()

    assert not SpecialistDataValidator({
        'includeWeightingsNiceToHave': True,
        'niceToHaveRequirements': [
            {
                'criteria': 'TEST',
                'weighting': '80'
            },
            {
                'criteria': 'TEST 2',
                'weighting': '30'
            },
        ]
    }).validate_evaluation_criteria_nice_to_have()


def test_validate_response_formats():
    assert SpecialistDataValidator({
        'evaluationType': [
            'Responses to selection criteria',
            'Résumés'.decode('utf-8'),
            'References',
            'Interviews',
            'Scenarios or tests',
            'Presentations'
        ]
    }).validate_response_formats()

    assert not SpecialistDataValidator({
        'evaluationType': [
            'Responses to selection criteria',
            'Résumés'.decode('utf-8'),
            'xxx',
        ]
    }).validate_response_formats()


def test_validate_sellers(supplier_domains, suppliers):
    assert SpecialistDataValidator({
        'openTo': 'selected',
        'sellerCategory': '1',
        'sellers': {
            '1': {
                'name': 'seller1'
            }
        }
    }).validate_sellers()

    assert SpecialistDataValidator({
        'openTo': 'selected',
        'sellerCategory': '4',
        'sellers': {
            '1': {
                'name': 'seller1'
            }
        }
    }).validate_sellers()


def test_validate_required():
    assert len(
        SpecialistDataValidator({})
        .validate_required()
    ) == 15
