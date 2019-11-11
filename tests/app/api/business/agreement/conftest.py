import pendulum
import pytest

from app.models import MasterAgreement, Supplier, User, db


@pytest.fixture()
def master_agreements(app):
    with app.app_context():
        now = pendulum.now('utc')

        db.session.add(
            MasterAgreement(
                id=1,
                start_date=now.subtract(years=3),
                end_date=now.subtract(years=2),
                data={
                    'pdfUrl': '/path/to/agreement1.pdf'
                }
            )
        )

        db.session.add(
            MasterAgreement(
                id=2,
                start_date=now.subtract(years=2),
                end_date=now.subtract(years=1),
                data={
                    'pdfUrl': '/path/to/agreement2.pdf'
                }
            )
        )

        db.session.add(
            MasterAgreement(
                id=3,
                start_date=now.subtract(years=1),
                end_date=now.add(years=1),
                data={
                    'htmlUrl': '/path/to/agreement3.html',
                    'pdfUrl': '/path/to/agreement3.pdf'
                }
            )
        )

        db.session.add(
            MasterAgreement(
                id=4,
                start_date=now.add(years=1),
                end_date=now.add(years=2),
                data={}
            )
        )

        db.session.commit()

        yield MasterAgreement.query.all()


@pytest.fixture()
def supplier(app):
    with app.app_context():
        db.session.add(
            Supplier(
                id=1,
                code=1,
                name='FriendFace',
                is_recruiter=False,
                data={}
            )
        )

        db.session.commit()

        yield Supplier.query.first()


@pytest.fixture()
def user(app):
    with app.app_context():
        db.session.add(
            User(
                id=1,
                name='Maurice Moss',
                email_address='moss@ri.com.au',
                password='mossman',
                active=True,
                password_changed_at=pendulum.now('utc'),
                role='supplier',
                supplier_code=1
            )
        )

        db.session.commit()

        yield Supplier.query.first()
